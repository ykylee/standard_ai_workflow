#!/usr/bin/env python3
"""파일을 일시적으로 고쳤다 되돌리는 writer 를 **현장에서** 붙잡는 감시 도구.

## 왜 이 도구가 있는가

2026-08-11 병렬 전량 검사 중 원본 `workflow-source/pyproject.toml` 이 일시
변경됐다 되돌아왔다 (`version_auto_sync` 의 byte-대조가 1회 포착). 표적 3회 +
전량 2회 재실행과 50ms md5 watcher(일회용 셸 스크립트)로도 재현하지 못했고,
그 스크립트는 저장소 밖(`~/tmp`)에 있어 다음 사람은 다시 만들어야 한다 —
**일회용 조사는 조사가 아니다.** 이 도구는 그 감시를 저장소에 고정한다.

`check_no_repo_write` 는 "실행 **후** 복원되었는가" 만 판정하므로 고쳤다
되돌리는 writer 를 구조적으로 못 본다 (**되돌리는 것은 안 건드리는 것이
아니다**). 실행 *중* 감시를 검사 계약으로 격상하는 것은 범위가 크다고 판단해
(handoff §6), 이 도구는 **opt-in** 이다 — 재발이 의심될 때 옆에 세워 둔다.

## 무엇을 남기는가

변화가 관측될 때마다 이벤트 1건:

- **diff** — 직전 내용과의 unified diff. *무엇을* 고쳤는지가 writer 의 정체를
  가장 강하게 좁힌다 (version bump 모양이면 release 경로, 등).
- **내용 스냅샷** — 변경된 내용 전문 (diff 가 잘려도 원본이 남게).
- **ps 전량 스냅샷** — 그 순간의 전체 프로세스 목록. 패턴 필터로 *저장하지
  않는다* — 포함 목록은 사각지대를 못 보고, 용의자 패턴이 틀리면 현장을
  잃는다. 필터링은 사후에 한다.
- **fuser** — 그 순간 파일을 잡고 있는 프로세스 (best-effort, 없으면 skip).

파일이 일시 소멸/재출현하는 것도 별도 이벤트로 남긴다 (rename-swap 형태의
쓰기는 md5 폴링 사이에 ENOENT 로 보일 수 있다).

## 오염하지 않는다

로그는 기본적으로 시스템 temp 아래에 만든다. 감시 대상 파일이 속한 git 저장소
**안**에 로그를 두려 하면 거부한다 (`--allow-repo-log` 로만 해제) — 감시
도구가 저장소를 오염시키면 관찰 자체가 다른 검사의 위양성이 된다.

사용:

    # 전량 검사를 돌리는 동안 옆에서 감시 (기본 대상: cwd 의 workflow-source/pyproject.toml)
    python3 workflow-source/tools/watch_transient_writer.py &
    .venv/bin/python3 workflow-source/tests/run_all_checks.py --branch-context=all --tmp-dir=...
    kill %1   # SIGTERM 을 받으면 summary.json 을 쓰고 종료한다

    # 명시 인자
    python3 workflow-source/tools/watch_transient_writer.py \
        --file workflow-source/pyproject.toml --interval 0.05 --duration 600 --json

Cross-ref: session_handoff §6 "transient pyproject writer 정체 미상",
TASK-2026-08-11-main-008 (관찰자 3검사 정숙화), TASK-2026-08-11-main-013.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FILE_SOURCE_ARGUMENT = "argument"
FILE_SOURCE_CWD_DEFAULT = "cwd-default"

#: 미지정 시 cwd 기준으로 찾는 기본 대상 — 이 도구를 만들게 한 바로 그 파일.
DEFAULT_TARGET_RELPATH = "workflow-source/pyproject.toml"


@dataclass
class Event:
    seq: int
    kind: str  # "changed" | "missing" | "reappeared"
    at_unix: float
    at_human: str
    md5: str | None
    size: int | None
    mtime_ns: int | None
    diff_path: str | None = None
    snapshot_path: str | None = None
    ps_path: str | None = None
    fuser: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq, "kind": self.kind,
            "at_unix": self.at_unix, "at_human": self.at_human,
            "md5": self.md5, "size": self.size, "mtime_ns": self.mtime_ns,
            "diff_path": self.diff_path, "snapshot_path": self.snapshot_path,
            "ps_path": self.ps_path, "fuser": self.fuser,
        }


@dataclass
class WatchResult:
    target: str
    target_source: str
    log_dir: str
    interval_s: float
    started_at: str
    stopped_at: str = ""
    polls: int = 0
    events: list[Event] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "target_source": self.target_source,
            "log_dir": self.log_dir,
            "interval_s": self.interval_s,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "polls": self.polls,
            "event_count": len(self.events),
            "events": [e.as_dict() for e in self.events],
        }


def _now_human() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + f".{int(time.time() * 1000) % 1000:03d}"


def _read_state(path: Path) -> tuple[str, int, int, bytes] | None:
    """(md5, size, mtime_ns, content) — 파일이 없으면 None.

    내용까지 함께 읽는 이유: md5 만 남기면 "바뀌었다" 는 알아도 *무엇이*
    바뀌었는지를 잃는다. diff 가 writer 의 정체를 좁히는 핵심 증거다.
    """
    try:
        content = path.read_bytes()
        st = path.stat()
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        return None
    return (hashlib.md5(content).hexdigest(), st.st_size, st.st_mtime_ns, content)


def _git_toplevel(path: Path) -> Path | None:
    """path 가 속한 git 저장소 루트. 없으면 None."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path if path.is_dir() else path.parent),
             "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def _capture_ps(log_dir: Path, seq: int) -> str | None:
    """ps 전량 스냅샷을 파일로. 필터링은 사후에 — 용의자 목록이 틀리면 현장을 잃는다."""
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,ppid,etime,args"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = log_dir / f"event-{seq:03d}.ps.txt"
    out.write_text(proc.stdout, encoding="utf-8")
    return str(out)


