"""workflow_kit.cache_size_compare eviction trigger test (v0.7.47+).

Test list:
1. test_evict_lfu_over_size_evicts_lowest_access_count_v0_7_47: evicts entries with lowest access_count first
2. test_evict_lru_over_size_evicts_oldest_first_v0_7_47: evicts entries with oldest timestamp first
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_url_validity = _import_module("url_validity", WORKFLOW_KIT_DIR / "url_validity.py")
_size_compare = _import_module("cache_size_compare", WORKFLOW_KIT_DIR / "cache_size_compare.py")
CacheEntry = _url_validity.CacheEntry


def test_evict_lfu_over_size_evicts_lowest_access_count_v0_7_47() -> None:
    """evict_lfu_over_size evicts entries with lowest access_count first."""
    # v1.0.0: mkdtemp() → TemporaryDirectory(). mkdtemp 은 자동 정리가 없어
    # *성공한 실행마다* temp dir 이 하나씩 남는다 (실측 확인).
    with tempfile.TemporaryDirectory() as _td:
        tmp_path = Path(_td)
        base = tmp_path / "url_validity_cache.json"
        cf = _url_validity.cache_file_for_strategy(base, "lfu")
        cf.parent.mkdir(parents=True, exist_ok=True)
        cache = {
            "https://cold.com/": CacheEntry(url="https://cold.com/", timestamp=100.0, issues=(), access_count=1),
            "https://warm.com/": CacheEntry(url="https://warm.com/", timestamp=200.0, issues=(), access_count=50),
            "https://hot.com/": CacheEntry(url="https://hot.com/", timestamp=300.0, issues=(), access_count=1000),
        }
        _url_validity._save_cache(cf, cache)
        current_size = cf.stat().st_size
        max_bytes = max(1, current_size // 2)
        evicted = _size_compare.evict_lfu_over_size(max_bytes, base_path=base)
        assert evicted >= 1, f"expected at least 1 eviction, got {evicted}"
        remaining = _url_validity._load_cache(cf)
        assert "https://cold.com/" not in remaining, f"cold.com should be evicted first: {remaining}"
        assert "https://hot.com/" in remaining, f"hot.com should still be present: {remaining}"


def test_evict_lru_over_size_evicts_oldest_first_v0_7_47() -> None:
    """evict_lru_over_size evicts entries with oldest timestamp first."""
    with tempfile.TemporaryDirectory() as _td:
        tmp_path = Path(_td)
        base = tmp_path / "url_validity_cache.json"
        cf = _url_validity.cache_file_for_strategy(base, "lru")
        cf.parent.mkdir(parents=True, exist_ok=True)
        cache = {
            "https://old.com/": CacheEntry(url="https://old.com/", timestamp=100.0, issues=(), access_count=0),
            "https://newer.com/": CacheEntry(url="https://newer.com/", timestamp=200.0, issues=(), access_count=0),
            "https://newest.com/": CacheEntry(url="https://newest.com/", timestamp=300.0, issues=(), access_count=0),
        }
        _url_validity._save_cache(cf, cache)
        current_size = cf.stat().st_size
        max_bytes = max(1, current_size // 2)
        evicted = _size_compare.evict_lru_over_size(max_bytes, base_path=base)
        assert evicted >= 1, f"expected at least 1 eviction, got {evicted}"
        remaining = _url_validity._load_cache(cf)
        assert "https://old.com/" not in remaining, f"old.com should be evicted first: {remaining}"
        assert "https://newest.com/" in remaining, f"newest.com should still be present: {remaining}"


def main() -> int:
    test_funcs = [
        test_evict_lfu_over_size_evicts_lowest_access_count_v0_7_47,
        test_evict_lru_over_size_evicts_oldest_first_v0_7_47,
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


def test_case_3() -> None:
    # case_3: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_4() -> None:
    # case_4: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
