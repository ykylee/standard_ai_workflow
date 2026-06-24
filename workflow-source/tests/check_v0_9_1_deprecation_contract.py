"""v0.9.1 deprecation policy contract test.

workflow-source/core/v0_9_0_deprecation_policy_spec.md §3.2 의 contract:
workflow_kit.__all__ 의 모든 public symbol 이 다음 중 하나여야 한다:
1. **deprecation-free**: call 시 DeprecationWarning raise 안 함 (정상)
2. **deprecation-marked**: call 시 DeprecationWarning raise (의도적 표시)

contract = "예외 없이" 정합. *untracked deprecation* (deprecation 의도 없이
DeprecationWarning raise) 또는 *silent deprecation* (DeprecationWarning raise
해야 하는데 안 함) 모두 contract 위반.

v0.9.1 chapter 5 deliverable: contract test 로 deprecation policy 의 *운영 검증*
자동화. spec §7.2 chapter 2 의 1st cycle verify 와 별개로, *전체* public surface
에 대한 *meta-contract*.

**v0.10.0 갱신**: 1st cycle (`fetch_federated_phishing_urls_v4`) + 2nd cycle
(`build_default_sources_v4`) 동시 종료 (spec §3.5/§3.6 removal column ✅ v0.10.0).
DEPRECATION_MARKED_CALLABLES whitelist 가 empty 가 정합. phishing_federation_v4
가 `__all__` 에서 제거 + file 자체 delete. consumer 가 *명시적 except* 없으면
hard fail (ImportError).
"""
from __future__ import annotations

import importlib
import re
import sys
import warnings
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"
WORKFLOW_KIT_INIT = WORKFLOW_KIT_DIR / "__init__.py"


# v0.10.0 갱신: 1st cycle (v0.9.0) + 2nd cycle (v0.9.3) 동시 종료.
# spec §3.5/§3.6 의 removal column = "v0.10.0 ✅". 본 whitelist 는 empty 가 정합.
# 다음 deprecation cycle 진입 시 새 entry 추가 (같은 정공법: 1 release DeprecationWarning → 1 release removal).
DEPRECATION_MARKED_CALLABLES: dict[str, tuple[str, tuple, dict]] = {
    # v0.10.0 정합: empty (1st + 2nd cycle 동시 종료)
    # 다음 deprecation cycle 의 placeholder 예시:
    # "workflow_kit.<future_module>.<future_callable>": (
    #     "workflow_kit.<replacement_module>.<replacement_callable>",
    #     (args,),  # invoke args
    #     {},  # invoke kwargs
    # ),
}


def _parse_all_list(init_path: Path) -> list[str]:
    """workflow_kit/__init__.py 의 __all__ literal 추출.

    stub namespace setup (test file 의 다른 test 에서 사용) 이 __init__ 실행을
    가로채므로, static parse 로 __all__ list 를 직접 검증.
    """
    src = init_path.read_text()
    m = re.search(r"^__all__\s*:\s*list\[str\]\s*=\s*\[(.+?)\]", src, re.S | re.M)
    assert m is not None, (
        f"could not parse __all__ literal from {init_path} (test fixture broken)"
    )
    return re.findall(r'"([^"]+)"', m.group(1))


