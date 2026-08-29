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

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/workflow_kit/tools/*",
)

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "watch_transient_writer.py"

READY_TIMEOUT_S = 10  # watcher 기동 신호 대기 상한
#: 변화 사이 최소 간격. **고정 sleep 만으로는 부족하다** — 이 값이 폴링 간격(0.02)의
#: 20배라는 근거는 *폴러가 실제로 20번 스케줄된다* 는 전제에 기대는데, 전량 병렬
#: (16-way)에서는 그 전제가 깨진다. 2026-08-20 게이트의 slash 축에서 정확히 그렇게
#: 한 번 red 가 났고(standalone·재실행은 green), 원인은 감시자가 굶어 transient
#: 쓰기를 **되돌리기 전에 못 본** 것이었다. 그래서 아래 `_wait_for_events` 로
#: **관측을 기다린 뒤** 다음 단계로 간다 — sleep 은 하한일 뿐이다.
SETTLE_S = 0.4
#: 이벤트가 나타나기를 기다리는 상한. 부하가 커도 이 안에는 잡힌다.
EVENT_WAIT_S = 20.0


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


def _atomic_write(path: Path, text: str) -> None:
    """같은 디렉터리에 쓴 뒤 `os.replace` 로 갈아끼운다 — **한 번의 상태 전이**.

    `Path.write_text` 는 truncate 후 write 라 원자적이지 않다. 그 사이에는
    **빈 파일**과 **절반만 쓰인 파일**이 실재하고, 이 도구는 그것을 정직하게
    관측한다 — 감시자로서는 옳은 동작이다.

    문제는 테스트의 가정이었다 (TASK-2026-08-24-main-001). "이벤트가 1건
    쌓였다" 를 "내 주입 완결본이 관측됐다" 로 읽었는데, 둘은 다르다. 한가할
    때는 폴러가 truncate 창을 놓쳐 우연히 맞았고, 병렬 부하에서 타이밍이
    바뀌자 `changed[0]` 이 빈 파일이 되어 red 가 났다 (2026-08-22 전량).

    실측 (창을 넓혀 원리 확인): 1.8MB 파일을 30회 왕복시키면 changed 22건 중
    **12건이 완결 아닌 크기**(`0`, `1800046`)를 관측한다.

    그래서 테스트는 원자적으로 쓴다 — 재려는 것은 *transient 를 잡는가* 이지
    *부분 쓰기를 잡는가* 가 아니다. 후자는 아래 전용 case 가 따로 선언한다.
    """
    tmp_path = path.with_name(path.name + ".tmp-atomic")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def _wait_for_events(log_dir: Path, minimum: int, *, timeout: float = EVENT_WAIT_S) -> int:
    """`events.jsonl` 에 `changed` 이벤트가 `minimum` 건 쌓일 때까지 기다린다.

    감시자는 이벤트를 **즉시** 기록하므로(SIGKILL 대비) 종료를 기다리지 않고 셀 수
    있다. 고정 sleep 대신 이걸 쓰는 이유는 위 `SETTLE_S` 주석 참조 — 부하에서
    폴러가 굶으면 고정 시간은 근거가 못 된다.
    """
    deadline = time.time() + timeout
    path = log_dir / "events.jsonl"
    seen = 0
    while time.time() < deadline:
        if path.is_file():
            seen = sum(
                1 for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and json.loads(line).get("kind") == "changed"
            )
            if seen >= minimum:
                return seen
        time.sleep(0.05)
    return seen


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
        # **원자적으로** 쓴다. 비원자적 쓰기는 truncate 창에 빈 파일을 노출하고,
        # 감시자는 그것을 첫 변경으로 잡는다 — 그러면 아래 `changed[0]` 단언이
        # 부하에 따라 갈린다 (`_atomic_write` 주석의 2026-08-22 flake).
        _atomic_write(target, original.replace("1.0.0", "99.99.99"))
        # **되돌리기 전에** 첫 변경이 관측됐는지 확인한다. 이걸 기다리지 않고
        # 되돌리면 감시자가 굶은 사이 원본으로 돌아가 transient 가 통째로 사라진다.
        assert _wait_for_events(log_dir, 1) >= 1, "주입이 관측되지 않았다 (감시자 기아)"
        _atomic_write(target, original)  # 되돌린다 — transient 의 핵심
        _wait_for_events(log_dir, 2)
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


def test_intermediate_state_is_reported_not_smoothed(tmp: Path) -> None:
    """디스크에 **실재했던 중간 상태**는 보고된다 — 뭉개지 않는다.

    이것은 결함이 아니라 **선언된 동작**이다 (TASK-2026-08-24-main-001).
    비원자적 쓰기(`Path.write_text` = truncate 후 write)는 그 사이 빈 파일을
    디스크에 **실재하게** 한다. 포렌식 감시자가 그것을 못 본다면 오히려 놓치는
    것이다 — 남의 도구가 파일을 잠깐 망가뜨렸다 되돌리는 것이 바로 이 도구가
    찾으라고 만들어진 현상이다.

    이 case 가 없으면 다음 사람이 그 관측을 잡음으로 오해해 **도구 쪽을
    뭉갠다**(빈 파일 무시·완결 대기 따위). 그러면 도구의 존재 이유가 사라진다.

    **중간 상태를 운에 맡기지 않는다.** 첫 판은 큰 파일을 비원자적으로 써서
    폴러가 truncate 창을 잡길 기대했는데, 그 자신이 5회 중 4회 red 인 flake 가
    됐다 — 고치려던 병을 검사가 다시 앓은 것이다. 그래서 중간 상태를 **폴링
    간격보다 확실히 긴 시간 동안 실재**하게 만든다. 재려는 것은 *폴러가 좁은
    창을 잡는가* 가 아니라 *실재한 상태를 보고하는가* 다.
    """
    target = tmp / "pyproject.toml"
    original = "[project]\nname = \"probe\"\nversion = \"1.0.0\"\n"
    target.write_text(original, encoding="utf-8")
    log_dir = tmp / "log6"
    log_dir.mkdir()

    proc = _spawn_watcher(target, log_dir)
    try:
        # 2단계 쓰기: 비우고 → (폴링 간격보다 길게) 머문 뒤 → 채운다.
        # 비원자적 쓰기가 만드는 상태를 **결정적으로** 재현한 것이다.
        with target.open("w", encoding="utf-8") as handle:
            handle.truncate(0)
            handle.flush()
            os.fsync(handle.fileno())
            assert _wait_for_events(log_dir, 1) >= 1, "빈 상태가 관측되지 않았다 (감시자 기아)"
            handle.write(original.replace("1.0.0", "99.99.99"))
        _wait_for_events(log_dir, 2)
        time.sleep(SETTLE_S)
    finally:
        summary = _stop_and_summary(proc, log_dir)

    changed = [e for e in summary["events"] if e["kind"] == "changed"]
    assert changed, f"변경이 하나도 안 잡혔다: {summary}"
    empty = [e for e in changed if e.get("size") == 0]
    assert empty, (
        "디스크에 실재했던 빈 상태가 보고되지 않았다 — 감시자가 중간 상태를 "
        f"뭉개면 transient 포렌식이 성립하지 않는다. 관측 크기: "
        f"{[e.get('size') for e in changed]}"
    )


CASES = [
    test_transient_reinjection_is_captured,
    test_no_change_yields_zero_events,
    test_missing_and_reappear_are_distinct,
    test_refuses_log_inside_watched_repo,
    test_quiet_run_leaves_no_auto_log,
    test_intermediate_state_is_reported_not_smoothed,
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
