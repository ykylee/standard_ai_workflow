"""mkdocs 설정이 **실제로 로드 가능한가** (v1.0.1+).

## 왜 필요한가

`mkdocs.yml` 이 이렇게 적혀 있었다:

    plugins:
      - search
      - tools.mkdocs_git_dates:GitDatesPlugin

그리고 workflow 는 `PYTHONPATH=workflow-source` 를 주며 주석에 "plugin import 가능하게"
라고 적어 두었다. 그러나 mkdocs 는 `plugins:` 항목을 **`mkdocs.plugins` entry point
이름** 으로만 해석한다 (`mkdocs.plugins.get_plugins()` → `entry_points(group=...)`).
import 경로가 아니다. 그래서 그 줄은 *이름* 으로 취급됐고 build 는 매번

    ERROR - Config value 'plugins': The "tools.mkdocs_git_dates:GitDatesPlugin"
            plugin is not installed

로 중단됐다. **최근 100회 실행 중 성공 0회** — 문서 사이트가 한 번도 배포되지 않았다.
(덧붙여 그 클래스는 `BasePlugin` 을 상속하지도 않아 entry point 를 등록했어도 거부됐다.)

가장 나쁜 점은 이것이 *조용히* 잘못됐다는 것이다. 설정은 그럴듯해 보였고, 로컬에서
`mkdocs build` 를 돌려 보지 않으면 드러나지 않으며, CI 는 red 였지만 아무도 보지 않았다.

## 판정 규칙

`mkdocs build` 를 돌리려면 mkdocs 설치가 필요해 smoke 에 넣기엔 무겁다. 대신 **로드
가능성의 필요조건** 만 mkdocs 없이 검사한다:

1. `plugins:` 의 각 항목은 **entry point 이름**이어야 한다 — `module.path:Class` 모양은
   절대 로드되지 않으므로 즉시 fail.
2. `hooks:` 의 각 경로는 실재해야 한다.
3. hook 모듈은 mkdocs event 함수를 **module level** 로 최소 1개 노출해야 한다
   (클래스 메서드만 있으면 hook 으로 호출되지 않는다).

Test list (4 case):
1. test_plugins_are_entry_point_names   ← 원래 결함을 직접 잡는다
2. test_hook_paths_exist
3. test_hook_modules_expose_events
4. test_detector_catches_injected_regression  ← 탐지기 자체가 동작하는가

Cross-ref: releases/Beta-v1.0.0.md §2.28.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"

# mkdocs plugin/hook event 이름 (전수는 아니고, 이 저장소가 쓰는 것 + 대표적인 것).
MKDOCS_EVENT_NAMES = {
    "on_config", "on_files", "on_nav", "on_env", "on_serve", "on_startup", "on_shutdown",
    "on_pre_build", "on_post_build", "on_build_error",
    "on_pre_template", "on_template_context", "on_post_template",
    "on_pre_page", "on_page_read_source", "on_page_markdown",
    "on_page_content", "on_page_context", "on_post_page",
}


def _read_yaml_block(text: str, key: str) -> list[str]:
    """`key:` 아래의 `  - value` 항목들을 뽑는다 (PyYAML 의존 없이).

    mkdocs.yml 은 이 저장소에서 단순한 형태만 쓴다. YAML 파서를 끌어오는 대신
    필요한 최소한만 읽는다 — 이 check 는 의존성 없이 항상 돌아야 한다.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_block = False
    for line in lines:
        if re.match(rf"^{re.escape(key)}:\s*$", line):
            in_block = True
            continue
        if in_block:
            if re.match(r"^\s*#", line) or not line.strip():
                continue
            m = re.match(r"^\s+-\s+(.+?)\s*$", line)
            if m:
                out.append(m.group(1))
                continue
            # 들여쓰기가 끝나면 블록 종료
            if not line.startswith((" ", "\t")):
                break
    return out


