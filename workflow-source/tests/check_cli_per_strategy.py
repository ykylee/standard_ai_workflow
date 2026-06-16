"""workflow_kit.url_validity CLI --per-strategy flag test (v0.7.45+).

Test list:
1. test_cli_per_strategy_flag_v0_7_45: CLI --per-strategy flag is accepted (no crash)
2. test_cli_cache_stats_strategy_flag_v0_7_45: CLI --cache-stats-strategy flag is accepted
"""

from __future__ import annotations

import importlib.util
import sys
import io
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"


def _import_url_validity():
    spec = importlib.util.spec_from_file_location("url_validity", str(URL_VALIDITY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["url_validity"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cli_per_strategy_flag_v0_7_45() -> None:
    """CLI --per-strategy flag is accepted (no crash on parse)."""
    mod = _import_url_validity()
    saved_argv = sys.argv
    saved_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        sys.argv = ["x", "https://example.com/", "--per-strategy", "--mode", "loose"]
        rc = mod.main()
        # No exception = pass (rc may be 0 or 1 depending on lint mode)
    finally:
        sys.argv = saved_argv
        sys.stderr = saved_stderr


def test_cli_cache_stats_strategy_flag_v0_7_45() -> None:
    """CLI --cache-stats-strategy flag is accepted (no crash on parse)."""
    mod = _import_url_validity()
    saved_argv = sys.argv
    saved_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        sys.argv = ["x", "https://example.com/", "--cache-stats-strategy", "mixed", "--mode", "loose"]
        rc = mod.main()
    finally:
        sys.argv = saved_argv
        sys.stderr = saved_stderr


def main() -> int:
    test_funcs = [
        test_cli_per_strategy_flag_v0_7_45,
        test_cli_cache_stats_strategy_flag_v0_7_45,
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
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
