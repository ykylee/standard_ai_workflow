"""자식 프로세스로 **이 패키지의 도구를 다시 부를 때** 쓰는 정본 helper.

## 왜 필요한가 (TASK-2026-08-18-main-003)

여러 도구가 다른 도구를 subprocess 로 부르면서 **파일 경로**를 조립했다::

    [sys.executable, str(SOURCE_ROOT / "workflow_kit" / "tools" / "x.py"), ...]

``SOURCE_ROOT`` 는 모듈 파일 위치에서 역산한 ``<repo>/workflow-source`` 다. 저장소
체크아웃에서는 맞지만 소비자는 **wheel 로 설치**하므로 그런 디렉터리가 없다. 개발
호스트의 ``wk`` 는 editable 설치라 우연히 맞아서, 이 어긋남이 로컬에서는 영원히
드러나지 않았다 (2026-08-18 실측: 비-editable wheel 에서 ``REPO_ROOT`` 가
``<venv>/lib/python3.x`` 로 잡혔다).

정공법은 **모듈로 부르는 것**이다 (``python -m workflow_kit.tools.x``). 설치본이든
체크아웃이든 import 규칙 하나로 풀린다. 체크아웃에서 패키지를 설치하지 않고 직접
실행하는 경우를 위해 ``PYTHONPATH`` 에 패키지의 부모 디렉터리를 얹는다.

규칙을 여기 한 곳에만 둔다 — 복사해 둔 caller 가 레이아웃 변경을 놓치는 것이 원래
결함의 형태였다.
"""

from __future__ import annotations

import os
from pathlib import Path

#: ``workflow_kit`` 패키지를 담은 디렉터리.
#: 저장소면 ``workflow-source/``, 설치본이면 site-packages.
PACKAGE_PARENT = Path(__file__).resolve().parents[2]


def module_command(module: str, *args: str, python: str | None = None) -> list[str]:
    """``python -m <module> <args...>`` 명령줄.

    Args:
        module: dotted module path (예: ``workflow_kit.tools.refresh_state``).
        args: 그대로 이어 붙일 인자.
        python: 인터프리터. 기본은 현재 프로세스의 것.
    """
    import sys
    return [python or sys.executable, "-m", module, *args]


def child_env(extra: dict[str, str] | None = None, *, base: dict[str, str] | None = None) -> dict[str, str]:
    """자식 프로세스 환경 — ``PYTHONPATH`` 앞에 :data:`PACKAGE_PARENT` 를 얹는다.

    Args:
        extra: 덮어쓸 키.
        base: 시작 환경. 기본은 ``os.environ`` 전체. 환경을 좁히려는 caller
            (예: ``claim_workspace``) 는 최소 dict 를 넘긴다.
    """
    env = {**(os.environ if base is None else base)}
    if extra:
        env.update(extra)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{PACKAGE_PARENT}{os.pathsep}{existing}" if existing else str(PACKAGE_PARENT)
    )
    return env
