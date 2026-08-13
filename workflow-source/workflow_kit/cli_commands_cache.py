"""workflow_kit.cli_commands_cache - cache / analytics dispatcher subcommands.

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
부분 분할). 13개 cache/analytics handler: cache-dashboard / dashboard-export /
trend-chart / alert / cache-decay / cache-migrate / cache-prune /
cache-merge-multi / cache-import-csv / cache-export-json /
cache-lfu-decay-persist / cache-lru-decay / cache-merge-csv.

`@register` 가 import 시점에 `cli_registry.COMMANDS` 에 등록하고,
workflow_kit_cli 가 본 모듈의 handler 를 재-export 한다 — arg surface 문서는
workflow_kit_cli 모듈 docstring 이 계속 정본이다.
"""

from __future__ import annotations

import sys
from typing import Any, Literal, cast

from workflow_kit.cli_registry import _has_flag, _parse_flag, register

__all__ = [
    "cmd_cache_dashboard",
    "cmd_dashboard_export",
    "cmd_trend_chart",
    "cmd_alert",
    "cmd_cache_decay",
    "cmd_cache_migrate",
    "cmd_cache_prune",
    "cmd_cache_merge_multi",
    "cmd_cache_import_csv",
    "cmd_cache_export_json",
    "cmd_cache_lfu_decay_persist",
    "cmd_cache_lru_decay",
    "cmd_cache_merge_csv",
]


@register("cache-dashboard")
def cmd_cache_dashboard(argv: list[str]) -> int:
    cache_path = _parse_flag(argv, "--cache-path")
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_dashboard import cache_dashboard
        base = Path(cache_path) if cache_path else DEFAULT_CACHE_FILE
        merged: dict[str, Any] = {}
        for strategy in ("lru", "lfu", "mixed"):
            cf = cache_file_for_strategy(base, strategy)
            if cf.exists():
                entries = _load_cache(cf)
                for url, entry in entries.items():
                    if hasattr(entry, "__dict__"):
                        d = entry.__dict__.copy()
                    elif isinstance(entry, dict):
                        d = entry.copy()
                    else:
                        d = {"timestamp": getattr(entry, "timestamp", 0.0)}
                    d["strategy"] = strategy
                    merged[url] = d
        print(cache_dashboard(merged))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("dashboard-export")
def cmd_dashboard_export(argv: list[str]) -> int:
    output = _parse_flag(argv, "--output")
    if output is None:
        print("ERROR: --output=PATH required", file=sys.stderr)
        return 2
    fmt = _parse_flag(argv, "--format") or "text"
    if fmt not in ("text", "json", "markdown", "html"):
        print(f"ERROR: invalid --format '{fmt}'", file=sys.stderr)
        return 2
    fmt_literal = cast(Literal["text", "json", "markdown", "html"], fmt)
    cache_path = _parse_flag(argv, "--cache-path")
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_dashboard import write_dashboard
        base = Path(cache_path) if cache_path else DEFAULT_CACHE_FILE
        merged: dict[str, Any] = {}
        for strategy in ("lru", "lfu", "mixed"):
            cf = cache_file_for_strategy(base, strategy)
            if cf.exists():
                entries = _load_cache(cf)
                for url, entry in entries.items():
                    if hasattr(entry, "__dict__"):
                        d = entry.__dict__.copy()
                    elif isinstance(entry, dict):
                        d = entry.copy()
                    else:
                        d = {"timestamp": getattr(entry, "timestamp", 0.0)}
                    d["strategy"] = strategy
                    merged[url] = d
        write_dashboard(merged, output, format=fmt_literal)
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("trend-chart")
def cmd_trend_chart(argv: list[str]) -> int:
    snapshots_path = _parse_flag(argv, "--snapshots")
    if snapshots_path is None:
        print("ERROR: --snapshots=PATH required", file=sys.stderr)
        return 2
    metric = _parse_flag(argv, "--metric") or "total_size"
    metric_literal = cast(Literal["total_size", "total_hits", "total_misses"], metric)
    try:
        from workflow_kit.cache_analytics_trend import load_snapshots
        from workflow_kit.cache_analytics_trend_chart import render_trend_chart_ascii
        snapshots = load_snapshots(snapshots_path)
        if not snapshots:
            print("ERROR: no snapshots found", file=sys.stderr)
            return 2
        print(render_trend_chart_ascii(snapshots, metric=metric_literal))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("alert")