def _capture_fuser(target: Path) -> str | None:
    """그 순간 파일을 잡고 있는 프로세스 (best-effort — fuser 부재/무점유면 None)."""
    try:
        proc = subprocess.run(
            ["fuser", "-v", str(target)],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    combined = (proc.stdout + proc.stderr).strip()
    return combined or None


def _write_diff(log_dir: Path, seq: int, before: bytes, after: bytes) -> str:
    before_text = before.decode("utf-8", errors="replace").splitlines(keepends=True)
    after_text = after.decode("utf-8", errors="replace").splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(
        before_text, after_text, fromfile="before", tofile="after"))
    out = log_dir / f"event-{seq:03d}.diff"
    out.write_text(diff if diff else "(binary 또는 diff 산출 불가 — snapshot 대조)\n",
                   encoding="utf-8")
    return str(out)


def _write_snapshot(log_dir: Path, seq: int, content: bytes) -> str:
    out = log_dir / f"event-{seq:03d}.snapshot"
    out.write_bytes(content)
    return str(out)


def resolve_target(raw: str | None) -> tuple[Path, str]:
    """감시 대상과 **그 출처** — 모듈 위치에서 유도하지 않는다 (audit_root_anchors R2)."""
    if raw is not None:
        return Path(raw).resolve(), FILE_SOURCE_ARGUMENT
    return (Path.cwd() / DEFAULT_TARGET_RELPATH).resolve(), FILE_SOURCE_CWD_DEFAULT


