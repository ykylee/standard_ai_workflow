"""Merged cache smoke checks (check_cache_*.py x13, test bodies preserved verbatim).

Merges the following 13 files; every test function is kept with its original name
and body verbatim (the only in-body change is loader call-site substitution to the
shared _load()/_load_wk() helpers):

 1. check_cache_analytics.py            — workflow_kit.cache_analytics (v0.7.47+)
 2. check_cache_analytics_alerting.py   — workflow_kit.cache_analytics_alerting (v0.7.51+)
 3. check_cache_analytics_diff.py       — workflow_kit.cache_analytics_diff (v0.7.52)
 4. check_cache_analytics_trend.py      — workflow_kit.cache_analytics_trend (v0.7.49+)
 5. check_cache_analytics_trend_chart.py — workflow_kit.cache_analytics_trend_chart (v0.7.50+)
 6. check_cache_dashboard.py            — workflow_kit.cache_dashboard (v0.7.48+)
 7. check_cache_lfu_decay.py            — workflow_kit.cache_lfu_decay (v0.7.47+)
 8. check_cache_lfu_decay_full.py       — save_cache_lfu_decay_full (v0.7.48+)
 9. check_cache_lfu_decay_persist.py    — cache_lfu_decay_persist (v0.7.49+, ADR-021 follow-up)
10. check_cache_lfu_decay_persist_csv.py — cache_lfu_decay_persist CSV (v0.7.50+)
11. check_cache_migration.py            — workflow_kit.cache_migration (v0.7.44+)
12. check_cache_size_compare.py         — workflow_kit.cache_size_compare (v0.7.46+)
13. check_cache_size_compare_evict.py   — cache_size_compare eviction trigger (v0.7.47+)

Loader consolidation:
- _load(mod_name): bare-name registration (sys.modules[mod_name]) — replaces the
  no-arg _import_module() of files 2, 3, 5, 9, 10.
- _load_wk(mod_name): package-qualified registration (sys.modules["workflow_kit.<name>"],
  with the workflow_kit package registered once below) — replaces the
  _import_module(name, path) of files 1, 4, 6, 7, 8, 11, 12, 13.
- Collided module-level constants across sections (_analytics, _lfu_config, _decay,
  _url_validity, CacheEntry) were byte-identical loads of the same modules and are
  deduplicated to a single definition at first occurrence.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile
import time
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# Register workflow_kit as a package for cross-module imports
workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _load(mod_name: str):
    """Load workflow_kit/<mod_name>.py, register under bare mod_name (flat-loader files)."""
    path = WORKFLOW_KIT_DIR / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_wk(mod_name: str):
    """Load workflow_kit/<mod_name>.py, register under workflow_kit.<mod_name> (package-loader files)."""
    path = WORKFLOW_KIT_DIR / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{mod_name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{mod_name}"] = mod
    spec.loader.exec_module(mod)
    return mod


# ==== from check_cache_analytics.py ====
# workflow_kit.cache_analytics test (v0.7.47+): per-strategy hit rate + cross-strategy summary.

_analytics = _load_wk("cache_analytics")


def test_cache_analytics_per_strategy_hit_rate_v0_7_47() -> None:
    """cache_analytics returns per-strategy hit rate."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lru", "hits": 20, "misses": 0, "evictions": 1},
        "https://c.com/": {"strategy": "lfu", "hits": 5, "misses": 15, "evictions": 0},
    }
    result = _analytics.cache_analytics(cache)
    assert "lru" in result
    assert "lfu" in result
    # LRU: 30 hits, 5 misses -> 30/35 = 0.8571
    assert abs(result["lru"]["hit_rate"] - 30 / 35) < 0.001
    # LFU: 5 hits, 15 misses -> 5/20 = 0.25
    assert abs(result["lfu"]["hit_rate"] - 0.25) < 0.001


