"""workflow_kit.workflow_kit_cli - unified CLI dispatcher (consolidated v0.7.52).

Replaces 6 per-feature CLI modules (cache_dashboard_cli, v_r13_layer2_cli,
cache_analytics_trend_chart_cli, cache_dashboard_export_cli,
phishing_federation_v5_cli, cache_analytics_alerting_cli).

Usage:
    python -m workflow_kit.workflow_kit_cli --command=<name> [args...]

Commands:
    cache-dashboard [--cache-path=PATH]
    dashboard-export --output=PATH [--format=json|markdown|html] [--cache-path=PATH]
    trend-chart --snapshots=PATH [--metric=total_size|total_hits|total_misses]
    alert [--max-size=N] [--min-hit-rate=0.5] [--max-evictions=N] [--cache-path=PATH]
    layer2 --layer2 URL [--user=USER --token=TOKEN]
    federate [--phishtank-key=KEY] [--min-confidence=0.0]

Exit codes: 0 = success (or no alerts), 1 = alerts triggered / operation result, 2 = usage error.
"""

from __future__ import annotations

import json
import sys
from typing import Callable


COMMANDS: dict[str, Callable[[list[str]], int]] = {}


def register(name: str):
    def decorator(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        COMMANDS[name] = fn
        return fn
    return decorator


def _print_usage() -> None:
    print("Usage: workflow_kit_cli --command=<name> [args...]")
    print("Commands:")
    for name in sorted(COMMANDS):
        print(f"  {name}")


def _parse_flag(argv: list[str], flag: str) -> str | None:
    for arg in argv:
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


def _has_flag(argv: list[str], flag: str) -> bool:
    return flag in argv


@register("cache-dashboard")
def cmd_cache_dashboard(argv: list[str]) -> int:
    cache_path = _parse_flag(argv, "--cache-path")
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_dashboard import cache_dashboard
        base = Path(cache_path) if cache_path else DEFAULT_CACHE_FILE
        merged: dict = {}
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
    cache_path = _parse_flag(argv, "--cache-path")
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_dashboard import write_dashboard
        base = Path(cache_path) if cache_path else DEFAULT_CACHE_FILE
        merged: dict = {}
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
        write_dashboard(merged, output, format=fmt)
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
    try:
        from workflow_kit.cache_analytics_trend import load_snapshots
        from workflow_kit.cache_analytics_trend_chart import render_trend_chart_ascii
        snapshots = load_snapshots(snapshots_path)
        if not snapshots:
            print("ERROR: no snapshots found", file=sys.stderr)
            return 2
        print(render_trend_chart_ascii(snapshots, metric=metric))
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
        merged: dict = {}
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


@register("layer2")
def cmd_layer2(argv: list[str]) -> int:
    # Find URL (first non-flag arg)
    url = None
    for arg in argv:
        if not arg.startswith("--") and arg:
            url = arg
            break
    if url is None:
        print("ERROR: URL required", file=sys.stderr)
        return 2
    user = _parse_flag(argv, "--user")
    token = _parse_flag(argv, "--token")
    try:
        from workflow_kit.v_r13_commit_diff import run_layer2_pipeline
        result = run_layer2_pipeline(url, user=user, token=token)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("federate")
def cmd_federate(argv: list[str]) -> int:
    phishtank_key = _parse_flag(argv, "--phishtank-key")
    min_conf_s = _parse_flag(argv, "--min-confidence")
    min_confidence = float(min_conf_s) if min_conf_s else 0.0
    try:
        from workflow_kit.phishing_federation import (
            fetch_federated_phishing_urls,
            build_default_sources,
        )
        sources = build_default_sources(phishtank_api_key=phishtank_key)
        result = fetch_federated_phishing_urls(sources, min_confidence=min_confidence)
        output = [
            {"url": u, "confidence": c, "sources": s}
            for u, c, s in result
        ]
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def run_workflow_kit_cli(argv: list[str]) -> int:
    """Run workflow_kit_cli from argv (v0.7.52+)."""
    if "--command" not in argv[0:1] and not any(a.startswith("--command=") for a in argv):
        _print_usage()
        return 2
    cmd_name = None
    rest: list[str] = []
    for arg in argv:
        if arg == "--command" or arg.startswith("--command="):
            if "=" in arg:
                cmd_name = arg.split("=", 1)[1]
        else:
            rest.append(arg)
    if cmd_name is None:
        _print_usage()
        return 2
    if cmd_name not in COMMANDS:
        _print_usage()
        return 2
    return COMMANDS[cmd_name](rest)


if __name__ == "__main__":
    sys.exit(run_workflow_kit_cli(sys.argv[1:]))
