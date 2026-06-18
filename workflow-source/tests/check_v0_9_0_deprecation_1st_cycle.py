"""v0.9.0 deprecation 1st cycle verification test.

Acceptance criteria (workflow-source/core/v0_9_0_deprecation_policy_spec.md §3.4, §7.2):
1. fetch_federated_phishing_urls_v4 호출 시 DeprecationWarning 1회 raise
2. phishing_federation.fetch_federated_phishing_urls 가 deprecation target 과
   *동일 출력* (regression test, zero behavior change)
3. phishing_federation_v4 가 __all__ 에 *그대로* 존재 (즉시 제거 ❌, v0.10.0 까지
   warning 만)
4. zero behavior change — 기존 check_phishing_federation.py 의 4 test 모두 동일
   결과
"""
from __future__ import annotations

import importlib.util
import sys
import types
import warnings
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# workflow_kit namespace setup (mirrors check_phishing_federation.py)
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


def _sample_sources():
    def s1():
        return ["https://a.com/", "https://b.com/"]

    def s2():
        return ["https://a.com/", "https://c.com/"]

    return [(s1, 1.0), (s2, 0.5)]


def test_deprecation_warning_raised_v0_9_0() -> None:
    """Acceptance §3.4 #1: DeprecationWarning 1회 raise per call."""
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = v4_mod.fetch_federated_phishing_urls_v4(_sample_sources())
    assert len(captured) == 1, (
        f"expected 1 DeprecationWarning, got {len(captured)}: "
        f"{[str(w.message) for w in captured]}"
    )
    assert captured[0].category is DeprecationWarning
    msg = str(captured[0].message)
    assert "fetch_federated_phishing_urls_v4" in msg
    assert "phishing_federation.fetch_federated_phishing_urls" in msg
    assert "v0.10.0" in msg
    # Stacklevel = 2 이므로 caller 가 정확히 v4 의 함수 호출 site
    assert result, "result must be non-empty (zero behavior change)"


def test_deprecation_warning_strict_mode_v0_9_0() -> None:
    """warnings.simplefilter('error', DeprecationWarning) 환경에서도 동작."""
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        try:
            v4_mod.fetch_federated_phishing_urls_v4(_sample_sources())
        except DeprecationWarning as e:
            assert "v0.10.0" in str(e)
            return
    raise AssertionError("DeprecationWarning was not raised under simplefilter('error')")


def test_consolidated_does_not_warn_v0_9_0() -> None:
    """phishing_federation.fetch_federated_phishing_urls 는 DeprecationWarning 발생 ❌."""
    fed_mod = _load_module("phishing_federation", "phishing_federation.py")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fed_mod.fetch_federated_phishing_urls(_sample_sources())
    deprecation_warnings = [
        w for w in captured if issubclass(w.category, DeprecationWarning)
    ]
    assert deprecation_warnings == [], (
        f"consolidated function raised unexpected DeprecationWarning: "
        f"{[str(w.message) for w in deprecation_warnings]}"
    )


def test_output_identical_to_consolidated_v0_9_0() -> None:
    """Acceptance §3.4 #2: phishing_federation_v4 와 phishing_federation 의
    출력 동일 (regression test)."""
    v4_mod = _load_module("phishing_federation_v4", "phishing_federation_v4.py")
    fed_mod = _load_module("phishing_federation", "phishing_federation.py")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        v4_result = v4_mod.fetch_federated_phishing_urls_v4(_sample_sources())
    new_result = fed_mod.fetch_federated_phishing_urls(_sample_sources())
    assert v4_result == new_result, (
        f"output diverged: v4={v4_result!r} vs new={new_result!r}"
    )


def test_phishing_federation_v4_in_all_v0_9_0() -> None:
    """Acceptance §3.4 #3: phishing_federation_v4 가 __all__ 에 그대로 존재.

    Stub namespace setup (test 파일 상단) 가 workflow_kit.__init__ 실행을 가로채므로,
    static check 로 workflow_kit/__init__.py 의 __all__ list 를 직접 검증한다.
    """
    init_path = WORKFLOW_KIT_DIR / "__init__.py"
    assert init_path.exists(), f"__init__.py not found at {init_path}"
    src = init_path.read_text()
    # __all__: list[str] = [ ... ] literal 추출
    import re
    m = re.search(r"^__all__\s*:\s*list\[str\]\s*=\s*\[(.+?)\]", src, re.S | re.M)
    assert m is not None, (
        f"could not parse __all__ literal from {init_path} (test fixture broken)"
    )
    all_items = re.findall(r'"([^"]+)"', m.group(1))
    assert "phishing_federation_v4" in all_items, (
        f"phishing_federation_v4 removed from __all__ (premature removal, "
        f"expected at v0.10.0); current __all__ entries: {all_items}"
    )
    assert "phishing_federation" in all_items, (
        f"phishing_federation missing from __all__: {all_items}"
    )
    # module file 자체도 존재 확인 (즉시 제거 ❌)
    v4_path = WORKFLOW_KIT_DIR / "phishing_federation_v4.py"
    assert v4_path.exists(), f"phishing_federation_v4.py missing at {v4_path}"


def test_existing_phishing_federation_tests_still_pass_v0_9_0() -> None:
    """Acceptance §3.4 #4: zero behavior change — 기존 check_phishing_federation.py 의
    4 test 가 동일 결과."""
    # in-process import + 동일 fixture 로 regression verify
    fed_mod = _load_module("phishing_federation", "phishing_federation.py")

    # test_fetch_federated_phishing_urls_weighted_v0_7_52 와 동일
    def s1():
        return ["https://a.com/", "https://b.com/"]

    def s2():
        return ["https://a.com/", "https://c.com/"]

    def s3():
        return ["https://a.com/"]

    result = fed_mod.fetch_federated_phishing_urls([(s1, 1.0), (s2, 0.5), (s3, 0.8)])
    by_url = {url: conf for url, conf, _ in result}
    assert abs(by_url["https://a.com/"] - 2.3) < 0.001
    assert by_url["https://b.com/"] == 1.0
    assert by_url["https://c.com/"] == 0.5
    assert result[0][0] == "https://a.com/"

    # test_fetch_federated_phishing_urls_min_confidence_v0_7_52 와 동일
    def h1():
        return ["https://low.com/", "https://high.com/"]

    def h2():
        return ["https://high.com/"]

    result = fed_mod.fetch_federated_phishing_urls(
        [(h1, 0.5), (h2, 0.5)], min_confidence=0.6
    )
    urls = [r[0] for r in result]
    assert "https://low.com/" not in urls
    assert "https://high.com/" in urls

    # test_fetch_by_min_source_count_v0_7_52 와 동일
    def m1():
        return ["https://a.com/", "https://b.com/", "https://c.com/"]

    def m2():
        return ["https://a.com/", "https://b.com/", "https://d.com/"]

    def m3():
        return ["https://a.com/", "https://e.com/"]

    urls = fed_mod.fetch_federated_phishing_urls_by_min_source_count([m1, m2, m3], 2)
    assert "https://a.com/" in urls
    assert "https://b.com/" in urls
    assert "https://c.com/" not in urls


def main() -> int:
    test_funcs = [
        test_deprecation_warning_raised_v0_9_0,
        test_deprecation_warning_strict_mode_v0_9_0,
        test_consolidated_does_not_warn_v0_9_0,
        test_output_identical_to_consolidated_v0_9_0,
        test_phishing_federation_v4_in_all_v0_9_0,
        test_existing_phishing_federation_tests_still_pass_v0_9_0,
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