def test_cache_analytics_summary_cross_strategy_v0_7_47() -> None:
    """cache_analytics_summary returns aggregate + lru_to_lfu_size_ratio."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lru", "hits": 0, "misses": 0, "evictions": 0},
        "https://c.com/": {"strategy": "lru", "hits": 0, "misses": 0, "evictions": 0},
        "https://d.com/": {"strategy": "lfu", "hits": 0, "misses": 0, "evictions": 0},
    }
    summary = _analytics.cache_analytics_summary(cache)
    assert summary["total_size"] == 4
    assert summary["total_hits"] == 10
    assert summary["total_misses"] == 5
    # LRU: 3 entries, LFU: 1 entry -> ratio = 3.0
    assert summary["lru_to_lfu_size_ratio"] == 3.0
    # Overall hit rate: 10/(10+5) = 0.6667
    assert abs(summary["overall_hit_rate"] - 10 / 15) < 0.001


# ==== from check_cache_analytics_alerting.py ====
# workflow_kit.cache_analytics_alerting test (v0.7.51+): size / hit_rate threshold alerts.


def test_check_alerts_size_threshold_v0_7_51() -> None:
    """check_alerts triggers size alert when exceeded."""
    mod = _load("cache_analytics_alerting")
    analytics = {
        "lru": {"size": 100, "hits": 50, "misses": 50, "hit_rate": 0.5, "evictions": 0},
        "lfu": {"size": 200, "hits": 100, "misses": 100, "hit_rate": 0.5, "evictions": 5},
    }
    thresholds = mod.AlertThresholds(max_size=150)
    alerts = mod.check_alerts(analytics, thresholds)
    # lru (100) under 150: no alert
    # lfu (200) over 150: 1 alert
    assert len(alerts) == 1, f"expected 1 alert, got {len(alerts)}"
    assert alerts[0].strategy == "lfu"
    assert alerts[0].metric == "size"
    assert alerts[0].value == 200.0


def test_check_alerts_hit_rate_threshold_v0_7_51() -> None:
    """check_alerts triggers hit_rate alert when below threshold."""
    mod = _load("cache_analytics_alerting")
    analytics = {
        "lru": {"size": 100, "hits": 10, "misses": 90, "hit_rate": 0.1, "evictions": 0},
    }
    thresholds = mod.AlertThresholds(min_hit_rate=0.5)
    alerts = mod.check_alerts(analytics, thresholds)
    assert len(alerts) == 1
    assert alerts[0].metric == "hit_rate"
    assert alerts[0].severity == "critical"


# ==== from check_cache_analytics_diff.py ====
# workflow_kit.cache_analytics_diff test (v0.7.52): snapshot diff per-metric + per-strategy.


def test_compute_diff_basic_v0_7_52() -> None:
    """두 snapshot 의 per-metric + per-strategy delta 가 정확."""
    mod = _load("cache_analytics_diff")
    snap1 = {
        "timestamp": 1000.0,
        "total_size": 5, "total_hits": 10, "total_misses": 5,
        "per_strategy": {
            "lru": {"size": 3, "hits": 5, "misses": 2, "evictions": 0},
            "lfu": {"size": 2, "hits": 5, "misses": 3, "evictions": 0},
        },
    }
    snap2 = {
        "timestamp": 2000.0,
        "total_size": 8, "total_hits": 30, "total_misses": 10,
        "per_strategy": {
            "lru": {"size": 5, "hits": 15, "misses": 5, "evictions": 1},
            "lfu": {"size": 3, "hits": 15, "misses": 5, "evictions": 0},
        },
    }
    diff = mod.compute_diff(snap1, snap2)
    assert diff["delta_total"]["total_size"] == 3
    assert diff["delta_total"]["total_hits"] == 20
    assert diff["delta_per_strategy"]["lru"]["size"] == 2
    assert diff["delta_per_strategy"]["lfu"]["hits"] == 10


# ==== from check_cache_analytics_trend.py ====
# workflow_kit.cache_analytics_trend test (v0.7.49+): snapshot trend deltas + save/load roundtrip.
# (원본은 cache_analytics 를 먼저 로드했다 — 위 analytics 섹션의 _analytics 로드가 이를 대체.)

_trend = _load_wk("cache_analytics_trend")


def test_take_and_compute_trend_v0_7_49() -> None:
    """take_snapshot + compute_trend computes deltas between snapshots."""
    cache_t1 = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
    }
    cache_t2 = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lru", "hits": 20, "misses": 10, "evictions": 0},
    }
    snap1 = _trend.take_snapshot(cache_t1, now=1000.0)
    snap2 = _trend.take_snapshot(cache_t2, now=2000.0)
    trend = _trend.compute_trend([snap1, snap2])
    assert trend["snapshot_count"] == 2
    assert trend["deltas"]["total_size"] == 1, f"size delta expected 1, got {trend['deltas']}"
    assert trend["deltas"]["total_hits"] == 20, f"hits delta expected 20, got {trend['deltas']}"


def test_save_and_load_snapshots_roundtrip_v0_7_49() -> None:
    """save_snapshots + load_snapshots roundtrip returns same snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "snapshots.json")
        snapshots = [
            _trend.take_snapshot(
                {"https://a.com/": {"strategy": "lru", "hits": 5, "misses": 1, "evictions": 0}},
                now=1000.0,
            ),
            _trend.take_snapshot(
                {"https://b.com/": {"strategy": "lfu", "hits": 10, "misses": 2, "evictions": 1}},
                now=2000.0,
            ),
        ]
        _trend.save_snapshots(snapshots, path)
        loaded = _trend.load_snapshots(path)
        assert len(loaded) == 2
        assert loaded[0]["timestamp"] == 1000.0
        assert loaded[1]["timestamp"] == 2000.0


