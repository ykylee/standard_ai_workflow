"""교차 플랫폼 **배타 파일 락** — POSIX ``fcntl.flock`` / Windows ``msvcrt.locking``.

## 왜 필요한가 (TASK-2026-10-31-main-003)

``fcntl`` 는 POSIX 전용이라 Windows 에서 import 하면 ``ModuleNotFoundError`` 다.
그래서 전까지 두 구현이 **각자** Windows 를 처리했는데, 두 곳 다 같은 방향으로
실패했다: *"락을 못 잡으면 조용히 진행"* — 동시 실행 가드가 사라지는 것이다.
검사 하나는 ``ModuleNotFoundError`` 로 죽고, 다른 하나는 **락 없이 진행**했다.
동작이 조용히 약해지는 실패가 가장 나쁘다.

여기서는 두 플랫폼의 공통 계약 하나만 둔다:

- :func:`try_lock_exclusive` — 즉시(비차단) 배타 획득. 성공 ``True``.
- :func:`lock_exclusive_blocking` — 대기하며 획득.
- :func:`unlock` — 해제.

호출자는 어느 플랫폼인지 몰라도 된다.

## Windows 구현 — 실측으로 확정한 함정 (2026-10-31)

Windows 바이트범위 락은 POSIX ``flock`` 와 성질이 다르다. **advisory 가 아니라
mandatory** 다 — 락이 덮는 영역의 읽기/쓰기가 *다른 프로세스* 에게 막힌다.

1. ``msvcrt.locking`` 은 **현재 파일 위치** 부터 n 바이트를 잠근다. 파일 위치가
   락 위치다.
2. **락 영역과 내용 영역이 겹치면 안 된다.** 락 파일 안에 보유자 정보(JSON)를
   써 넣는 설계이므로, 정보는 앞쪽(오프셋 0)에 두고 락은 그 뒤
   (:data:`WINDOWS_LOCK_OFFSET`)에 건다. 그래야 "락이 잡힌 상태로 정보를 읽는다" 가
   성립한다 — 앞쪽을 잠그면 contender 가 정보를 **읽지 못한다**.
3. **빈 파일은 문제가 된다.** 크기 0 인 파일의 뒤쪽을 잠그면 그 파일 전체가
   읽히지 않는다 (실측). 그래서 락 전에 최소 1 바이트를 확보한다.
4. **잠근 상태에서 자기가 쓰기는 된다.** 보유자가 정보를 덮어써도 락이 풀리지
   않는다 (실측).
5. 같은 프로세스의 **다른 핸들** 로 같은 바이트를 잠그면 ``OSError(13)`` 로 막힌다
   — "이미 잡혔는지" 판정에 그대로 쓸 수 있다 (실측).

위 1~5 는 전부 이 호스트에서 직접 실측한 값이다 (2026-10-31).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import IO, Any

#: Windows 바이트범위 락을 걸 오프셋 — **내용 영역과 겹치지 않는 곳**.
#:
#: 보유자 정보(JSON)는 오프셋 0 에 쓰고, 락은 여기 둔다. 앞쪽을 잠그면
#: contender 가 정보를 읽지 못한다 (위 2번 함정).
WINDOWS_LOCK_OFFSET = 65536


def prepare_lock_file(path: Path) -> None:
    """락 파일을 준비한다 — 없으면 만들고, 비어 있으면 최소 1 바이트를 넣는다.

    Windows 의 빈 파일 함정(위 3번) 때문에 필요하다. 이미 다른 주체가 락을
    잡고 있으면 이 쓰기는 막힌다 — 그 경우에도 락 시도 자체가 "이미 잡혔다" 로
    판정되므로, 준비 단계는 best effort 다.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > 0:
            return
        with open(path, "ab") as handle:
            handle.write(b"\0")
            handle.flush()
    except OSError:
        # 준비 단계 실패는 조용히 넘긴다 — 실제 락 시도가 최종 판정한다.
        pass


def try_lock_exclusive(handle: IO[Any]) -> bool:
    """``handle`` 에 배타 락을 **즉시**(비차단) 시도한다.

    Args:
        handle: 이진 모드로 열린 파일 핸들 (Windows 는 바이너리가 필요하다 —
            텍스트 모드의 ``seek`` 가 바이트 오프셋을 정확히 보장하지 않는다).

    Returns:
        True — 락을 잡았다. False — 다른 주체가 이미 잡고 있다.

    Note:
        실패해도 예외를 내지 않는다 — "이미 잡혔다" 는 정상적인 경쟁 결과다.
        호출자가 재시도/대기 전략을 고를 수 있게 해야 한다.
    """
    if sys.platform == "win32":
        import msvcrt  # noqa: PLC0415 - Windows 전용

        try:
            handle.seek(WINDOWS_LOCK_OFFSET)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    import fcntl  # noqa: PLC0415 - POSIX 전용

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def lock_exclusive_blocking(handle: IO[Any], *, timeout: float | None = None,
                            interval: float = 0.05) -> bool:
    """배타 락을 **대기하며** 획득한다.

    Args:
        handle: 이진 모드로 열린 파일 핸들.
        timeout: 최대 대기 초. ``None`` 이면 무제한.
        interval: 재시도 간격(초).

    Returns:
        True — 획득했다. False — 타임아웃.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        if try_lock_exclusive(handle):
            return True
        if deadline is not None and time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def unlock(handle: IO[Any]) -> None:
    """잡았던 배타 락을 해제한다 (이미 풀렸거나 실패했으면 조용히 넘어간다)."""
    if sys.platform == "win32":
        import msvcrt  # noqa: PLC0415 - Windows 전용

        try:
            handle.seek(WINDOWS_LOCK_OFFSET)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except (OSError, ValueError):
            pass
        return

    import fcntl  # noqa: PLC0415 - POSIX 전용

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except (OSError, ValueError):
        pass


def lock_backend() -> str:
    """현재 플랫폼에서 쓰이는 락 백엔드 이름 — 진단·로그용."""
    return "msvcrt" if sys.platform == "win32" else "fcntl"
