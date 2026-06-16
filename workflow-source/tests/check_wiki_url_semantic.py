"""workflow_kit.url_validity V-R13 semantic URL check (PoC, v0.7.39).

ADR-019 convention 의 executable implementation (ADR-020 PoC). 6/8 check executable
in fast mode (parse-only), 8/8 with --perform-head (v0.7.40+).

Test list:
1. test_parse_semantic_url_full: 4 layer parts all populated
2. test_parse_semantic_url_minimal: commit_sha only, no query params
3. test_parse_semantic_url_no_commit: URL not GitHub-style (no commit_sha)
4. test_parse_semantic_url_invalid_hash: hash missing sha256: prefix
5. test_parse_semantic_url_range: layer 2 range parse
6. test_parse_semantic_url_invalid_range: range sha too short
7. test_validate_semantic_url_all_layers: 4 checks all clean
8. test_validate_semantic_url_no_commit_sha_warn: layer 0 missing
9. test_validate_semantic_url_no_content_hash_warn: layer 1 missing
10. test_validate_semantic_url_range_not_chronological: range_start >= range_end
11. test_check_url_semantic_fast: default mode (parse-only, 5 stub WARN)
12. test_check_url_semantic_stub_checks: 5 stub checks always WARN
13. test_semantic_url_with_v_r10_offline: combined V-R10 + V-R13
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"


def _import_url_validity():
    spec = importlib.util.spec_from_file_location("url_validity", str(URL_VALIDITY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["url_validity"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: full 4 layer parse ---


def test_parse_semantic_url_full() -> None:
    """All 4 layer parts populated."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234567/spec.md?hash=sha256:" + "a" * 64 + "&range=aaa1111..fffffff"
    p = mod.parse_semantic_url(url)
    assert p.commit_sha == "abc1234567", f"commit_sha: {p.commit_sha!r}"
    assert p.content_hash == "sha256:" + "a" * 64, f"content_hash: {p.content_hash!r}"
    assert p.range_start == "aaa1111", f"range_start: {p.range_start!r}"
    assert p.range_end == "fffffff", f"range_end: {p.range_end!r}"
# --- Test 2: minimal (commit_sha only) ---


def test_parse_semantic_url_minimal() -> None:
    """Only layer 0 (commit_sha) populated; no query params."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/deadbeef/path/to/doc.md"
    p = mod.parse_semantic_url(url)
    assert p.commit_sha == "deadbeef", f"commit_sha: {p.commit_sha!r}"
    assert p.content_hash is None
    assert p.range_start is None
    assert p.range_end is None


# --- Test 3: no commit_sha (not GitHub URL) ---


def test_parse_semantic_url_no_commit() -> None:
    """Non-GitHub URL: no commit_sha; hash + range still parse from query."""
    mod = _import_url_validity()
    url = "https://example.com/spec.md?hash=sha256:" + "b" * 64
    p = mod.parse_semantic_url(url)
    assert p.commit_sha is None
    assert p.content_hash == "sha256:" + "b" * 64


# --- Test 4: invalid hash format ---


def test_parse_semantic_url_invalid_hash() -> None:
    """Hash without sha256: prefix is rejected."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md?hash=md5:12345"
    p = mod.parse_semantic_url(url)
    assert p.content_hash is None, f"invalid hash should not parse: {p.content_hash!r}"
    assert p.commit_sha == "abc1234"


# --- Test 5: range parse ---


def test_parse_semantic_url_range() -> None:
    """Layer 2 range parses correctly."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md?range=abc1234..def5678"
    p = mod.parse_semantic_url(url)
    assert p.range_start == "abc1234"
    assert p.range_end == "def5678"


# --- Test 6: invalid range sha (too short) ---


def test_parse_semantic_url_invalid_range() -> None:
    """Range SHA < 7 chars is rejected."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md?range=ab..def5678"
    p = mod.parse_semantic_url(url)
    assert p.range_start is None, f"too-short sha should reject: {p.range_start!r}"
    assert p.range_end is None, f"too-short sha should reject: {p.range_end!r}"


# --- Test 7: validate all layers clean ---