# ==== from check_cache_analytics_trend_chart.py ====
# workflow_kit.cache_analytics_trend_chart test (v0.7.50+): ASCII chart render + empty case.


def test_render_trend_chart_ascii_basic_v0_7_50() -> None:
    """render_trend_chart_ascii renders chart with header + bars."""
    mod = _load("cache_analytics_trend_chart")
    snapshots = [
        {"timestamp": 1000.0, "total_size": 5},
        {"timestamp": 2000.0, "total_size": 10},
        {"timestamp": 3000.0, "total_size": 20},
    ]
    output = mod.render_trend_chart_ascii(snapshots, metric="total_size", width=30, height=5)
    assert "Trend Chart" in output
    assert "=" in output
    # Should have at least one bar character
    assert "█" in output, f"expected bar chars in: {output}"


def test_render_trend_chart_ascii_empty_v0_7_50() -> None:
    """render_trend_chart_ascii with empty snapshots returns 'No snapshots'."""
    mod = _load("cache_analytics_trend_chart")
    output = mod.render_trend_chart_ascii([], metric="total_size")
    assert "No snapshots" in output, f"unexpected: {output}"


# ==== from check_cache_dashboard.py ====
# workflow_kit.cache_dashboard test (v0.7.48+): table format + machine-readable dict.
# (원본은 cache_analytics 를 먼저 로드했다 — 위 analytics 섹션의 _analytics 로드가 이를 대체.)

_dashboard = _load_wk("cache_dashboard")


def test_cache_dashboard_formats_table_v0_7_48() -> None:
    """cache_dashboard returns formatted table with header + totals."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lfu", "hits": 20, "misses": 10, "evictions": 1},
    }
    output = _dashboard.cache_dashboard(cache)
    assert "Per-Strategy Cache Dashboard" in output
    assert "lru" in output
    assert "lfu" in output
    assert "TOTAL" in output
    # Should have a separator (== or --)
    assert "=" in output or "-" in output


def test_cache_dashboard_dict_returns_machine_readable_v0_7_48() -> None:
    """cache_dashboard_dict returns dict with strategies + totals."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lfu", "hits": 20, "misses": 10, "evictions": 1},
    }
    result = _dashboard.cache_dashboard_dict(cache)
    assert "strategies" in result
    assert "totals" in result
    assert "lru" in result["strategies"]
    assert "lfu" in result["strategies"]
    assert result["totals"]["total_size"] == 2
    assert result["totals"]["total_hits"] == 30


# ==== from check_cache_lfu_decay.py ====
# workflow_kit.cache_lfu_decay test (v0.7.47+): decay scores + persist + eviction candidates.

# Pre-import dependencies
_lfu_config = _load_wk("lfu_config")
_decay = _load_wk("cache_lfu_decay")


def test_save_cache_with_decay_returns_scores_v0_7_47() -> None:
    """save_cache_with_decay returns dict of url -> decay_score."""
    cache = {
        "https://a.com/": {"access_count": 100, "timestamp": 0.0},
        "https://b.com/": {"access_count": 5, "timestamp": 0.0},
    }
    config = _lfu_config.LFUConfig()  # default decay_seconds=86400
    # now=7200 (2 hours), so age=7200
    # half_life=86400 (default), so decay factor = exp(-ln(2) * 7200 / 86400) = exp(-0.0578) ≈ 0.9438
    # v0.7.57+: cache_path=None (compute-only, no file artifact)
    scores = _decay.save_cache_with_decay(
        cache=cache, cache_path=None, config=config, now=7200.0,
    )
    assert "https://a.com/" in scores
    assert "https://b.com/" in scores
    # Just verify that a.com has higher score than b.com (since 100 > 5 hits)
    assert scores["https://a.com/"] > scores["https://b.com/"], (
        f"a.com should have higher score than b.com: {scores}"
    )
    # All scores should be positive
    for url, score in scores.items():
        assert score > 0, f"score should be positive for {url}: {score}"


def test_save_cache_with_decay_persists_v0_7_47() -> None:
    """save_cache_with_decay with valid path writes JSON file (v0.7.47+)."""
    import json
    import tempfile
    from pathlib import Path
    cache = {
        "https://a.com/": {"access_count": 100, "timestamp": 0.0},
    }
    config = _lfu_config.LFUConfig()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "decay.json"
        scores = _decay.save_cache_with_decay(
            cache=cache, cache_path=str(cp), config=config, now=7200.0,
        )
        # File should exist
        assert cp.exists(), f"expected file at {cp}"
        # Content should be parseable JSON
        data = json.loads(cp.read_text(encoding="utf-8"))
        assert "version" in data
        assert "entries" in data
        assert "lfu_decay_scores" in data
        assert "https://a.com/" in data["lfu_decay_scores"]
        # Returned scores match file content
        assert scores["https://a.com/"] == data["lfu_decay_scores"]["https://a.com/"]


def test_select_eviction_candidates_with_decay_picks_lowest_v0_7_47() -> None:
    """select_eviction_candidates_with_decay returns URLs sorted by lowest score."""
    cache = {
        "https://hot.com/": {"access_count": 1000, "timestamp": 7000.0},  # recent, very hot
        "https://warm.com/": {"access_count": 50, "timestamp": 0.0},     # old, warm
        "https://cold.com/": {"access_count": 5, "timestamp": 0.0},      # old, cold
    }
    config = _lfu_config.LFUConfig()  # default
    # now=7200
    candidates = _decay.select_eviction_candidates_with_decay(
        cache=cache, config=config, n=2, now=7200.0,
    )
    assert len(candidates) == 2, f"expected 2 candidates, got {len(candidates)}: {candidates}"
    # Expected: cold.com (lowest) first, then warm.com
    assert candidates[0] == "https://cold.com/", f"expected cold.com first, got: {candidates}"
    assert "https://hot.com/" not in candidates, f"hot.com should not be evicted: {candidates}"


# ==== from check_cache_lfu_decay_full.py ====
# workflow_kit.cache_lfu_decay.save_cache_lfu_decay_full test (v0.7.48+): evict-to-cap by lowest score.
# (원본의 _lfu_config/_decay 로드는 위 lfu_decay 섹션과 동일 — dedupe.)

_url_validity = _load_wk("url_validity")
CacheEntry = _url_validity.CacheEntry


def test_save_cache_lfu_decay_full_evicts_to_cap_v0_7_48() -> None:
    """save_cache_lfu_decay_full evicts excess entries to meet max_entries cap."""
    # v1.0.0: mkdtemp() → TemporaryDirectory(). mkdtemp 은 자동 정리가 없어
    # *성공한 실행마다* temp dir 이 하나씩 남는다 (실측 확인).
    with tempfile.TemporaryDirectory() as _td:
        tmp_path = Path(_td)
        cache_file = tmp_path / "cache.json"
        entries = {
            f"https://site{i}.com/": CacheEntry(
                url=f"https://site{i}.com/",
                timestamp=1000.0 + i,
                issues=(),
                access_count=i,
            )
            for i in range(10)
        }
        config = _lfu_config.LFUConfig()
        result = _decay.save_cache_lfu_decay_full(
            cache_file_path=str(cache_file),
            entries=entries,
            max_bytes=10_000_000,  # effectively unlimited
            max_entries=5,  # cap at 5
            config=config,
            now=2000.0,
        )
        assert len(result) == 5, f"expected 5 entries after eviction, got {len(result)}: {result}"


