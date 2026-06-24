"""v0.10.0 deprecation 1st + 2nd cycle 동시 종료 verify.

Acceptance criteria (workflow-source/core/v0_9_0_deprecation_policy_spec.md §3.5 + §3.6):
1. `phishing_federation_v4.py` 파일이 더 이상 workflow_kit/ 에 존재하지 않음 (delete)
2. `phishing_federation_v4` 가 `workflow_kit.__all__` 에서 제거됨
3. `from workflow_kit import phishing_federation_v4` → ImportError raise
4. `workflow_kit.phishing_federation_v4` direct import → ModuleNotFoundError raise
5. `workflow_kit.phishing_federation` (consolidated) 은 *영향 없이* import 가능 + 정상 동작
6. DEPRECATION_MARKED_CALLABLES whitelist 가 empty (1st + 2nd cycle 동시 종료 정합)

consumer 가 *명시적 except* 없으면 hard fail (semver major 정합).
"""
from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"
WORKFLOW_KIT_INIT = WORKFLOW_KIT_DIR / "__init__.py"


def _parse_all_list(init_path: Path) -> list[str]:
    """workflow_kit/__init__.py 의 __all__ literal 추출 (static parse)."""
    src = init_path.read_text()
    m = re.search(r"^__all__\s*:\s*list\[str\]\s*=\s*\[(.+?)\]", src, re.S | re.M)
    assert m is not None, (
        f"could not parse __all__ literal from {init_path} (test fixture broken)"
    )
    return re.findall(r'"([^"]+)"', m.group(1))


# ---------------------------------------------------------------------------
# Acceptance #1: phishing_federation_v4.py 파일 자체가 삭제됨
# ---------------------------------------------------------------------------
def test_phishing_federation_v4_file_deleted_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #1: v0.10.0 정합 — phishing_federation_v4.py file delete."""
    v4_path = WORKFLOW_KIT_DIR / "phishing_federation_v4.py"
    assert not v4_path.exists(), (
        f"v0.10.0 정합: {v4_path} 가 존재하지 않아야 함 (deprecation cycle 종료). "
        f"파일이 여전히 존재하면 v0.10.0 semver major 정공법 미준수"
    )


# ---------------------------------------------------------------------------
# Acceptance #2: phishing_federation_v4 가 __all__ 에서 제거됨
# ---------------------------------------------------------------------------
def test_phishing_federation_v4_not_in_all_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #2: v0.10.0 정합 — __all__ 에서 phishing_federation_v4 제거."""
    all_list = _parse_all_list(WORKFLOW_KIT_INIT)
    assert "phishing_federation_v4" not in all_list, (
        f"v0.10.0 정합: phishing_federation_v4 가 __all__ 에서 제거되어야 함. "
        f"__all__ = {all_list}"
    )
    # phishing_federation (consolidated) 은 유지
    assert "phishing_federation" in all_list, (
        f"phishing_federation (consolidated) 는 __all__ 에 유지되어야 함. "
        f"__all__ = {all_list}"
    )


# ---------------------------------------------------------------------------
# Acceptance #3: from workflow_kit import phishing_federation_v4 → ImportError
# ---------------------------------------------------------------------------
def test_import_phishing_federation_v4_raises_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #3: v0.10.0 정합 — `from workflow_kit import phishing_federation_v4` ImportError."""
    sys.path.insert(0, str(SOURCE_ROOT))
    try:
        from workflow_kit import phishing_federation_v4  # type: ignore[import-not-found]  # noqa: F401
        raise AssertionError(
            "v0.10.0 정합: `from workflow_kit import phishing_federation_v4` 가 "
            "ImportError raise 해야 함 (consumer 가 *명시적 except* 없으면 hard fail)"
        )
    except ImportError as e:
        # 정공법: ImportError 메시지에 module 이름 포함
        assert "phishing_federation_v4" in str(e), (
            f"ImportError 메시지에 'phishing_federation_v4' 포함 권장. got: {e}"
        )