def watch(target: Path, target_source: str, log_dir: Path, interval_s: float,
          duration_s: float, stop_flag: dict[str, bool]) -> WatchResult:
    result = WatchResult(
        target=str(target), target_source=target_source, log_dir=str(log_dir),
        interval_s=interval_s, started_at=_now_human(),
    )
    prev = _read_state(target)
    # baseline 을 뜬 "뒤"에 ready 마커를 남긴다 — 감시가 실제로 무장된 시점의
    # 증거이자, 호출자(검사 포함)가 sleep 추측 대신 기다릴 수 있는 handshake.
    (log_dir / "watcher_ready.json").write_text(
        json.dumps({"started_at": result.started_at,
                    "baseline_present": prev is not None}, ensure_ascii=False),
        encoding="utf-8")
    deadline = time.monotonic() + duration_s if duration_s > 0 else None
    seq = 0

    while not stop_flag["stop"]:
        if deadline is not None and time.monotonic() >= deadline:
            break
        time.sleep(interval_s)
        result.polls += 1
        cur = _read_state(target)

        if cur is None and prev is None:
            continue
        if cur is not None and prev is not None and cur[0] == prev[0]:
            prev = cur
            continue

        # 변화다 — 현장부터 뜬다 (ps/fuser 는 지금이 아니면 사라진다).
        seq += 1
        ps_path = _capture_ps(log_dir, seq)
        fuser_out = _capture_fuser(target)

        if cur is None:
            event = Event(
                seq=seq, kind="missing", at_unix=time.time(), at_human=_now_human(),
                md5=None, size=None, mtime_ns=None, ps_path=ps_path, fuser=fuser_out,
            )
        else:
            kind = "reappeared" if prev is None else "changed"
            event = Event(
                seq=seq, kind=kind, at_unix=time.time(), at_human=_now_human(),
                md5=cur[0], size=cur[1], mtime_ns=cur[2],
                snapshot_path=_write_snapshot(log_dir, seq, cur[3]),
                diff_path=_write_diff(log_dir, seq, prev[3] if prev else b"", cur[3]),
                ps_path=ps_path, fuser=fuser_out,
            )
        result.events.append(event)
        # 이벤트는 즉시도 남긴다 — watcher 가 SIGKILL 로 죽으면 summary 는 못 쓴다.
        (log_dir / "events.jsonl").open("a", encoding="utf-8").write(
            json.dumps(event.as_dict(), ensure_ascii=False) + "\n")
        prev = cur

    result.stopped_at = _now_human()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    parser.add_argument("--file", default=None,
                        help=f"감시 대상 (기본: cwd 의 {DEFAULT_TARGET_RELPATH})")
    parser.add_argument("--log-dir", default=None,
                        help="증거 저장 위치 (기본: 시스템 temp 에 신규 생성)")
    parser.add_argument("--interval", type=float, default=0.05,
                        help="폴링 간격 초 (기본 0.05)")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="감시 시간 초 (기본 0 = SIGINT/SIGTERM 까지)")
    parser.add_argument("--json", action="store_true", help="종료 시 summary JSON 을 stdout 으로")
    parser.add_argument("--allow-repo-log", action="store_true",
                        help="감시 대상 저장소 안에 로그를 두는 것을 허용 (기본 거부)")
    args = parser.parse_args(argv)

    target, target_source = resolve_target(args.file)
    if not target.exists():
        print(f"FAIL: 감시 대상이 없다: {target} (출처: {target_source})", file=sys.stderr)
        return 2

    auto_log_dir = args.log_dir is None
    if auto_log_dir:
        log_dir = Path(tempfile.mkdtemp(prefix="watch-transient-writer-")).resolve()
    else:
        log_dir = Path(args.log_dir).resolve()
        log_dir.mkdir(parents=True, exist_ok=True)

    # 감시 도구가 저장소를 오염시키면 관찰 자체가 다른 검사의 위양성이 된다.
    repo = _git_toplevel(target)
    if repo is not None and not args.allow_repo_log \
            and (log_dir == repo or repo in log_dir.parents):
        print(f"FAIL: 로그 위치({log_dir})가 감시 대상 저장소({repo}) 안이다 — "
              f"저장소 밖 경로를 쓰거나 --allow-repo-log 로 명시 해제할 것.",
              file=sys.stderr)
        return 2

    stop_flag = {"stop": False}

    def _stop(_signum: int, _frame: Any) -> None:
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(f"watch: {target} (출처: {target_source})", file=sys.stderr)
    print(f"log:   {log_dir}", file=sys.stderr)

    result = watch(target, target_source, log_dir, args.interval, args.duration, stop_flag)

    # 관측 0건 + 자동 생성 로그면 지운다 — 조용한 감시가 실행마다 temp dir 을
    # 쌓으면 안 된다 (tempdir_leak_guard). 증거가 있거나 사용자가 위치를 명시했으면 남긴다.
    if auto_log_dir and not result.events:
        shutil.rmtree(log_dir, ignore_errors=True)
        if args.json:
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"관측 0건 / poll {result.polls}회 — 자동 생성 로그 제거", file=sys.stderr)
        return 0

    summary_path = log_dir / "summary.json"
    summary_path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"관측 {len(result.events)}건 / poll {result.polls}회 — 증거: {log_dir}",
              file=sys.stderr)
        for e in result.events:
            print(f"  [{e.seq:03d}] {e.kind} @ {e.at_human} md5={e.md5} "
                  f"diff={e.diff_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
