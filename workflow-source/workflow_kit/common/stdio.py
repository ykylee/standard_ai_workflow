"""프로세스 stdio 를 UTF-8 로 고정한다 — Windows 로캘 인코딩(cp949 등) 대응.

TASK-2026-10-02-main-006. Windows 에서 stdio 가 **파이프**이면(하네스가 `wk` 를
subprocess 로 부르는 경우 — OpenCode 데스크톱 · Codex hook 등) Python 은 로캘
인코딩으로 읽고 쓴다. 한국어 Windows 라면 cp949 이고, cp949 에는 `—`(U+2014) ·
`✅` 같은 문자가 없다. 그래서 출력 도중 `UnicodeEncodeError` 로 죽는다 (exit 2).
콘솔에 직접 붙은 경우는 Python 이 UTF-16 콘솔 API 를 써서 안 나므로, 터미널에서
손으로 돌리면 재현되지 않는다.

하네스(Node 기반 OpenCode · Claude Code 등)는 자식 출력을 UTF-8 로 읽는다. 그래서
로캘을 따르는 대신 UTF-8 로 맞춘다. stdin 도 같은 이유로 맞춘다 — hook payload JSON 은
UTF-8 로 들어온다.

파일 · subprocess 텍스트 I/O 의 기본 인코딩은 이 함수가 바꾸지 못한다 (UTF-8 mode 는
인터프리터 시작 시에만 켜진다). 그쪽은 호출마다 `encoding=` 을 명시하고
`tests/check_text_io_encoding.py` 가 강제한다.

적용 범위: `wk` 진입점과 하네스가 `python -m` 으로 부르는 모듈의 `__main__`.
`workflow-<name>` 개별 binary(A안)는 하네스가 부르지 않아 대상이 아니다.
"""

from __future__ import annotations

import io
import sys


def force_utf8_stdio() -> list[str]:
    """stdin/stdout/stderr 가 UTF-8 이 아니면 UTF-8 로 재설정한다.

    `TextIOWrapper` 가 아닌 스트림(테스트의 StringIO · None)은 건드리지 않는다.
    바꾼 스트림 이름을 돌려준다 — 이미 UTF-8 이면 빈 목록.
    """
    changed: list[str] = []
    for name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, name, None)
        if not isinstance(stream, io.TextIOWrapper):
            continue
        encoding = (stream.encoding or "").lower().replace("_", "-")
        if encoding in ("utf-8", "utf8"):
            continue
        # 출력 쪽은 errors 를 보존한다 (stderr 는 기본 backslashreplace).
        # 입력 쪽은 깨진 바이트로 죽기보다 대체 문자로 받는다.
        errors = "replace" if name == "stdin" else stream.errors
        stream.reconfigure(encoding="utf-8", errors=errors)
        changed.append(name)
    return changed