# ---------------------------------------------------------------------------
# Acceptance #4: workflow_kit.phishing_federation_v4 direct import → ModuleNotFoundError
# ---------------------------------------------------------------------------
def test_import_workflow_kit_phishing_federation_v4_raises_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #4: v0.10.0 정합 — direct importlib ModuleNotFoundError."""
    sys.path.insert(0, str(SOURCE_ROOT))
    try:
        importlib.import_module("workflow_kit.phishing_federation_v4")
        raise AssertionError(
            "v0.10.0 정합: `import workflow_kit.phishing_federation_v4` 가 "
            "ModuleNotFoundError raise 해야 함"
        )
    except ModuleNotFoundError as e:
        assert "phishing_federation_v4" in str(e), (
            f"ModuleNotFoundError 메시지에 'phishing_federation_v4' 포함 권장. got: {e}"
        )


# ---------------------------------------------------------------------------
# Acceptance #5: phishing_federation (consolidated) 영향 없이 정상 동작
# ---------------------------------------------------------------------------
def test_phishing_federation_consolidated_still_works_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #5: v0.10.0 정합 — consolidated `phishing_federation` 정상 동작.

    v0.10.0 deprecation removal 은 *deprecated module* 만 영향. consolidated
    `phishing_federation` (v0.7.52+) 은 *대체 (replacement)* 이므로 영향 ❌.
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    mod = importlib.import_module("workflow_kit.phishing_federation")
    # public API 2종 모두 attribute 존재
    assert hasattr(mod, "fetch_federated_phishing_urls"), (
        "phishing_federation.fetch_federated_phishing_urls 가 누락"
    )
    assert hasattr(mod, "build_default_sources"), (
        "phishing_federation.build_default_sources 가 누락"
    )
    # zero behavior regression — fetch_federated_phishing_urls([],) 정상 반환
    result = mod.fetch_federated_phishing_urls([], min_confidence=0.0)
    assert isinstance(result, list), (
        f"phishing_federation.fetch_federated_phishing_urls([]) 의 output type list 여야 함. "
        f"got: {type(result).__name__}"
    )
    # build_default_sources 정상 반환
    sources = mod.build_default_sources()
    assert isinstance(sources, list), (
        f"phishing_federation.build_default_sources() 의 output type list 여야 함. "
        f"got: {type(sources).__name__}"
    )


# ---------------------------------------------------------------------------
# Acceptance #6: DEPRECATION_MARKED_CALLABLES whitelist empty
# ---------------------------------------------------------------------------
def test_deprecation_whitelist_empty_v0_10_0() -> None:
    """Acceptance §3.5 + §3.6 #6: v0.10.0 정합 — DEPRECATION_MARKED_CALLABLES whitelist empty.

    1st cycle (v0.9.0) + 2nd cycle (v0.9.3) 동시 종료. whitelist empty 가 정합.
    """
    # check_v0_9_1_deprecation_contract.py 의 whitelist 직접 verify
    contract_test_path = SOURCE_ROOT / "tests" / "check_v0_9_1_deprecation_contract.py"
    src = contract_test_path.read_text()
    # DEPRECATION_MARKED_CALLABLES dict 의 literal 추출
    m = re.search(
        r"^DEPRECATION_MARKED_CALLABLES:\s*dict\[str,\s*tuple\[str,\s*tuple,\s*dict\]\]\s*=\s*\{(.+?)\}",
        src,
        re.S | re.M,
    )
    assert m is not None, (
        f"could not parse DEPRECATION_MARKED_CALLABLES literal from {contract_test_path}"
    )
    dict_body = m.group(1).strip()
    # dict body 가 *오직* 주석만 있는 경우 (다음 cycle 의 placeholder example) → empty 정합
    # 주석 line 제외한 후 non-empty content 가 있는지 확인
    non_comment_lines = [
        line for line in dict_body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert non_comment_lines == [], (
        f"v0.10.0 정합: DEPRECATION_MARKED_CALLABLES whitelist 가 empty 여야 함. "
        f"non-comment lines: {non_comment_lines}"
    )


def main() -> int:
    test_funcs = [
        test_phishing_federation_v4_file_deleted_v0_10_0,
        test_phishing_federation_v4_not_in_all_v0_10_0,
        test_import_phishing_federation_v4_raises_v0_10_0,
        test_import_workflow_kit_phishing_federation_v4_raises_v0_10_0,
        test_phishing_federation_consolidated_still_works_v0_10_0,
        test_deprecation_whitelist_empty_v0_10_0,
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
