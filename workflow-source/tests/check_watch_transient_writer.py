#!/usr/bin/env python3
"""watch_transient_writer 도구의 계약 검사.

## 무엇을 판정하는가

이 도구는 "고쳤다 되돌리는 writer" 를 잡으려고 존재한다 (TASK-2026-08-11-main-013).
그러므로 검사도 그 시나리오를 **되주입**한다 — 감시 중 파일을 고쳤다 되돌리고,
두 변화 모두 diff 와 함께 잡히는지 본다. 반대 방향(아무 일도 없으면 0건)도
같이 재야 한다 — 잡기만 잘하는 검출기는 위양성 검출기와 구분되지 않는다.

case:

1. **transient 되주입** — 변경→복원 2회 변화가 모두 이벤트로 남고, 첫 diff 에
   주입한 marker 가 있으며, snapshot/events.jsonl/summary.json 이 실재한다.
2. **무변화 0건** — 같은 시간 감시에서 이벤트 0건.
3. **소멸/재출현** — unlink 후 재작성이 missing / reappeared 로 갈려 남는다
   (rename-swap 형 쓰기가 폴링 사이에 ENOENT 로 보이는 경로).
4. **저장소 오염 거부** — 감시 대상이 속한 git 저장소 안에 로그를 두려 하면
   exit 2 로 거부하고, `--allow-repo-log` 명시 시에만 허용한다.
5. **조용한 실행은 잔여물 0** — 로그 위치 미지정 + 관측 0건이면 자동 생성한
   temp 로그 디렉터리를 지운다 (tempdir_leak_guard 의 요구 — 감시를 상시로
   돌려도 temp 가 쌓이지 않는다). 증거가 있으면 남긴다 (case 1 이 보장).

전부 temp 에서만 논다 — 원본 저장소는 읽지도 쓰지도 않는다
(`REQUIRES_QUIET_REPO` 불필요).
"""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "workflow-source" / "tools" / "watch_transient_writer.py"

READY_TIMEOUT_S = 10  # watcher 기동 신호 대기 상한
SETTLE_S = 0.4        # 변화 사이 간격 (interval 0.02 의 20배 — 폴링 누락 여지 없음)


def _spawn_watcher(target: Path, log_dir: Path) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [sys.executable, str(TOOL_PATH),
         "--file", str(target), "--log-dir", str(log_dir),
         "--interval", "0.02", "--duration", "30"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    # 고정 sleep 은 handshake 가 아니다 — CI 부하에서 기동이 늦으면 baseline 이
    # 첫 주입 "뒤"에 잡혀 변경 2건이 1건으로 접힌다 (2026-08-11 CI 실측 flake).
    # 도구가 baseline 확보 후 남기는 ready 마커를 기다린다.
    ready = log_dir / "watcher_ready.json"
    wait_deadline = time.monotonic() + READY_TIMEOUT_S
    while not ready.is_file():
        assert proc.poll() is None, \
            f"watcher 조기 종료: rc={proc.returncode} err={proc.stderr.read() if proc.stderr else ''}"
        assert time.monotonic() < wait_deadline, f"watcher 기동 신호 {READY_TIMEOUT_S}s 대기 초과"
        time.sleep(0.02)
    return proc


def _stop_and_summary(proc: subprocess.Popen[str], log_dir: Path) -> dict[str, object]:
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=15)
    summary_path = log_dir / "summary.json"
    assert summary_path.is_file(), f"summary.json 부재: {log_dir}"
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_transient_reinjection_is_captured(tmp: Path) -> None:
    target = tmp / "pyproject.toml"
    original = "[project]\nname = \"probe\"\nversion = \"1.0.0\"\n"
    target.write_text(original, encoding="utf-8")
    log_dir = tmp / "log1"
    log_dir.mkdir()

    proc = _spawn_watcher(target, log_dir)
    try:
        target.write_text(original.replace("1.0.0", "99.99.99"), encoding="utf-8")
        time.sleep(SETTLE_S)
        target.write_text(original, encoding="utf-8")  # 되돌린다 — transient 의 핵심
        time.sleep(SETTLE_S)
    finally:
        summary = _stop_and_summary(proc, log_dir)

    events = summary["events"]
    assert isinstance(events, list)
    changed = [e for e in events if e["kind"] == "changed"]
    assert len(changed) >= 2, f"변경+복원 2건이 잡혀야 한다: {events}"

    first = changed[0]
    diff_path = first["diff_path"]
    assert diff_path and Path(diff_path).is_file(), f"diff 부재: {first}"
    diff_text = Path(diff_path).read_text(encoding="utf-8")
    assert "99.99.99" in diff_text, f"주입 marker 가 diff 에 없다:\n{diff_text}"

    snapshot_path = first["snapshot_path"]
    assert snapshot_path and Path(snapshot_path).is_file(), f"snapshot 부재: {first}"
    assert (log_dir / "events.jsonl").is_file(), "events.jsonl 부재 (SIGKILL 대비 즉시 기록)"

    # 마지막 changed 는 복원 — md5 가 원본과 같아야 transient 임이 산출물에 남는다.
    import hashlib
    assert changed[-1]["md5"] == hashlib.md5(original.encode()).hexdigest(), \
        "복원 이벤트의 md5 가 원본과 달라야 할 이유가 없다"


