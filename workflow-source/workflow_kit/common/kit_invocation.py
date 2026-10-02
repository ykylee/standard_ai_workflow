"""kit 호출 형태의 정본 — ``python -m workflow_kit <command>``.

TASK-2026-10-02-main-007. 하네스가 kit 를 부르는 형태를 ``wk`` 실행 파일에서
**모듈 실행**으로 옮겼다. pip 의 console-script 런처(``wk.exe``)는 Windows 에서 설치마다
새로 생성되는 서명 없는 실행 파일이라, 평판 기반 백신(실측: AhnLab V3)이 차단한다.

- **에이전트에게 보이는 명령**(정본 §11.1 표 · 스킬 · 진입점 블록)은
  :data:`KIT_INVOCATION` 형태다. 해석기 이름은 플랫폼마다 다르다(Windows ``python`` ·
  POSIX 대개 ``python3``) — 그 안내는 정본 §11 의 bullet 이 싣는다.
- **hook 명령**은 사람이 읽지 않고 그대로 실행된다. 그래서 이름을 고정하지 않고
  :data:`HOOK_INTERPRETERS` 를 차례로 시험해 ``workflow_kit`` 를 import 할 수 있는
  첫 해석기를 쓴다 (:func:`posix_interpreter_probe`). PATH 의 ``python`` 이 kit 를 깐
  해석기라는 보장은 없다 — 다른 Python, Windows Store 별칭일 수 있다.

``wk`` console-script 는 남겨 둔다 (POSIX 사람 사용자의 단축형). 하네스 산출물만 쓰지 않는다.
"""

from __future__ import annotations

#: kit 의 실행 모듈 (``workflow_kit/__main__.py``).
KIT_MODULE = "workflow_kit"
#: 에이전트에게 보이는 호출 접두. 정본 §11.1 표의 명령이 이 접두로 시작한다.
KIT_INVOCATION = f"python -m {KIT_MODULE}"
#: hook 이 시험하는 해석기 순서. POSIX 관례(``python3``) 먼저 — Windows 의 ``python3`` 는
#: 대개 Store 별칭이라 import 탐침에서 떨어지고 ``python`` 으로 넘어간다.
HOOK_INTERPRETERS = ("python3", "python")
#: hook 셸에서 고른 해석기를 담는 변수 이름.
HOOK_PY_VAR = "py"


def kit_subcommand(command: str) -> str:
    """정본 명령에서 kit 하위 명령(+인자)을 꺼낸다 — ``python -m workflow_kit X`` → ``X``.

    접두가 다르면 :class:`ValueError` — 정본이 다른 형태로 바뀐 것을 조용히 넘기지 않는다.
    """
    prefix = KIT_INVOCATION + " "
    if not command.startswith(prefix):
        raise ValueError(f"kit 명령이 {KIT_INVOCATION!r} 로 시작하지 않는다: {command!r}")
    return command[len(prefix):]


def posix_interpreter_probe() -> str:
    """``workflow_kit`` 를 import 할 수 있는 첫 해석기를 ``$py`` 에 담는 POSIX 셸 조각.

    못 찾으면 ``$py`` 는 빈 문자열이다. 뒤에 ``;`` 를 붙여 돌려준다.
    """
    candidates = " ".join(HOOK_INTERPRETERS)
    var = HOOK_PY_VAR
    return (
        f"for {var} in {candidates}; do "
        f"\"${var}\" -c 'import {KIT_MODULE}' >/dev/null 2>&1 && break; {var}=; done;"
    )


def posix_kit_call(subcommand: str) -> str:
    """탐침으로 고른 해석기로 kit 를 부르는 셸 조각 (탐침 뒤에 이어 쓴다)."""
    return f"\"${HOOK_PY_VAR}\" -m {KIT_MODULE} {subcommand}"


def posix_kit_found() -> str:
    """탐침이 해석기를 찾았는지의 셸 조건식."""
    return f"[ -n \"${HOOK_PY_VAR}\" ]"


__all__ = [
    "HOOK_INTERPRETERS",
    "HOOK_PY_VAR",
    "KIT_INVOCATION",
    "KIT_MODULE",
    "kit_subcommand",
    "posix_interpreter_probe",
    "posix_kit_call",
    "posix_kit_found",
]