def _module_level_event_names(path: Path) -> set[str]:
    """모듈 **최상위** 에 정의된 mkdocs event 함수 이름 집합."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:  # 최상위만 — 클래스 메서드는 hook 으로 호출되지 않는다
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in MKDOCS_EVENT_NAMES:
                names.add(node.name)
    return names


def _plugin_entries() -> list[str]:
    return _read_yaml_block(MKDOCS_YML.read_text(encoding="utf-8"), "plugins")


def _hook_entries() -> list[str]:
    return _read_yaml_block(MKDOCS_YML.read_text(encoding="utf-8"), "hooks")


def test_plugins_are_entry_point_names() -> bool:
    """1) `plugins:` 항목이 entry point 이름 모양인가 (`module:Class` ❌)."""
    bad = [p for p in _plugin_entries() if ":" in p or "/" in p or p.endswith(".py")]
    if bad:
        print(f"  FAIL: plugins 에 entry point 이름이 아닌 항목: {bad}")
        print("        mkdocs 는 plugins 를 entry point 이름으로만 해석한다 — "
              "파일/모듈 경로는 hooks: 로 옮겨야 한다.")
        return False
    print(f"  PASS: plugins {_plugin_entries()} 모두 entry point 이름 모양")
    return True


def test_hook_paths_exist() -> bool:
    """2) `hooks:` 의 각 경로가 실재하는가."""
    entries = _hook_entries()
    if not entries:
        print("  PASS: hooks 미사용 (검사 대상 없음)")
        return True
    missing = [h for h in entries if not (REPO_ROOT / h).is_file()]
    if missing:
        print(f"  FAIL: hooks 경로 부재: {missing}")
        return False
    print(f"  PASS: hooks {len(entries)}개 경로 모두 실재")
    return True


def test_hook_modules_expose_events() -> bool:
    """3) hook 모듈이 module-level event 함수를 노출하는가.

    클래스 메서드만 있으면 mkdocs 가 호출하지 않는다 — 조용히 아무 일도 안 한다.
    """
    ok = True
    for h in _hook_entries():
        path = REPO_ROOT / h
        if not path.is_file():
            continue
        events = _module_level_event_names(path)
        if not events:
            print(f"  FAIL: {h} 에 module-level mkdocs event 함수가 없다 "
                  "(클래스 메서드만 있으면 hook 으로 호출되지 않는다)")
            ok = False
        else:
            print(f"  [info] {h}: {sorted(events)}")
    if ok:
        print("  PASS: hook 모듈 모두 module-level event 노출")
    return ok


def test_detector_catches_injected_regression() -> bool:
    """4) 탐지기 자체가 동작하는가 — 원래 결함 모양을 주입해 잡히는지 확인."""
    injected = "plugins:\n  - search\n  - tools.mkdocs_git_dates:GitDatesPlugin\n\nextra:\n"
    entries = _read_yaml_block(injected, "plugins")
    if "tools.mkdocs_git_dates:GitDatesPlugin" not in entries:
        print(f"  FAIL: 주입한 항목을 파서가 읽지 못했다: {entries}")
        return False
    bad = [p for p in entries if ":" in p]
    if not bad:
        print("  FAIL: 탐지기가 `module:Class` 모양을 잡지 못한다")
        return False
    print(f"  PASS: 주입한 결함을 탐지 ({bad})")
    return True


def main() -> int:
    if not MKDOCS_YML.is_file():
        print(f"SKIP: {MKDOCS_YML} 부재")
        return 0
    cases = [
        ("test_plugins_are_entry_point_names", test_plugins_are_entry_point_names),
        ("test_hook_paths_exist", test_hook_paths_exist),
        ("test_hook_modules_expose_events", test_hook_modules_expose_events),
        ("test_detector_catches_injected_regression", test_detector_catches_injected_regression),
    ]
    results = [(name, fn()) for name, fn in cases]
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