def test_no_change_yields_zero_events(tmp: Path) -> None:
    target = tmp / "quiet.toml"
    target.write_text("untouched = true\n", encoding="utf-8")
    log_dir = tmp / "log2"
    log_dir.mkdir()

    proc = _spawn_watcher(target, log_dir)
    time.sleep(SETTLE_S)
    summary = _stop_and_summary(proc, log_dir)

    assert summary["event_count"] == 0, f"무변화인데 이벤트가 있다: {summary['events']}"
    polls = summary["polls"]
    assert isinstance(polls, int) and polls > 0, "폴링 0회는 감시가 아니다 — 실행 못 한 검사는 통과가 아니다"


def test_missing_and_reappear_are_distinct(tmp: Path) -> None:
    target = tmp / "vanish.toml"
    target.write_text("x = 1\n", encoding="utf-8")
    log_dir = tmp / "log3"
    log_dir.mkdir()

    proc = _spawn_watcher(target, log_dir)
    try:
        target.unlink()
        time.sleep(SETTLE_S)
        target.write_text("x = 2\n", encoding="utf-8")
        time.sleep(SETTLE_S)
    finally:
        summary = _stop_and_summary(proc, log_dir)

    events = summary["events"]
    assert isinstance(events, list)
    kinds = [e["kind"] for e in events]
    assert "missing" in kinds and "reappeared" in kinds, f"kinds={kinds}"


def test_refuses_log_inside_watched_repo(tmp: Path) -> None:
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    target = repo / "pyproject.toml"
    target.write_text("v = 1\n", encoding="utf-8")
    inside_log = repo / "watch-log"

    denied = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--file", str(target),
         "--log-dir", str(inside_log), "--duration", "0.1"],
        capture_output=True, text=True,
    )
    assert denied.returncode == 2, \
        f"저장소 안 로그는 거부해야 한다: rc={denied.returncode} err={denied.stderr}"
    assert "allow-repo-log" in denied.stderr, f"해제 방법을 안내해야 한다: {denied.stderr}"

    allowed = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--file", str(target),
         "--log-dir", str(inside_log), "--duration", "0.1", "--allow-repo-log"],
        capture_output=True, text=True,
    )
    assert allowed.returncode == 0, \
        f"--allow-repo-log 명시면 허용: rc={allowed.returncode} err={allowed.stderr}"


def test_quiet_run_leaves_no_auto_log(tmp: Path) -> None:
    target = tmp / "quiet2.toml"
    target.write_text("still = true\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--file", str(target),
         "--interval", "0.02", "--duration", "0.4"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    log_lines = [ln for ln in proc.stderr.splitlines() if ln.startswith("log:")]
    assert log_lines, f"자동 로그 경로가 stderr 에 보고돼야 한다: {proc.stderr}"
    auto_dir = Path(log_lines[0].split("log:", 1)[1].strip())
    assert not auto_dir.exists(), \
        f"관측 0건인데 자동 생성 로그가 남았다 (temp 누수): {auto_dir}"
    assert "관측 0건" in proc.stderr, proc.stderr


CASES = [
    test_transient_reinjection_is_captured,
    test_no_change_yields_zero_events,
    test_missing_and_reappear_are_distinct,
    test_refuses_log_inside_watched_repo,
    test_quiet_run_leaves_no_auto_log,
]


def main() -> int:
    passed = 0
    failures: list[str] = []
    for case in CASES:
        with tempfile.TemporaryDirectory(prefix="check-watch-transient-") as raw:
            try:
                case(Path(raw))
                passed += 1
            except AssertionError as exc:
                failures.append(f"{case.__name__}: {exc}")
            except Exception as exc:  # noqa: BLE001 — 검사 실패는 전부 보고한다
                failures.append(f"{case.__name__}: {type(exc).__name__}: {exc}")
    for line in failures:
        print(f"  FAIL {line}")
    print(f"{passed}/{len(CASES)} PASS")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