def test_save_cache_lfu_decay_full_picks_lowest_score_first_v0_7_48() -> None:
    """save_cache_lfu_decay_full evicts by lowest score (oldest+lowest access_count)."""
    with tempfile.TemporaryDirectory() as _td:
        tmp_path = Path(_td)
        cache_file = tmp_path / "cache.json"
        # Entry with access_count=0, oldest = lowest score = first to evict
        entries = {
            "https://low.com/": CacheEntry(
                url="https://low.com/", timestamp=100.0, issues=(), access_count=0,
            ),
            "https://high.com/": CacheEntry(
                url="https://high.com/", timestamp=900.0, issues=(), access_count=1000,
            ),
        }
        config = _lfu_config.LFUConfig()
        result = _decay.save_cache_lfu_decay_full(
            cache_file_path=str(cache_file),
            entries=entries,
            max_bytes=10_000_000,
            max_entries=1,  # cap at 1 -> evict one
            config=config,
            now=2000.0,
        )
        assert len(result) == 1
        assert "https://high.com/" in result, f"high.com should survive, got: {result}"
        assert "https://low.com/" not in result, f"low.com should be evicted: {result}"


# ==== from check_cache_lfu_decay_persist.py ====
# workflow_kit.cache_lfu_decay_persist test (v0.7.49+, ADR-021 follow-up): score persist roundtrip + CSV in-place decay.


def test_save_and_load_decay_scores_roundtrip_v0_7_49() -> None:
    """save_decay_scores + load_decay_scores roundtrip returns same scores."""
    mod = _load("cache_lfu_decay_persist")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.json")
        scores = {
            "https://a.com/": 10.5,
            "https://b.com/": 5.2,
            "https://c.com/": 0.0,
        }
        mod.save_decay_scores(scores, path)
        loaded = mod.load_decay_scores(path)
        assert loaded == scores, f"roundtrip mismatch: {loaded} != {scores}"


def test_update_decay_score_persists_v0_7_49() -> None:
    """update_decay_score updates single URL + persists to disk."""
    mod = _load("cache_lfu_decay_persist")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.json")
        scores: dict[str, float] = {"https://a.com/": 5.0}
        mod.update_decay_score(scores, "https://b.com/", 10.0, path)
        # Re-load from disk to verify persistence
        loaded = mod.load_decay_scores(path)
        assert loaded == {"https://a.com/": 5.0, "https://b.com/": 10.0}
        assert mod.get_decay_score(loaded, "https://c.com/", default=-1.0) == -1.0


def test_decay_csv_inplace_v0_7_56() -> None:
    """decay_csv_inplace: read CSV, apply decay, write back to same path (v0.7.56+)."""
    mod = _load("cache_lfu_decay_persist")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.csv")
        scores = {
            "https://hot.com/": 100.0,
            "https://warm.com/": 50.0,
        }
        mod.export_to_csv(scores, path)
        # Make file 7 days old (saved_at = old time)
        old = time.time() - 86400 * 7
        os.utime(path, (old, old))
        result = mod.decay_csv_inplace(path, saved_at=old, half_life_seconds=86400.0)
        assert result["scores_in"] == 2
        assert result["scores_out"] == 2
        # Read back
        after = mod.import_from_csv(path)
        # Expected: score * exp(-ln(2) * 7) = score * 0.00781
        expected_hot = 100.0 * math.exp(-math.log(2) * 7)
        actual_hot = after["https://hot.com/"]
        assert abs(actual_hot - expected_hot) < 0.01, (
            f"decay math wrong: expected {expected_hot:.4f}, got {actual_hot:.4f}"
        )


def test_export_import_csv_roundtrip_v0_7_50() -> None:
    """export_to_csv + import_from_csv roundtrip returns same scores (v0.7.50+)."""
    mod = _load("cache_lfu_decay_persist")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.csv")
        scores = {
            "https://x.com/": 7.5,
            "https://y.com/": 3.2,
        }
        mod.export_to_csv(scores, path)
        loaded = mod.import_from_csv(path)
        assert loaded == scores, f"roundtrip mismatch: {loaded} != {scores}"


# ==== from check_cache_lfu_decay_persist_csv.py ====
# workflow_kit.cache_lfu_decay_persist CSV test (v0.7.50+): CSV roundtrip + missing file.


def test_export_and_import_csv_roundtrip_v0_7_50() -> None:
    """export_to_csv + import_from_csv roundtrip returns same scores."""
    mod = _load("cache_lfu_decay_persist")
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
    mod = _load("cache_lfu_decay_persist")
    loaded = mod.import_from_csv("/tmp/nonexistent_v0_7_50_scores.csv")
    assert loaded == {}, f"expected empty dict, got: {loaded}"


# ==== from check_cache_migration.py ====
# workflow_kit.cache_migration test (v0.7.44+): single->mixed migrate, split, merge, CSV/JSON import-export.
# (원본의 _url_validity 로드는 위 lfu_decay_full 섹션과 동일 — dedupe.)

_cache_migration = _load_wk("cache_migration")


def test_migrate_to_per_strategy_cache_v0_7_44() -> None:
    """migrate_to_per_strategy_cache moves v0.7.41 single file -> 3 per-strategy files (mixed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        # Create v0.7.41 single file with 2 entries
        now = time.time()
        entries = {
            "https://a.com/": _url_validity.CacheEntry(url="https://a.com/", timestamp=now, issues=("ok",), access_count=5),
            "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",), access_count=10),
        }
        _url_validity._save_cache(base, entries)
        assert base.exists()
        # Migrate
        result = _cache_migration.migrate_to_per_strategy_cache(base_path=base)
        assert result["migrated"] is True, f"migration should have occurred: {result}"
        assert result["entries_migrated"] == 2, f"expected 2 entries migrated, got {result['entries_migrated']}"
        # Source should be deleted
        assert not base.exists(), f"source should be deleted, but exists: {base}"
        # Mixed file should exist with entries
        mixed_file = Path(result["mixed_file"])
        assert mixed_file.exists(), f"mixed file should exist: {mixed_file}"
        loaded = _url_validity._load_cache(mixed_file)
        assert "https://a.com/" in loaded, f"a.com should be in mixed file, got: {list(loaded.keys())}"
        assert "https://b.com/" in loaded, f"b.com should be in mixed file, got: {list(loaded.keys())}"


def test_split_to_per_strategy_v0_7_45() -> None:
    """split_to_per_strategy splits mixed file by access_count threshold (default 10)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        # First, create v0.7.41 single file and migrate to mixed
        now = time.time()
        entries = {
            "https://low.com/": _url_validity.CacheEntry(url="https://low.com/", timestamp=now, issues=("ok",), access_count=0),
            "https://mid.com/": _url_validity.CacheEntry(url="https://mid.com/", timestamp=now, issues=("ok",), access_count=5),
            "https://high.com/": _url_validity.CacheEntry(url="https://high.com/", timestamp=now, issues=("ok",), access_count=100),
        }
        _url_validity._save_cache(base, entries)
        _cache_migration.migrate_to_per_strategy_cache(base_path=base)
        # Now split
        result = _cache_migration.split_to_per_strategy(base_path=base, lfu_threshold=10)
        assert result["split"] is True, f"split should have occurred: {result}"
        # LRU file: low + mid (access_count < 10)
        assert result["lru_entries"] == 2, f"expected 2 LRU entries, got {result['lru_entries']}"
        # LFU file: high (access_count >= 10)
        assert result["lfu_entries"] == 1, f"expected 1 LFU entry, got {result['lfu_entries']}"
        # Verify files
        lru_file = Path(result["lru_file"])
        lfu_file = Path(result["lfu_file"])
        assert lru_file.exists(), f"lru file should exist: {lru_file}"
        assert lfu_file.exists(), f"lfu file should exist: {lfu_file}"
        lru_loaded = _url_validity._load_cache(lru_file)
        lfu_loaded = _url_validity._load_cache(lfu_file)
        assert "https://low.com/" in lru_loaded
        assert "https://mid.com/" in lru_loaded
        assert "https://high.com/" in lfu_loaded