def cmd_alert(argv: list[str]) -> int:
    max_size_s = _parse_flag(argv, "--max-size")
    min_hit_s = _parse_flag(argv, "--min-hit-rate")
    max_ev_s = _parse_flag(argv, "--max-evictions")
    cache_path = _parse_flag(argv, "--cache-path")
    max_size = int(max_size_s) if max_size_s else None
    min_hit_rate = float(min_hit_s) if min_hit_s else None
    max_evictions = int(max_ev_s) if max_ev_s else None
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_analytics import cache_analytics
        from workflow_kit.cache_analytics_alerting import AlertThresholds, check_alerts, format_alerts
        base = Path(cache_path) if cache_path else DEFAULT_CACHE_FILE
        merged: dict[str, Any] = {}
        for strategy in ("lru", "lfu", "mixed"):
            cf = cache_file_for_strategy(base, strategy)
            if cf.exists():
                entries = _load_cache(cf)
                for url, entry in entries.items():
                    if hasattr(entry, "__dict__"):
                        d = entry.__dict__.copy()
                    elif isinstance(entry, dict):
                        d = entry.copy()
                    else:
                        d = {"timestamp": getattr(entry, "timestamp", 0.0)}
                    d["strategy"] = strategy
                    merged[url] = d
        analytics = cache_analytics(merged)
        thresholds = AlertThresholds(
            max_size=max_size, min_hit_rate=min_hit_rate, max_evictions=max_evictions,
        )
        alerts = check_alerts(analytics, thresholds)
        print(format_alerts(alerts))
        return 1 if alerts else 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-decay")
def cmd_cache_decay(argv: list[str]) -> int:
    """Apply temporal decay to LFU cache scores (v0.7.51+, CSV in-place v0.7.56+).

    Reads scores from JSON or CSV file, applies age-based decay (default half-life=1 day),
    writes decayed scores back. Args:
        --scores=PATH          input file (url → score, JSON or CSV)
        --saved-at=ISO8601     timestamp when scores were saved
                              (default: file mtime)
        --output=PATH          output JSON file (default: stdout)
        --inplace              CSV in-place write (v0.7.56+)
        --half-life=N          half-life in seconds (default 86400 = 1 day)
        --json                 JSON output
    """
    import json as _json
    scores_path_s = _parse_flag(argv, "--scores")
    if scores_path_s is None:
        print("ERROR: --scores=PATH required", file=sys.stderr)
        return 2
    saved_at_s = _parse_flag(argv, "--saved-at")
    output_s = _parse_flag(argv, "--output")
    inplace = _has_flag(argv, "--inplace")
    half_life_s = _parse_flag(argv, "--half-life")
    half_life = float(half_life_s) if half_life_s else 86400.0
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_lfu_decay_persist import (
            decay_age_scores, decay_csv_inplace, import_from_csv,
        )
        scores_path = _P(scores_path_s)
        if not scores_path.exists():
            print(f"ERROR: --scores path not found: {scores_path}", file=sys.stderr)
            return 2
        if saved_at_s is None:
            mtime = scores_path.stat().st_mtime
            saved_at = mtime
        else:
            import datetime as _dt
            saved_at = _dt.datetime.fromisoformat(saved_at_s).timestamp()
        # CSV in-place (v0.7.56+)
        if inplace:
            if scores_path.suffix.lower() != ".csv":
                print(f"ERROR: --inplace requires .csv file, got {scores_path.suffix}", file=sys.stderr)
                return 2
            result = decay_csv_inplace(
                str(scores_path),
                saved_at=saved_at,
                half_life_seconds=half_life,
            )
            if use_json:
                print(_json.dumps(result, indent=2, default=str))
            else:
                print(f"Decayed {result['scores_out']} scores in-place → {result['path']}")
                print(f"  half_life={result['half_life_seconds']}s, saved_at={result['saved_at']:.0f}")
            return 0
        # JSON path (v0.7.51+)
        scores = _json.loads(scores_path.read_text(encoding="utf-8"))
        decayed = decay_age_scores(scores, saved_at=saved_at, half_life_seconds=half_life)
        if output_s:
            _P(output_s).write_text(_json.dumps(decayed, indent=2, sort_keys=True), encoding="utf-8")
            if use_json:
                print(_json.dumps({"output": output_s, "scores_in": len(scores), "scores_out": len(decayed)}, indent=2))
            else:
                print(f"Decayed {len(decayed)} scores → {output_s}")
        else:
            if use_json:
                print(_json.dumps({"scores": decayed, "saved_at": saved_at, "half_life": half_life}, indent=2))
            else:
                print(f"Decayed {len(decayed)} scores (half_life={half_life}s, saved_at={saved_at})")
                for url, score in list(decayed.items())[:10]:
                    print(f"  {url}: {score:.4f}")
                if len(decayed) > 10:
                    print(f"  ... +{len(decayed) - 10} more")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-migrate")
def cmd_cache_migrate(argv: list[str]) -> int:
    """Migrate v0.7.41 single-strategy cache → per-strategy files (ADR-024).

    2 step:
      1. migrate: v0.7.41 single file → mixed file (1-step, no-op if already)
      2. split:   mixed file → LRU + LFU files (per access_count threshold)

    Args:
        --cache-path=PATH   base cache file (default: DEFAULT_CACHE_FILE)
        --mode=migrate|split|both  default = both
        --lfu-threshold=N   access_count threshold for LFU classification (default 10)
        --json              JSON output (otherwise human-readable)
    """
    import json as _json
    cache_path_s = _parse_flag(argv, "--cache-path")
    mode = _parse_flag(argv, "--mode") or "both"
    if mode not in ("migrate", "split", "both"):
        print(f"ERROR: --mode must be migrate|split|both, got {mode!r}", file=sys.stderr)
        return 2
    lfu_th_s = _parse_flag(argv, "--lfu-threshold")
    lfu_threshold = int(lfu_th_s) if lfu_th_s else 10
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_migration import (
            migrate_to_per_strategy_cache,
            split_to_per_strategy,
        )
        base = _P(cache_path_s) if cache_path_s else None
        all_results: dict[str, object] = {"mode": mode, "cache_path": str(base) if base else None}
        if mode in ("migrate", "both"):
            all_results["migrate"] = migrate_to_per_strategy_cache(base_path=base)
        if mode in ("split", "both"):
            all_results["split"] = split_to_per_strategy(base_path=base, lfu_threshold=lfu_threshold)
        if use_json:
            print(_json.dumps(all_results, indent=2, default=str))
        else:
            if "migrate" in all_results:
                m = cast(dict[str, Any], all_results["migrate"])
                if m.get("migrated"):
                    print(f"[migrate] OK: {m.get('entries_migrated', 0)} entries → mixed file")
                else:
                    print(f"[migrate] no-op (per-strategy already exist or source absent)")
            if "split" in all_results:
                s = cast(dict[str, Any], all_results["split"])
                if s.get("split"):
                    print(f"[split] OK: {s.get('lru_entries', 0)} LRU + {s.get('lfu_entries', 0)} LFU (threshold={lfu_threshold})")
                else:
                    print(f"[split] no-op (mixed file absent or empty)")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-prune")
