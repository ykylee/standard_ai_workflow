"""workflow_kit.cache_lfu_decay_persist CSV test (v0.7.50+).

Test list:
1. test_export_and_import_csv_roundtrip_v0_7_50: export + import returns same scores
2. test_import_csv_handles_missing_file_v0_7_50: missing file returns empty dict
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PERSIST = SOURCE_ROOT / "workflow_kit" / "cache_lfu_decay_persist.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("cache_lfu_decay_persist", str(PERSIST))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cache_lfu_decay_persist"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_export_and_import_csv_roundtrip_v0_7_50() -> None:
    """export_to_csv + import_from_csv roundtrip returns same scores."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.csv")
        scores = {
            "https://a.com/": 10.5,
            "https://b.com/": 5.2,
        }
        mod.export_to_csv(scores, path)
        loaded = mod.import_from_csv(path)
        assert loaded == scores, f"roundtrip mismatch: {loaded} != {scores}"


def test_import_csv_handles_missing_file_v0_7_50() -> None:
    """import_from_csv with missing file returns empty dict."""
    mod = _import_module()
    loaded = mod.import_from_csv("/tmp/nonexistent_v0_7_50_scores.csv")
    assert loaded == {}, f"expected empty dict, got: {loaded}"


def main() -> int:
    test_funcs = [
        test_export_and_import_csv_roundtrip_v0_7_50,
        test_import_csv_handles_missing_file_v0_7_50,
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
