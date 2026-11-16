"""받은편지함 도착 신호 — 워크벤치가 응답을 받으면 작업 세션의 hook 이 곧바로 알게 한다 (TASK-2026-11-16-main-014).

- 서버는 응답을 공개한 뒤 checkout 루트의 ``.workbench/inbox.stamp`` 에 **새 표식**(시각 + 무작위)을 쓴다 — 쓰는 것은
  여전히 받은편지함과 ``.workbench/`` 뿐이다 (ADR-032 결정 15: task 파일은 작업 세션만 쓴다).
- 작업 세션의 hook 은 ``inbox.stamp`` 와 ``inbox.seen`` 의 **내용**이 다를 때만 ``plan-import --hook`` 을 부른다 (``cmp``).
  mtime 이 아니라 내용이라 1초 단위 파일시스템에서도 같은 초의 두 번째 응답을 놓치지 않는다 (verifier 재현).
- 처리한 뒤 ``inbox.seen`` 에 처리 **시작 때 읽은** 표식을 쓴다 — 처리 중 새 응답이 오면 표식이 달라 다음 hook 이 다시 본다.
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path

DIRNAME = ".workbench"
STAMP = "inbox.stamp"
SEEN = "inbox.seen"
GITIGNORE_BODY = b"*\n"


def signal_dir(workspace: Path) -> Path:
    return workspace / DIRNAME


def _ensure_dir(workspace: Path) -> Path:
    directory = signal_dir(workspace)
    directory.mkdir(exist_ok=True)
    ignore = directory / ".gitignore"
    try:
        current = ignore.read_bytes() if ignore.is_file() else None
    except OSError:
        current = None
    if current != GITIGNORE_BODY:
        ignore.write_bytes(GITIGNORE_BODY)
    return directory


def _write_atomic(path: Path, data: bytes) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}")
    temp.write_bytes(data)
    os.replace(temp, path)


def touch_stamp(workspace: Path) -> Path:
    """응답이 도착했다는 표시 — 매번 다른 표식을 쓴다 (내용 비교라 시각 해상도에 기대지 않는다)."""
    path = _ensure_dir(workspace) / STAMP
    _write_atomic(path, f"{time.time_ns()}-{secrets.token_hex(8)}\n".encode("ascii"))
    return path


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def pending_signal(workspace: Path) -> bytes | None:
    """처리할 신호가 있으면 그 stamp 표식, 없으면 None — seen 이 없거나 내용이 다를 때만."""
    stamp = _read(signal_dir(workspace) / STAMP)
    if not stamp:
        return None
    return stamp if stamp != _read(signal_dir(workspace) / SEEN) else None


def mark_seen(workspace: Path, stamp: bytes) -> None:
    """처리 시작 때 읽은 표식을 seen 에 쓴다 — 그 사이 새 응답이 왔으면 stamp 가 달라 다음 hook 이 다시 본다."""
    _write_atomic(_ensure_dir(workspace) / SEEN, stamp)
