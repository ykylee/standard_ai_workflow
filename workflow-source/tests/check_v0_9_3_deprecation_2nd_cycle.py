"""v0.9.3 deprecation 2nd cycle verification test.

Acceptance criteria (workflow-source/core/v0_9_0_deprecation_policy_spec.md §3.6):
1. build_default_sources_v4() 호출 시 DeprecationWarning 1회 raise
2. simplefilter('error', DeprecationWarning) 환경에서도 raise (strict mode)
3. phishing_federation.build_default_sources 는 DeprecationWarning ❌
4. 두 함수 output byte-identical (zero behavior change regression)

2nd cycle scope = 1 symbol (`build_default_sources_v4`). 1st cycle 의 *같은
module* 의 *다른 public function*. dispatcher (`cmd_federate`) 가 이미
`phishing_federation.build_default_sources` (consolidated) 사용 중 = v4 module
자체가 unused → 1st cycle 의 *운영 검증 결과* 기반 2nd cycle 첫 symbol.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import warnings
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# workflow_kit namespace setup (mirrors check_v0_9_0_deprecation_1st_cycle.py)
_workflow_kit_pkg = types.ModuleType("workflow_kit")
_workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules.setdefault("workflow_kit", _workflow_kit_pkg)


def _load_module(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(
        name, str(WORKFLOW_KIT_DIR / file_name)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_deprecation_warning_raised_v0_9_3() -> None:
    """Acceptance §3.6 #1: DeprecationWarning 1회 raise per call."""
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = v4_mod.build_default_sources_v4()
    assert len(captured) == 1, (
        f"expected 1 DeprecationWarning, got {len(captured)}: "
        f"{[str(w.message) for w in captured]}"
    )
    assert captured[0].category is DeprecationWarning
    msg = str(captured[0].message)
    assert "build_default_sources_v4" in msg
    assert "phishing_federation.build_default_sources" in msg
    assert "v0.10.0" in msg
    # zero behavior change — default 1 source (OpenPhish only;
    # PhishTank 은 phishtank_api_key 부재 시 skip)
    assert isinstance(result, list)
    assert len(result) == 1, (
        f"expected 1 default source (OpenPhish), got {len(result)} (zero behavior change)"
    )


def test_deprecation_warning_strict_mode_v0_9_3() -> None:
    """Acceptance §3.6 #2: simplefilter('error', DeprecationWarning) 환경에서도 raise."""
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        try:
            v4_mod.build_default_sources_v4()
        except DeprecationWarning as e:
            assert "v0.10.0" in str(e)
            return
    raise AssertionError("DeprecationWarning was not raised under simplefilter('error')")


def test_consolidated_does_not_warn_v0_9_3() -> None:
    """Acceptance §3.6 #3: phishing_federation.build_default_sources 는 DeprecationWarning 발생 ❌."""
    fed_mod = _load_module("phishing_federation", "phishing_federation.py")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fed_mod.build_default_sources()
    deprecation_warnings = [
        w for w in captured if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warnings == [], (
        f"consolidated function raised unexpected DeprecationWarning: "
        f"{[str(w.message) for w in deprecation_warnings]}"
    )


def test_output_equivalent_to_consolidated_v0_9_3() -> None:
    """Acceptance §3.6 #4: build_default_sources_v4 와 phishing_federation.build_default_sources 의
    출력 동등 (regression test, zero behavior change).

    Callable 의 identity 비교는 위험 (v4 는 lambda 로 매번 새 instance).
    length + weight (float) 만 비교.
    """
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    fed_mod = _load_module("phishing_federation", "phishing_federation.py")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        v4_result = v4_mod.build_default_sources_v4()
    new_result = fed_mod.build_default_sources()
    # 두 함수 의 output 은 list[tuple[Callable, float]] 형식.
    assert len(v4_result) == len(new_result), (
        f"length diverged: v4={len(v4_result)} vs new={len(new_result)}"
    )
    for v4_item, new_item in zip(v4_result, new_result):
        assert len(v4_item) == len(new_item) == 2
        # weight (float) 비교 — callable identity 비교 안 함 (v4 의 lambda)
        assert abs(v4_item[1] - new_item[1]) < 0.001, (
            f"weight diverged: v4={v4_item[1]} vs new={new_item[1]}"
        )


def main() -> int:
    test_funcs = [
        test_deprecation_warning_raised_v0_9_3,
        test_deprecation_warning_strict_mode_v0_9_3,
        test_consolidated_does_not_warn_v0_9_3,
        test_output_equivalent_to_consolidated_v0_9_3,
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
