"""emit 되는 MCP command 가 **전 렌더러에서** 플랫폼 관례를 따르는지 훑는다.

TASK-2026-08-25-main-017 의 판정 공백을 닫는다. 62차가 정본
:mod:`workflow_kit.common.python_launcher` 를 세우고 `mcp_server_command` 를
플랫폼 분기시켰지만, 그것을 재는 검사는 **정본 함수를 직접** 부를 뿐이었다 —
`check_bootstrap_mcp_roundtrip.unit_checks` 의 docstring 이 스스로 적어 두었듯
"smoke 는 이 호스트의 산출물만 밟는다". 그래서 새 렌더러가 command 를 손으로
적어도(= 정본을 안 지나도) 그 자리는 red 가 되지 않는다. 사본은 반드시 갈라진다는
것이 이 저장소가 Grok 렌더러에서 이미 겪은 일이다 (`mcp.py::render_mcp_toml_block`
docstring, 2026-08-05).

여기서 재는 것은 함수가 아니라 **산출물**이다: 렌더러를 전부 돌려 emit 된 설정에서
command 를 꺼내고, 플랫폼을 강제한 채 그것이 관례와 맞는지 본다.

세 가지를 함께 고정한다:

1. **win32 강제** → emit 된 모든 command 가 ``python`` (PATH 에 python3 이 없는
   Windows 에서 서버를 spawn 할 수 있어야 한다 — 2026-08-25 실측의 원인).
2. **posix 강제** → 모두 ``python3``.
3. **체크인 산출물은 렌더 호스트와 무관**하다 — 플러그인 payload 는 win32 호스트에서
   렌더해도 ``python3`` 여야 한다. payload 는 해시로 드리프트를 재므로 호스트마다
   내용이 갈리면 그 비교가 무너진다.

**커버리지도 함께 잰다.** 추출이 아무것도 못 찾으면 검사는 조용히 통과한다 —
모름을 통과로 세지 않으려면 렌더러마다 command 를 **최소 1개** 찾았는지 확인해야
한다. 실제로 이 검사를 쓰다가 opencode 를 놓친 적이 있다 (command 가 문자열이
아니라 **리스트**라 문자열 전용 추출이 0건을 반환했고, 그 0건은 위반 0건과
구분되지 않았다). 그리고 모듈의 ``render_*_mcp_config`` 전수가 훑는 집합과 같은지
대조한다 — 등록을 빠뜨린 새 렌더러가 조용히 검사 밖에 남지 않도록.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

FAILURES: list[str] = []

#: TOML 방언의 ``command = "python3"`` 형태.
_TOML_CMD = re.compile(r'^\s*#?\s*command\s*=\s*"([^"]+)"', re.MULTILINE)


def _make_ns(target: Path) -> argparse.Namespace:
    return argparse.Namespace(
        target_root=str(target),
        kit_dir="ai-workflow",
        adoption_mode="new",
        entry_mode="safe",
        mcp_bridge="jsonrpc-bridge",
        today="2026-09-07",
    )


def _commands_in(rendered: object) -> list[str]:
    """emit 산출물에서 command 의 **실행 파일 이름**을 전부 꺼낸다.

    JSON 이면 구조를 타고, 아니면 TOML 방언을 정규식으로 읽는다. command 는
    문자열(``"python3"``)일 수도 리스트(``["python3", "-m", ...]``)일 수도 있어
    **둘 다** 받는다 — 한쪽만 보면 다른 쪽이 0건으로 조용히 통과한다.
    """
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "command":
                    if isinstance(value, str):
                        found.append(value)
                    elif isinstance(value, list) and value and isinstance(value[0], str):
                        found.append(value[0])
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    if isinstance(rendered, (dict, list)):
        walk(rendered)
        return found

    text = str(rendered)
    try:
        walk(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        pass
    found.extend(_TOML_CMD.findall(text))
    return found


def _sweep(platform_name: str) -> dict[str, list[str]]:
    """모든 emit 렌더러를 돌려 {렌더러: [command 이름]} 을 돌려준다."""
    from workflow_kit.bootstrap_lib import mcp as mcp_module
    from workflow_kit.bootstrap_lib.__main__ import make_paths
    from workflow_kit.common.python_launcher import python_launcher

    original = mcp_module.python_launcher
    # 전역 `sys.platform` 패치는 이 호스트의 다른 분기까지 흔든다 — 정본 해석기
    # 하나만 갈아 끼운다 (`check_deploy_doctor` 의 win32 case 와 같은 방식).
    mcp_module.python_launcher = (
        lambda platform=None: python_launcher(platform_name if platform is None else platform)
    )
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir()
            ns = _make_ns(root)
            paths = make_paths(ns)
            result: dict[str, list[str]] = {}
            for name, render in mcp_module.MCP_CONFIG_RENDERERS.items():
                result[name] = _commands_in(render(ns, paths))
            # mavis 는 project-local 산출물이 0이라 레지스트리 밖에 있다 (§6.5.2) —
            # 그래도 emit 경로이므로 함께 훑는다.
            result["mavis(global)"] = _commands_in(
                mcp_module.render_mavis_global_mcp_config(ns)
            )
            return result
    finally:
        mcp_module.python_launcher = original


def test_emitted_commands_follow_platform_convention() -> None:
    """case 1·2: win32 는 python, posix 는 python3 — emit 산출물에서 잰다."""
    from workflow_kit.common.python_launcher import POSIX_PYTHON, WIN32_PYTHON

    for platform_name, expected in (("win32", WIN32_PYTHON), ("linux", POSIX_PYTHON)):
        swept = _sweep(platform_name)
        for renderer, commands in sorted(swept.items()):
            if not commands:
                FAILURES.append(
                    f"[{platform_name}] {renderer}: command 를 한 개도 못 찾았다 — "
                    "추출이 눈멀었거나 렌더러가 형태를 바꿨다. 0건은 위반 0건이 아니다"
                )
                continue
            bad = [c for c in commands if c != expected]
            if bad:
                FAILURES.append(
                    f"[{platform_name}] {renderer}: 관례를 안 따르는 command {bad} "
                    f"(기대 {expected!r}) — 정본 python_launcher 를 안 지나는 사본이다"
                )
        print(f"  [{platform_name}] 렌더러 {len(swept)}개, command 전부 {expected!r}: OK")


def test_checked_in_payload_is_host_independent() -> None:
    """case 3: 체크인되는 payload 는 win32 호스트에서 렌더해도 posix 고정이다."""
    from workflow_kit.bootstrap_lib import mcp as mcp_module
    from workflow_kit.common.python_launcher import POSIX_PYTHON, python_launcher
    from workflow_kit.plugin_payload import _payload_mcp_entry

    original = mcp_module.python_launcher
    mcp_module.python_launcher = (
        lambda platform=None: python_launcher("win32" if platform is None else platform)
    )
    try:
        _, command = _payload_mcp_entry()
    finally:
        mcp_module.python_launcher = original

    if command[0] != POSIX_PYTHON:
        FAILURES.append(
            f"win32 호스트에서 렌더한 플러그인 payload 의 command 가 {command[0]!r} 다 — "
            f"체크인 산출물은 렌더 호스트와 무관하게 {POSIX_PYTHON!r} 여야 한다 "
            "(payload 해시 드리프트 비교가 무너진다)"
        )
    else:
        print(f"  체크인 payload 는 win32 렌더에서도 {POSIX_PYTHON!r} 고정: OK")


def test_every_renderer_is_swept() -> None:
    """case 4: 모듈의 render_*_mcp_config 전수가 훑는 집합과 같다."""
    from workflow_kit.bootstrap_lib import mcp as mcp_module

    defined = {
        name
        for name in dir(mcp_module)
        if name.startswith("render_") and name.endswith("_mcp_config")
    }
    registered = {
        f"render_{name.replace('-', '_')}_mcp_config"
        for name in mcp_module.MCP_CONFIG_RENDERERS
    }
    # mavis 는 레지스트리 밖이지만 _sweep 이 명시적으로 부른다.
    swept = registered | {"render_mavis_global_mcp_config"}

    missing = defined - swept
    if missing:
        FAILURES.append(
            f"훑지 않는 emit 렌더러가 있다: {sorted(missing)} — "
            "MCP_CONFIG_RENDERERS 에 등록하거나 _sweep 에 명시적으로 추가한다"
        )
    stale = swept - defined
    if stale:
        FAILURES.append(f"모듈에 없는 렌더러를 훑고 있다: {sorted(stale)}")
    if not missing and not stale:
        print(f"  emit 렌더러 {len(defined)}개 전부 이 검사의 사정권 안: OK")


def main() -> int:
    tests = [
        test_emitted_commands_follow_platform_convention,
        test_checked_in_payload_is_host_independent,
        test_every_renderer_is_swept,
    ]
    passed = 0
    for test in tests:
        print(f"[{test.__name__}]")
        before = len(FAILURES)
        try:
            test()
        except Exception as exc:  # noqa: BLE001 — 어떤 예외도 실패로 보고한다
            FAILURES.append(f"{test.__name__} 실행 중 예외: {type(exc).__name__}: {exc}")
        if len(FAILURES) == before:
            passed += 1
            print(f"  ✓ {test.__name__} PASS\n")
        else:
            for line in FAILURES[before:]:
                print(f"  ✗ {line}")
            print()
    print(f"=== Result: {passed}/{len(tests)} PASS ===")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
