"""JSON / text file 의 atomic write helper (v0.7.15+).

SSOT 갱신 시 file write 의 *interrupted-write* 문제 (power loss, kill -9, mid-write crash)
해소. POSIX 의 `os.replace` 가 atomic (rename(2) 의 same-filesystem variant) 이므로:

    1. tempfile.NamedTemporaryFile 에 write
    2. fsync 로 disk 에 영구 기록
    3. os.replace(tmp, target) — atomic on POSIX

중간에 crash 나도 target file 은 *이전 version* 또는 *없음* 상태 보장. 둘 다 valid.

본 helper 는 SSOT JSON (state.json / work_backlog.md 등) 의 write caller 가 사용.

Usage:
    from workflow_kit.common.atomic_write import atomic_write_json, atomic_write_text

    atomic_write_json(state_path, {"session": {...}, "memory": {...}})
    atomic_write_text(notes_path, body)

Reference:
- POSIX rename(2): https://man7.org/linux/man-pages/man2/rename.2.html (atomic on same FS)
- Python os.replace: 3.3+ atomic on POSIX, may not be atomic on Windows
- v0.7.15 release note: SSOT (state.json, work_backlog.md) 의 interrupted-write issue
  발견 → 본 helper 도입
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def existing_newline(path: Path) -> str:
    """쓸 대상이 **이미 있으면 그 파일의 줄바꿈**을, 없으면 LF 를 돌려준다.

    저장소는 **혼재 상태**다 — 어떤 파일은 CRLF(Windows 호스트가 쓴 것이 남아 있고)
    어떤 파일은 LF 다. 파일을 다시 쓸 때 개행을 바꾸면 *내용은 같은데 바이트가
    달라진다*. git 은 `text=auto` 로 정규화해 그 차이를 감추지만, 읽는 쪽과
    **바이트 대조**(plugin payload → 소비측 복사, 해시 비교)는 본다 — 그래서
    뒤집힌 개행은 "오른 것 같고 실제로는 다른 파일" 이 된다.

    그래서 규칙은 하나다:

    - **대상이 이미 있으면 그 파일의 관례를 지킨다** (CRLF 파일은 CRLF 로 쓴다).
    - **새 파일이면 LF** — 저장소 표준(`.gitattributes` 의 `* text=auto eol=lf`).

    2026-10-31 실측: 이 규칙이 없으면 툴이 돌 때마다 파일의 개행이 뒤집힌다 —
    Windows 에서 쓴 CRLF task 파일이 정본 writer 의 LF 고정 때문에 CRLF→LF 로
    바뀌었다.
    """
    try:
        with path.open("rb") as fp:
            head = fp.read(8192)
    except OSError:
        return "\n"
    return "\r\n" if b"\r\n" in head else "\n"


def atomic_write_json(
    path: Path | str,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """JSON file 을 atomic 하게 작성. POSIX guarantee (os.replace).

    개행은 **대상 파일의 관례를 따른다** — 이미 있으면 그 파일의 관례,
    없으면 LF. (:func:`existing_newline` 참고)

    Args:
        path: target file path. parent dir 없으면 생성.
        data: json.dump 가능 dict / list / scalar.
        indent: JSON indent (default 2).
        ensure_ascii: json.dump 의 ensure_ascii (default False; 한글 등 보존).

    Raises:
        OSError: parent dir 생성 실패 / disk full / permission 등.
        TypeError: data 가 JSON-serializable 아닐 시.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    newline = existing_newline(path)

    # tmp file in same dir (same filesystem → os.replace atomic)
    fd, tmp_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        # `newline` — Windows 텍스트 모드는 `\n` 을 `os.linesep`(=CRLF) 로 번역한다.
        # `newline` 를 명시하지 않으면 **호스트마다 다른 바이트**가 된다 — 같은
        # 산출물이 POSIX 에선 LF · Windows 에선 CRLF 라 해시·비교가 갈린다
        # (TASK-2026-10-31-main-003 — 한글 Windows 프로필).
        # 무엇을 명시하느냐가 곧 "개행을 덮어쓸까" 결정이다:
        #   - LF 고정 → 기존 CRLF 파일이 **LF 로 뒤집힌다** (2026-10-31 실측).
        #   - 관례 보존 → 기존 파일은 그대로, 신규 파일만 LF.
        # 그래서 대상 파일의 관례를 먼저 읽는다 (:func:`existing_newline`).
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            try:
                os.fsync(f.fileno())  # ensure data hits disk before rename
            except OSError:
                # fsync may fail on some filesystems; non-fatal (best-effort)
                pass
        os.replace(tmp_str, path)
    except Exception:
        # cleanup tmp file on any failure
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise


def atomic_write_text(
    path: Path | str,
    body: str,
    *,
    encoding: str = "utf-8",
) -> None:
    """Text file 을 atomic 하게 작성. POSIX guarantee (os.replace).

    개행은 **대상 파일의 관례를 따른다** — 이미 있으면 그 파일의 관례,
    없으면 LF. (:func:`existing_newline` 참고)

    Args:
        path: target file path.
        body: file 본문.
        encoding: file encoding (default utf-8).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    newline = existing_newline(path)

    fd, tmp_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        # `newline` — 위 `atomic_write_json` 과 같은 이유. Windows 텍스트 모드의
        # CRLF 번역을 막되, **기존 파일의 관례까지 덮어쓰진 않는다**.
        # 기존 CRLF 파일이 LF 로 뒤집히면 "내용은 같은데 바이트가 다른 파일"이
        # 되어 consumer 측 바이트 대조(plugin payload → 설치본 복사)와
        # git worktree 상태가 어긋난다 (2026-10-31 실측).
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(body)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp_str, path)
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise
