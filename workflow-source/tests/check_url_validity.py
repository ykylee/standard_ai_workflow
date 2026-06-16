"""workflow_kit.url_validity helper smoke test (v0.7.53+, ADR-010/012/013/018/019/020).

Test list (offline only — online HEAD / GitHub API 는 network 의존이라 skip):
1. test_check_url_https_valid: https://example.com → 0 issue
2. test_check_url_http_rejected: http:// → V-R10-scheme error
3. test_check_url_no_scheme_rejected: example.com → V-R10-scheme error
4. test_check_url_localhost_rejected: localhost host → V-R10-localhost error
5. test_check_url_private_ip_rejected: 192.168.1.1 → V-R10-private-ip error
6. test_check_url_path_traversal_rejected: ../../etc/passwd → V-R10-traversal error
7. test_check_url_file_scheme_rejected: file:// → V-R10-file-scheme error
8. test_check_url_credentials_rejected: user:pass@host → V-R10-credentials error
9. test_check_url_github_form_unusual_warn: github.com URL with unusual 3rd path → warn
10. test_cache_stats_zero_on_empty: empty cache file → 0/0
11. test_cache_clear_idempotent: clear on non-existent file → no error
12. test_cache_file_for_strategy_suffix: per-strategy cache file naming

추가 audit (v0.7.53 audit 2차):
- online / cache / semantic_* 함수는 *외부 의존* (network, GitHub API) — 명시적 skip
- module 자체는 zero-dep (stdlib only: urllib / socket / ssl / ipaddress)
- 5 caller (workflow_kit_cli, okf_export, okf_import, v_r13_commit_diff, ...) — public surface 정합
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"


def _import_url_validity():
    """url_validity module importlib 로 load."""
    spec = importlib.util.spec_from_file_location("url_validity", str(URL_VALIDITY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["url_validity"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_check_url_https_valid_v0_7_53() -> None:
    """https://example.com → 0 issue (정합 URL)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/path")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" not in rule_codes, f"https rejected: {issues}"
    assert "V-R10-host" not in rule_codes, f"valid host rejected: {issues}"