def test_validate_semantic_url_all_layers() -> None:
    """All 4 layers present + range valid: only stub WARNs."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md?hash=sha256:" + "c" * 64 + "&range=aaa1111..fffffff"
    p = mod.parse_semantic_url(url)
    issues = mod.validate_semantic_url(p)
    # No errors, only 5 stub WARNs
    errors = [i for i in issues if i.severity == "error"]
    assert not errors, f"unexpected errors: {errors}"
    # All 5 stubs present
    stub_rules = {"V-R13-stub-content-type", "V-R13-stub-size", "V-R13-stub-author", "V-R13-stub-last-modified", "V-R13-stub-freshness"}
    actual_rules = {i.rule for i in issues}
    assert stub_rules <= actual_rules, f"missing stubs: {stub_rules - actual_rules}"

# --- Test 8: no commit_sha WARN ---


def test_validate_semantic_url_no_commit_sha_warn() -> None:
    """Layer 0 missing -> V-R13-no-commit-sha WARN."""
    mod = _import_url_validity()
    url = "https://example.com/spec.md"
    p = mod.parse_semantic_url(url)
    issues = mod.validate_semantic_url(p)
    rules = {i.rule for i in issues}
    assert "V-R13-no-commit-sha" in rules, f"missing V-R13-no-commit-sha: {rules}"


def test_validate_semantic_url_no_content_hash_warn() -> None:
    """Layer 1 missing -> V-R13-no-content-hash WARN."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md"
    p = mod.parse_semantic_url(url)
    issues = mod.validate_semantic_url(p)
    rules = {i.rule for i in issues}
    assert "V-R13-no-content-hash" in rules, f"missing V-R13-no-content-hash: {rules}"


def test_validate_semantic_url_range_not_chronological() -> None:
    """range_start >= range_end -> error."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md?range=fffffff..aaa1111"
    p = mod.parse_semantic_url(url)
    issues = mod.validate_semantic_url(p)
    rules = {(i.rule, i.severity) for i in issues}
    assert ("V-R13-range-not-chronological", "error") in rules, f"missing range error: {rules}"

# --- Test 11: check_url_semantic fast mode ---


def test_check_url_semantic_fast() -> None:
    """Default mode (fast): parse-only, returns 7-8 issues (5 stub + 2 layer missing)."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234/spec.md"
    issues = mod.check_url_semantic(url)
    # 5 stub WARNs + 1 layer-1 missing WARN + parse OK
    warn_count = sum(1 for i in issues if i.severity == "warn")
    error_count = sum(1 for i in issues if i.severity == "error")
    assert error_count == 0, f"unexpected errors: {error_count}"
    assert warn_count >= 5, f"expected >= 5 warns, got {warn_count}: {issues}"


# --- Test 12: stub checks always WARN ---


def test_check_url_semantic_stub_checks() -> None:
    """All 5 stub checks present in fast mode output."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234567/spec.md?hash=sha256:" + "d" * 64
    issues = mod.check_url_semantic(url)
    rules = {i.rule for i in issues}
    expected_stubs = {
        "V-R13-stub-content-type",
        "V-R13-stub-size",
        "V-R13-stub-author",
        "V-R13-stub-last-modified",
        "V-R13-stub-freshness",
    }
    missing = expected_stubs - rules
    assert not missing, f"missing stub checks: {missing}"


# --- Test 13: combined with V-R10 offline ---


def test_semantic_url_with_v_r10_offline() -> None:
    """V-R13 + V-R10 offline: both rule sets co-exist."""
    mod = _import_url_validity()
    url = "https://github.com/org/repo/blob/abc1234567/spec.md?hash=sha256:" + "e" * 64
    v_r10 = mod.check_url(url)
    v_r13 = mod.check_url_semantic(url)
    all_issues = v_r10 + v_r13
    # V-R10 should pass (https + no traversal)
    v_r10_errors = [i for i in v_r10 if i.severity == "error"]
    assert not v_r10_errors, f"V-R10 errors: {v_r10_errors}"
    # V-R13 should be all WARN (parse + 5 stub + 1 layer-1 missing = 6 warns)
    v_r13_errors = [i for i in v_r13 if i.severity == "error"]
    assert not v_r13_errors, f"V-R13 errors: {v_r13_errors}"
    # Combined: 5 V-R13 stub WARNs (no layer missing because hash is present) + 0 V-R10 errors
    assert len(all_issues) == 5, f"expected 5 (5 stub WARNs), got {len(all_issues)}: {all_issues}"


def main() -> int:
    test_funcs = [
        test_parse_semantic_url_full,
        test_parse_semantic_url_minimal,
        test_parse_semantic_url_no_commit,
        test_parse_semantic_url_invalid_hash,
        test_parse_semantic_url_range,
        test_parse_semantic_url_invalid_range,
        test_validate_semantic_url_all_layers,
        test_validate_semantic_url_no_commit_sha_warn,
        test_validate_semantic_url_no_content_hash_warn,
        test_validate_semantic_url_range_not_chronological,
        test_check_url_semantic_fast,
        test_check_url_semantic_stub_checks,
        test_semantic_url_with_v_r10_offline,
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
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
