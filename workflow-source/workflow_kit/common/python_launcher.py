"""플랫폼 관례의 Python 실행 파일 이름 — emit / preflight 가 공유하는 정본.

Windows 배포판(python.org 설치본, py launcher)은 ``python``/``py`` 만 두고
``python3`` 를 PATH 에 두지 않는 것이 관례다. emit 되는 MCP command 가
``python3`` 로 고정이던 동안 PATH 에 python3 이 없는 Windows 호스트에서 emit
설정으로 서버를 spawn 할 수 없었다 (TASK-2026-08-25-main-017, 2026-08-25 실측:
설치 preflight 6채널 전부 block 의 단일 주원인).

소유자 결정 (2026-08-25, 62차) = **플랫폼별 커맨드명**. ``sys.executable`` 파생은
머신 고유 절대 경로를 ``.mcp.json`` 류 *공유 파일*에 굽기 때문에 기각됐다 —
emit 의 '공유 파일에 절대 경로 금지' 계약(:func:`workflow_kit.bootstrap_lib.mcp.
_mcp_server_env` docstring)을 지키는 보수적 수리다.

체크인되는 산출물(플러그인 payload · 하네스 예시 문서)은 렌더 호스트와 무관하게
같은 내용이어야 한다 — payload 는 해시로 드리프트를 재므로 호스트마다 내용이
갈리면 그 비교가 무너진다. 그쪽 호출자는 ``platform="posix"`` 를 명시해 고정한다.
"""

from __future__ import annotations

import sys

#: POSIX 관례의 Python 실행 파일 이름 — 체크인 산출물이 고정하는 값이기도 하다.
POSIX_PYTHON = "python3"
#: Windows 관례의 Python 실행 파일 이름.
WIN32_PYTHON = "python"


def python_launcher(platform: str | None = None) -> str:
    """플랫폼 관례의 Python 실행 파일 이름을 돌려준다.

    Args:
        platform: ``sys.platform`` 형식의 플랫폼 문자열. ``None`` 이면 현재
            호스트 (bootstrap emit 이 쓰는 기본값). 체크인 산출물 렌더러는
            ``"posix"`` 를 명시해 호스트 독립성을 고정한다.
    """
    plat = sys.platform if platform is None else platform
    return WIN32_PYTHON if plat == "win32" else POSIX_PYTHON


__all__ = ["POSIX_PYTHON", "WIN32_PYTHON", "python_launcher"]