def cmd_cache_prune(argv: list[str]) -> int:
    """Prune cache entries by age and/or access count (v0.7.56+, dispatcher subcommand 16).

    Removes entries from per-strategy cache files (lru/lfu/mixed) matching:
    - older-than: only entries with age > this (default = no age filter)
    - min-access-count: only entries with access_count < this (default 0 = any)
    - cache-path: base cache file path (default: DEFAULT_CACHE_FILE)
    Default `--dry-run` reports what would be removed. Args:
        --cache-path=PATH      base cache file path
        --older-than=SECONDS   max age in seconds
        --min-access-count=N   only prune entries with access_count < N
        --apply                actually remove (default is dry-run)
        --json                 JSON output
    """
    import json as _json
    cache_path_s = _parse_flag(argv, "--cache-path")
    older_than_s = _parse_flag(argv, "--older-than")
    min_access_s = _parse_flag(argv, "--min-access-count")
    apply = _has_flag(argv, "--apply")
    use_json = _has_flag(argv, "--json")
    older_than = float(older_than_s) if older_than_s else None
    min_access_count = int(min_access_s) if min_access_s else 0
    try:
        from pathlib import Path as _P
        from workflow_kit.url_validity import cache_prune
        base = _P(cache_path_s) if cache_path_s else None
        result = cache_prune(
            base_path=base,
            max_age_seconds=older_than,
            min_access_count=min_access_count,
            dry_run=not apply,
        )
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            mode = "APPLY" if apply else "DRY-RUN"
            print(f"Cache prune ({mode}):")
            for strategy, info in result.items():
                if strategy.startswith("_"):
                    continue
                print(f"  {strategy}: removed={info['removed']}, kept={info['kept']}, total={info['total']}")
            overall = result.get("_overall", {})
            if "total_removed" in overall:
                print(f"  TOTAL removed: {overall['total_removed']}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# cache format interop (v0.7.57+, dispatcher subcommand 24-26)
# ---------------------------------------------------------------------------


@register("cache-merge-multi")
def cmd_cache_merge_multi(argv: list[str]) -> int:
    """Merge per-strategy LRU + LFU files back into mixed file (v0.7.57+, subcommand 24).

    Reverse of cache-migrate --mode=split. Default dry-run reports what would be
    merged. Args:
        --cache-path=PATH      base cache file path (default: DEFAULT_CACHE_FILE)
        --delete-sources       delete LRU + LFU files after merge
        --json                 JSON output
    """
    import json as _json
    cache_path_s = _parse_flag(argv, "--cache-path")
    delete_sources = _has_flag(argv, "--delete-sources")
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_migration import merge_per_strategy_to_mixed
        base = _P(cache_path_s) if cache_path_s else None
        result = merge_per_strategy_to_mixed(base_path=base, delete_sources=delete_sources)
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            if result["merged"]:
                print(f"Merged: {result['lru_entries']} LRU + {result['lfu_entries']} LFU → {result['total']} total → {result['mixed_file']}")
                if result["delete_sources"]:
                    print("  (LRU + LFU files deleted)")
            else:
                print(f"No-op: no LRU/LFU files found")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-import-csv")
def cmd_cache_import_csv(argv: list[str]) -> int:
    """Import URLs from CSV file into cache (v0.7.57+, subcommand 25).

    CSV format: `url,status,timestamp,access_count` (header required).
    Default merge with existing cache. Args:
        --csv=PATH             input CSV file (required)
        --cache-path=PATH      target cache file (default: DEFAULT_CACHE_FILE)
        --replace              replace existing cache (default merge)
        --json                 JSON output
    """
    import json as _json
    csv_s = _parse_flag(argv, "--csv")
    if csv_s is None:
        print("ERROR: --csv=PATH required", file=sys.stderr)
        return 2
    cache_path_s = _parse_flag(argv, "--cache-path")
    replace = _has_flag(argv, "--replace")
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_migration import import_csv_to_cache
        cache_path = cache_path_s
        result = import_csv_to_cache(csv_s, cache_path, merge=not replace)
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            mode = "REPLACE" if replace else "MERGE"
            print(f"Import ({mode}): {result['imported']} imported, {result['skipped']} skipped (of {result['total_rows']} rows)")
            print(f"  cache: {result['cache_path']}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-export-json")
def cmd_cache_export_json(argv: list[str]) -> int:
    """Export cache entries to standalone JSON file (v0.7.57+, subcommand 26).

    Format: flat dict of url -> {timestamp, issues, access_count}. Args:
        --output=PATH          output JSON file (required)
        --cache-path=PATH      source cache file (default: DEFAULT_CACHE_FILE)
        --compact              no indent (default pretty)
        --json                 JSON output
    """
    import json as _json
    output_s = _parse_flag(argv, "--output")
    if output_s is None:
        print("ERROR: --output=PATH required", file=sys.stderr)
        return 2
    cache_path_s = _parse_flag(argv, "--cache-path")
    compact = _has_flag(argv, "--compact")
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_migration import export_cache_to_json
        result = export_cache_to_json(
            output_s,
            cache_path=cache_path_s,
            pretty=not compact,
        )
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            print(f"Exported {result['entries']} entries → {result['output_path']}")
            if "error" in result:
                print(f"  WARN: {result['error']}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-lfu-decay-persist")
def cmd_cache_lfu_decay_persist(argv: list[str]) -> int:
    """Update a single URL's LFU decay score and persist (v0.7.60+, subcommand 28).

    In-process wrapper for `tools.release_pipeline_lib.cmd_lfu_decay_persist`.
    Reads existing scores from JSON file, simulates (dry-run default) or applies
    (with --apply) a single URL update, persists to disk.

    Args:
        --url=URL             URL key to update (required)
        --score=FLOAT         new decay score (required)
        --scores-path=PATH    JSON scores file (default: cache/lfu_decay_scores.json)
        --apply               actually persist (default: dry-run)
        --json                JSON output

    Safety: default is dry-run (memory rule 5). Pass --apply to persist.
    """
    import json as _json
    url = _parse_flag(argv, "--url")
    score_s = _parse_flag(argv, "--score")
    if not url:
        print("ERROR: --url=URL required", file=sys.stderr)
        return 2
    if score_s is None:
        print("ERROR: --score=FLOAT required", file=sys.stderr)
        return 2
    try:
        score = float(score_s)
    except ValueError:
        print(f"ERROR: --score must be a number, got {score_s!r}", file=sys.stderr)
        return 2
    scores_path = _parse_flag(argv, "--scores-path") or "cache/lfu_decay_scores.json"
    apply = _has_flag(argv, "--apply")
    use_json = _has_flag(argv, "--json")
    try:
        import importlib as _il
        rp_lib = _il.import_module("workflow_kit.tools.release_pipeline_lib")
        result = rp_lib.cmd_lfu_decay_persist(
            url=url, score=score, scores_path=scores_path, apply=apply,
        )
        print(_json.dumps(result, indent=2))
        return 0 if use_json or apply else 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-lru-decay")
def cmd_cache_lru_decay(argv: list[str]) -> int:
    """Evict LRU-stale entries to bring cache size under a cap (v0.8.9+, subcommand 29).

    LRU eviction: sorts entries by timestamp (oldest first), evicts until file size
    is under --max-bytes. In-process wrapper for
    `workflow_kit.cache_size_compare.evict_lru_over_size`.

    Args:
        --max-bytes=INT         target max cache file size in bytes (required)
        --cache-path=PATH       base cache file path (default: ~/.workflow_kit/url_validity_cache.json)
        --json                  JSON output

    Returns 0 on success, 2 on error.
    """
    import json as _json
    max_bytes_s = _parse_flag(argv, "--max-bytes")
    if max_bytes_s is None:
        print("ERROR: --max-bytes=INT required", file=sys.stderr)
        return 2
    try:
        max_bytes = int(max_bytes_s)
    except ValueError:
        print(f"ERROR: --max-bytes must be int, got {max_bytes_s!r}", file=sys.stderr)
        return 2
    cache_path = _parse_flag(argv, "--cache-path")
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_size_compare import evict_lru_over_size
        cache_path_obj = _P(cache_path) if cache_path else None
        evicted = evict_lru_over_size(max_bytes, cache_path_obj)
        if use_json:
            print(_json.dumps(
                {"evicted": evicted, "max_bytes": max_bytes, "cache_path": cache_path},
                indent=2,
            ))
        else:
            print(f"LRU eviction: {evicted} entries removed (target: {max_bytes} bytes)")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-merge-csv")
def cmd_cache_merge_csv(argv: list[str]) -> int:
    """Merge multiple CSV files into the cache (v0.8.9+, subcommand 30).

    Each --csv=PATH is imported (merge=True) into the same target cache.
    Duplicates (by URL) are handled by cache_migration.import_csv_to_cache merge
    logic. Useful for consolidating multiple CSV exports into one cache.

    Args:
        --csv=PATH              input CSV file (repeatable, at least 1 required)
        --cache-path=PATH       target cache file (default: DEFAULT_CACHE_FILE)
        --json                  JSON output

    Returns 0 on success, 2 on error.
    """
    import json as _json
    csvs = [a.split("=", 1)[1] for a in argv if a.startswith("--csv=")]
    if not csvs:
        print("ERROR: --csv=PATH (at least 1, repeatable) required", file=sys.stderr)
        return 2
    cache_path_s = _parse_flag(argv, "--cache-path")
    use_json = _has_flag(argv, "--json")
    try:
        from workflow_kit.cache_migration import import_csv_to_cache
        results: list[dict[str, object]] = []
        for csv_s in csvs:
            r = import_csv_to_cache(csv_s, cache_path_s, merge=True)
            results.append({"csv": csv_s, **r})
        total_imported = sum(int(cast(int, r["imported"])) for r in results)
        total_skipped = sum(int(cast(int, r["skipped"])) for r in results)
        if use_json:
            print(_json.dumps(
                {
                    "merged": results,
                    "cache_path": cache_path_s,
                    "total_imported": total_imported,
                    "total_skipped": total_skipped,
                },
                indent=2,
                default=str,
            ))
        else:
            print(
                f"Merged {len(csvs)} CSV files: "
                f"{total_imported} imported, {total_skipped} skipped"
            )
            for r in results:
                print(
                    f"  {r['csv']}: +{r['imported']} imported, "
                    f"{r['skipped']} skipped (of {r['total_rows']} rows)"
                )
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