def test_merge_per_strategy_to_mixed_v0_7_57() -> None:
    """merge_per_strategy_to_mixed merges LRU + LFU back into mixed file (v0.7.57+)."""
    mod = _load_wk("cache_migration")
    _url_validity = _load_wk("url_validity")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        # Seed LRU + LFU files
        lru_file = _url_validity.cache_file_for_strategy(base, "lru")
        lfu_file = _url_validity.cache_file_for_strategy(base, "lfu")
        lru_data = {
            "https://lru.com/": {"timestamp": 1000.0, "issues": [], "access_count": 2},
        }
        lfu_data = {
            "https://lfu.com/": {"timestamp": 2000.0, "issues": [], "access_count": 50},
        }
        lru_file.write_text(__import__("json").dumps(lru_data), encoding="utf-8")
        lfu_file.write_text(__import__("json").dumps(lfu_data), encoding="utf-8")
        result = mod.merge_per_strategy_to_mixed(base_path=base)
        assert result["merged"] is True
        assert result["lru_entries"] == 1
        assert result["lfu_entries"] == 1
        assert result["total"] == 2
        # mixed file should exist
        mixed_file = _url_validity.cache_file_for_strategy(base, "mixed")
        assert mixed_file.exists(), f"mixed file should exist: {mixed_file}"


def test_import_csv_to_cache_v0_7_57() -> None:
    """import_csv_to_cache imports external CSV (url,status,timestamp,access_count) (v0.7.57+)."""
    mod = _load_wk("cache_migration")
    _url_validity = _load_wk("url_validity")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        csv_p = Path(tmp) / "urls.csv"
        csv_p.write_text(
            "url,status,timestamp,access_count\n"
            "https://a.com/,ok,1000.0,5\n"
            "https://b.com/,ok,2000.0,10\n",
            encoding="utf-8",
        )
        result = mod.import_csv_to_cache(str(csv_p), str(base), merge=False)
        assert result["imported"] == 2
        assert result["skipped"] == 0
        assert result["total_rows"] == 2
        # Verify entries
        entries = _url_validity._load_cache(base)
        assert "https://a.com/" in entries
        assert "https://b.com/" in entries
        assert entries["https://a.com/"].access_count == 5


def test_export_cache_to_json_v0_7_57() -> None:
    """export_cache_to_json writes standalone JSON file (v0.7.57+)."""
    mod = _load_wk("cache_migration")
    _url_validity = _load_wk("url_validity")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        base.write_text(
            __import__("json").dumps({
                "https://a.com/": {"timestamp": 1000.0, "issues": [], "access_count": 5},
            }),
            encoding="utf-8",
        )
        output = Path(tmp) / "export.json"
        result = mod.export_cache_to_json(str(output), str(base), pretty=True)
        assert result["entries"] == 1
        assert output.exists()
        data = __import__("json").loads(output.read_text(encoding="utf-8"))
        assert "https://a.com/" in data
        assert data["https://a.com/"]["access_count"] == 5


# ==== from check_cache_size_compare.py ====
# workflow_kit.cache_size_compare test (v0.7.46+): bytes per strategy + sorted A/B compare.
# (원본의 _url_validity 로드는 위 lfu_decay_full 섹션과 동일 — dedupe.)

_cache_size_compare = _load_wk("cache_size_compare")


