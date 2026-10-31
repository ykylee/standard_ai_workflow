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


#: POSIX 최소 PATH — ``git`` · ``sh`` 가 있는 표준 위치.
POSIX_TOOL_PATH = "/usr/bin:/bin:/usr/local/bin"


def home_env(home: Path | str | None = None) -> dict[str, str]:
    """홈을 격리한 환경 조각 — POSIX 는 ``HOME``, Windows 는 ``HOME`` + ``USERPROFILE``.

    ``ntpath.expanduser`` 는 ``HOME`` 을 **읽지 않는다** — ``USERPROFILE``(또는
    ``HOMEDRIVE``+``HOMEPATH``) 가 있어야 하고, 둘 다 없으면 ``Path.home()`` 이
    ``RuntimeError`` 로 죽는다 (2026-10-31 Windows 실측). 그래서 두 키를 같은 값으로
    함께 준다 — 어느 플랫폼에서든 "이 자식의 홈은 이 디렉터리" 를 뜻한다.
    """
    if home is not None:
        target = str(home)
    else:
        target = os.environ.get("USERPROFILE") or os.environ.get("HOME") or os.path.expanduser("~")
    return {"HOME": target, "USERPROFILE": target}


def tool_path(posix_default: str = POSIX_TOOL_PATH) -> str:
    """자식에게 줄 ``PATH`` — Windows 는 상속, POSIX 는 호출자가 준 최소 경로.

    ``git.exe`` 는 ``/usr/bin`` 에 없다. POSIX 최소 PATH 를 그대로 주면 git 을 못
    찾아 그 git 을 쓰는 검사 전체가 성립하지 않는다. Windows 는 상속 PATH 로 대체하고,
    POSIX 는 호출자가 원하던 값을 그대로 쓴다 — 플랫폼 판정을 바꾸지 않는다.
    """
    if os.name == "nt":
        return os.environ.get("PATH", "")
    return posix_default


def platform_child_env(home: Path | str | None = None, *, path: str = POSIX_TOOL_PATH,
                        **extra: str) -> dict[str, str]:
    """Windows 에서도 성립하는 자식 환경 — 홈 격리 · UTF-8 · 도구 PATH.

    자식 프로세스는 파이프 stdout 을 로캘 인코딩(cp949 등)으로 쓴다. ``—``(U+2014) ·
    ``✅`` 같은 문자가 없으면 출력 도중 ``UnicodeEncodeError`` 로 죽는다. 자식이 UTF-8
    로 말하게 한다 (``PYTHONUTF8=1`` — ``scripts/cross_platform_cli_probe.py`` 와 같은
    관례).

    판정(허용/기각)은 바꾸지 않는다 — 환경만 그 플랫폼에서 성립하는 값으로 맞춘다.
    """
    env = {
        **home_env(home),
        "PATH": tool_path(path),
        "PYTHONUTF8": "1",
    }
    env.update(extra)
    return env


def platform_env(base: dict[str, str], home: Path | str | None = None) -> dict[str, str]:
    """기존 최소 환경 dict 에 플랫폼 조각을 덧댄다 — ``PATH`` 는 **건드리지 않는다**.

    ``PATH`` 를 건드리는 게 의도인 경우(자식이 git 같은 도구를 찾아야 한다면
    :func:`tool_path` 로 Windows 에서 상속으로 바꿔야 한다)에는 ``base`` 를 만들 때
    직접 바꿔서 넘긴다. 여기서는 격리하고 싶은 ``PATH=""`` · ``"/nonexistent"`` 같은
    **고정값**을 조용히 무너뜨리지 않는다.
    """
    env = {**base}
    env.update(home_env(home))
    env["PYTHONUTF8"] = "1"
    return env