def _safe_call_with_warning_capture(callable_obj, args: tuple, kwargs: dict) -> list[warnings.WarningMessage]:
    """callable 을 호출하면서 발생하는 모든 DeprecationWarning capture."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        try:
            callable_obj(*args, **kwargs)
        except Exception:
            # callable 이 *의도적으로* raise 할 수 있음 (예: invalid input). warning capture 만 관심.
            pass
    return [w for w in captured if issubclass(w.category, DeprecationWarning)]


def test_all_list_parse_v0_9_1() -> None:
    """__all__ list 가 parse 가능 + 최소 1개 entry.

    **v0.10.0 갱신**: 1st + 2nd cycle 동시 종료로 `phishing_federation_v4` 가
    `__all__` 에서 제거. `phishing_federation` (consolidated) 은 유지.
    """
    all_list = _parse_all_list(WORKFLOW_KIT_INIT)
    assert len(all_list) >= 1, f"__all__ is empty: {WORKFLOW_KIT_INIT}"
    # v0.10.0 정합: phishing_federation_v4 NOT in __all__ (deprecation cycle 종료)
    assert "phishing_federation_v4" not in all_list, (
        f"v0.10.0 정합: phishing_federation_v4 는 __all__ 에서 제거되어야 함. "
        f"__all__ = {all_list}"
    )
    # phishing_federation (consolidated, v0.7.52+) 은 유지
    assert "phishing_federation" in all_list


def test_deprecation_marked_callables_warn_v0_9_1() -> None:
    """DEPRECATION_MARKED_CALLABLES 의 모든 callable 이 DeprecationWarning raise.

    **v0.10.0 갱신**: whitelist empty → loop no-op → 즉시 PASS (cycle 종료 정합).
    다음 deprecation cycle 진입 시 entry 추가 (1 release DeprecationWarning → 1 release removal).
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    # v0.10.0 정합: whitelist empty 이므로 loop body 0회 실행
    for full_name, (replacement, args, kwargs) in DEPRECATION_MARKED_CALLABLES.items():
        module_path, callable_name = full_name.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        func = getattr(mod, callable_name)
        captured = _safe_call_with_warning_capture(func, args, kwargs)
        assert len(captured) >= 1, (
            f"{full_name} did not raise DeprecationWarning "
            f"(deprecation marker missing or removed prematurely)"
        )
        msg = str(captured[0].message)
        assert "deprecated" in msg.lower(), f"missing 'deprecated' in: {msg}"
        # removal release 명시 (다음 cycle 시 dynamic)
        assert "v0." in msg, f"missing removal release 'v0.X.Y' in: {msg}"


def test_non_deprecated_callables_no_warning_v0_9_1() -> None:
    """DEPRECATION_MARKED_CALLABLES 에 *없는* callable 이 DeprecationWarning raise 하면 contract 위반.

    chapter 2 의 1st cycle 이후, fetch_federated_phishing_urls (consolidated) 는
    DeprecationWarning raise ❌. 본 test 가 이 contract 를 verify.
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    # phishing_federation.fetch_federated_phishing_urls (consolidated, no deprecation)
    mod = importlib.import_module("workflow_kit.phishing_federation")
    captured = _safe_call_with_warning_capture(
        mod.fetch_federated_phishing_urls, ([],), {}
    )
    deprecation_warns = [
        w for w in captured if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warns == [], (
        f"workflow_kit.phishing_federation.fetch_federated_phishing_urls "
        f"raised unexpected DeprecationWarning: "
        f"{[str(w.message) for w in deprecation_warns]}"
    )


def test_all_symbols_resolvable_v0_9_1() -> None:
    """__all__ 의 모든 symbol 이 실제로 import 가능.

    contract: __all__ 의 모든 entry 가 실제로 module attribute 로 존재.
    typo 또는 누락 시 *implicit import error* 가 발생하므로, contract test 가
    *compile-time* 정합 verify.
    """
    all_list = _parse_all_list(WORKFLOW_KIT_INIT)
    # workflow_kit package 자체는 import
    sys.path.insert(0, str(SOURCE_ROOT))
    pkg = importlib.import_module("workflow_kit")
    missing: list[str] = []
    for name in all_list:
        if name == "__version__":
            # __version__ 는 pkg attribute
            assert hasattr(pkg, "__version__"), f"workflow_kit missing __version__"
            continue
        if not hasattr(pkg, name):
            missing.append(name)
    assert missing == [], f"__all__ entries missing in workflow_kit: {missing}"


def main() -> int:
    test_funcs = [
        test_all_list_parse_v0_9_1,
        test_deprecation_marked_callables_warn_v0_9_1,
        test_non_deprecated_callables_no_warning_v0_9_1,
        test_all_symbols_resolvable_v0_9_1,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())