def test_cache_size_per_strategy_v0_7_46() -> None:
    """cache_size_per_strategy returns bytes per strategy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        now = time.time()
        # Populate lru with 2 entries
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "lru"),
            {
                "https://a.com/": _url_validity.CacheEntry(url="https://a.com/", timestamp=now, issues=("ok",)),
                "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",)),
            },
        )
        # Populate mixed with 1 entry
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "mixed"),
            {
                "https://c.com/": _url_validity.CacheEntry(url="https://c.com/", timestamp=now, issues=("ok",)),
            },
        )
        sizes = _cache_size_compare.cache_size_per_strategy(base_path=base)
        assert sizes["lru"] > 0, f"lru should be > 0 bytes, got {sizes['lru']}"
        assert sizes["mixed"] > 0, f"mixed should be > 0 bytes, got {sizes['mixed']}"
        assert sizes["lfu"] == 0, f"lfu (no file) should be 0 bytes, got {sizes['lfu']}"
        # lru should be larger than mixed (2 entries vs 1)
        assert sizes["lru"] > sizes["mixed"], f"lru ({sizes['lru']}) should be > mixed ({sizes['mixed']})"


def test_cache_size_per_strategy_compare_v0_7_46() -> None:
    """cache_size_per_strategy_compare returns sorted (strategy, bytes) descending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        now = time.time()
        # Populate lru with 3 entries (largest)
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "lru"),
            {
                f"https://a{i}.com/": _url_validity.CacheEntry(url=f"https://a{i}.com/", timestamp=now, issues=("ok",))
                for i in range(3)
            },
        )
        # Populate mixed with 1 entry
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "mixed"),
            {
                "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",)),
            },
        )
        result = _cache_size_compare.cache_size_per_strategy_compare(base_path=base)
        # Should be sorted descending by bytes
        assert result[0][0] == "lru", f"lru should be first (largest), got: {result}"
        assert result[-1][0] == "lfu", f"lfu should be last (no file), got: {result}"
        assert result[0][1] > result[1][1], f"first should be > second, got: {result}"


# ==== from check_cache_size_compare_evict.py ====
# workflow_kit.cache_size_compare eviction trigger test (v0.7.47+): LFU/LRU over-size eviction order.
# (원본의 _url_validity/CacheEntry 로드는 위 lfu_decay_full 섹션과 동일 — dedupe.)

_size_compare = _load_wk("cache_size_compare")


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
        # check_cache_analytics.py
        test_cache_analytics_per_strategy_hit_rate_v0_7_47,
        test_cache_analytics_summary_cross_strategy_v0_7_47,
        # check_cache_analytics_alerting.py
        test_check_alerts_size_threshold_v0_7_51,
        test_check_alerts_hit_rate_threshold_v0_7_51,
        # check_cache_analytics_diff.py
        test_compute_diff_basic_v0_7_52,
        # check_cache_analytics_trend.py
        test_take_and_compute_trend_v0_7_49,
        test_save_and_load_snapshots_roundtrip_v0_7_49,
        # check_cache_analytics_trend_chart.py
        test_render_trend_chart_ascii_basic_v0_7_50,
        test_render_trend_chart_ascii_empty_v0_7_50,
        # check_cache_dashboard.py
        test_cache_dashboard_formats_table_v0_7_48,
        test_cache_dashboard_dict_returns_machine_readable_v0_7_48,
        # check_cache_lfu_decay.py
        test_save_cache_with_decay_returns_scores_v0_7_47,
        test_save_cache_with_decay_persists_v0_7_47,
        test_select_eviction_candidates_with_decay_picks_lowest_v0_7_47,
        # check_cache_lfu_decay_full.py
        test_save_cache_lfu_decay_full_evicts_to_cap_v0_7_48,
        test_save_cache_lfu_decay_full_picks_lowest_score_first_v0_7_48,
        # check_cache_lfu_decay_persist.py
        test_save_and_load_decay_scores_roundtrip_v0_7_49,
        test_update_decay_score_persists_v0_7_49,
        test_export_import_csv_roundtrip_v0_7_50,
        test_decay_csv_inplace_v0_7_56,
        # check_cache_lfu_decay_persist_csv.py
        test_export_and_import_csv_roundtrip_v0_7_50,
        test_import_csv_handles_missing_file_v0_7_50,
        # check_cache_migration.py
        test_migrate_to_per_strategy_cache_v0_7_44,
        test_split_to_per_strategy_v0_7_45,
        test_merge_per_strategy_to_mixed_v0_7_57,
        test_import_csv_to_cache_v0_7_57,
        test_export_cache_to_json_v0_7_57,
        # check_cache_size_compare.py
        test_cache_size_per_strategy_v0_7_46,
        test_cache_size_per_strategy_compare_v0_7_46,
        # check_cache_size_compare_evict.py
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


if __name__ == "__main__":
    sys.exit(main())