def test_check_url_http_rejected_v0_7_53() -> None:
    """http:// → V-R10-scheme error (only https allowed)."""
    mod = _import_url_validity()
    issues = mod.check_url("http://example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" in rule_codes, f"http not rejected: {issues}"


def test_check_url_no_scheme_rejected_v0_7_53() -> None:
    """example.com (no scheme) → V-R10-scheme error."""
    mod = _import_url_validity()
    issues = mod.check_url("example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-scheme" in rule_codes, f"no-scheme not rejected: {issues}"


def test_check_url_localhost_rejected_v0_7_53() -> None:
    """https://localhost → V-R10-localhost error (private host)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://localhost")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-localhost" in rule_codes, f"localhost not rejected: {issues}"


def test_check_url_private_ip_rejected_v0_7_53() -> None:
    """https://192.168.1.1 → V-R10-private-ip error (RFC 1918)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://192.168.1.1")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-private-ip" in rule_codes, f"private IP not rejected: {issues}"


def test_check_url_path_traversal_rejected_v0_7_53() -> None:
    """https://example.com/../../etc/passwd → V-R10-traversal error."""
    mod = _import_url_validity()
    issues = mod.check_url("https://example.com/../../etc/passwd")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-traversal" in rule_codes, f"traversal not rejected: {issues}"


def test_check_url_file_scheme_rejected_v0_7_53() -> None:
    """file:///etc/passwd → V-R10-file-scheme error."""
    mod = _import_url_validity()
    issues = mod.check_url("file:///etc/passwd")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-file-scheme" in rule_codes, f"file:// not rejected: {issues}"


def test_check_url_credentials_rejected_v0_7_53() -> None:
    """https://user:pass@example.com → V-R10-credentials error (security risk)."""
    mod = _import_url_validity()
    issues = mod.check_url("https://user:pass@example.com")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-credentials" in rule_codes, f"credentials not rejected: {issues}"


def test_check_url_github_form_unusual_warn_v0_7_53() -> None:
    """github.com with unusual 3rd path → V-R10-github-form warn (not error)."""
    mod = _import_url_validity()
    # github.com/foo/bar/zzz → 3rd segment 'zzz' is not in allowed list
    issues = mod.check_url("https://github.com/foo/bar/zzz")
    rule_codes = [i.rule for i in issues]
    assert "V-R10-github-form" in rule_codes, f"unusual github form not flagged: {issues}"
    severities = [i.severity for i in issues if i.rule == "V-R10-github-form"]
    assert severities == ["warn"], f"unusual form should be warn, got {severities}"


def test_cache_stats_zero_on_empty_v0_7_53() -> None:
    """cache_stats on non-existent file → 0 hits, 0 misses."""
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "nonexistent.json"
        stats = mod.cache_stats(cache)
        assert stats.get("hits", 0) == 0, f"non-empty hits: {stats}"
        assert stats.get("misses", 0) == 0, f"non-empty misses: {stats}"


def test_cache_clear_idempotent_v0_7_53() -> None:
    """cache_clear on non-existent file → no error (idempotent)."""
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "nonexistent.json"
        mod.cache_clear(cache)  # should not raise
        # Verify no file created
        assert not cache.exists(), f"cache_clear should not create file"


def test_cache_file_for_strategy_suffix_v0_7_53() -> None:
    """cache_file_for_strategy returns per-strategy file (stem-suffix pattern)."""
    mod = _import_url_validity()
    base = Path("/tmp/cache.json")
    for strategy in ("lru", "lfu", "mixed"):
        f = mod.cache_file_for_strategy(base, strategy)
        # Naming convention: <stem>_<strategy>.<ext> (e.g. /tmp/cache_lru.json)
        # Different strategies produce different files.
        assert strategy in f.name, f"strategy {strategy!r} not in filename: {f}"
        assert f.suffix == ".json", f"expected .json suffix, got {f.suffix}"


def test_cache_prune_dry_run_preserves_data_v0_7_56() -> None:
    """cache_prune (dry_run=True) reports removal but does not modify cache (v0.7.56+)."""
    import time
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        cache_data = {
            "https://a.com/": {
                "timestamp": time.time() - 86400 * 7,  # 7d old
                "issues": [],
                "access_count": 0,
            },
            "https://b.com/": {
                "timestamp": time.time(),
                "issues": [],
                "access_count": 5,
            },
        }
        cf = mod.cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        result = mod.cache_prune(base_path=base, max_age_seconds=86400, dry_run=True)
        assert result["mixed"]["removed"] == 1
        assert result["mixed"]["kept"] == 1
        assert result["_overall"]["dry_run"] is True
        # File should be unchanged
        after = json.loads(cf.read_text(encoding="utf-8"))
        assert len(after) == 2


def test_cache_prune_apply_removes_old_v0_7_56() -> None:
    """cache_prune (apply) actually removes old entries from cache (v0.7.56+)."""
    import time
    mod = _import_url_validity()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        cache_data = {
            "https://old.com/": {
                "timestamp": time.time() - 86400 * 7,
                "issues": [],
                "access_count": 0,
            },
            "https://fresh.com/": {
                "timestamp": time.time(),
                "issues": [],
                "access_count": 5,
            },
        }
        cf = mod.cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        result = mod.cache_prune(base_path=base, max_age_seconds=86400, min_access_count=5, dry_run=False)
        assert result["mixed"]["removed"] == 1
        assert result["_overall"]["dry_run"] is False
        after = json.loads(cf.read_text(encoding="utf-8"))
        assert "https://fresh.com/" in after
        assert "https://old.com/" not in after


def main() -> int:
    test_funcs = [
        test_check_url_https_valid_v0_7_53,
        test_check_url_http_rejected_v0_7_53,
        test_check_url_no_scheme_rejected_v0_7_53,
        test_check_url_localhost_rejected_v0_7_53,
        test_check_url_private_ip_rejected_v0_7_53,
        test_check_url_path_traversal_rejected_v0_7_53,
        test_check_url_file_scheme_rejected_v0_7_53,
        test_check_url_credentials_rejected_v0_7_53,
        test_check_url_github_form_unusual_warn_v0_7_53,
        test_cache_stats_zero_on_empty_v0_7_53,
        test_cache_clear_idempotent_v0_7_53,
        test_cache_file_for_strategy_suffix_v0_7_53,
        test_cache_prune_dry_run_preserves_data_v0_7_56,
        test_cache_prune_apply_removes_old_v0_7_56,
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
