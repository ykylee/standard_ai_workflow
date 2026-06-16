"""workflow_kit.cache_analytics_alerting_cli - CLI for threshold-based alerts (v0.7.52+).

ADR-024 follow-up: cache analytics alerting 의 *CLI opt-in* 의 *operational* 보강.
- run_alerting_cli(argv) -> int
- Reads cache files, runs check_alerts, prints alert summary as text
- Optional --max-size / --min-hit-rate / --max-evictions flags
- Exits 0 (no alerts) or 1 (alerts triggered)

CLI 의 *threshold-based alerts* 의 *operational* 의 *low-friction* 정공법.
Zero external dependency, in-repo only.
"""

from __future__ import annotations

import sys


def run_alerting_cli(argv: list[str]) -> int:
    """Run cache analytics alerting CLI from argv (v0.7.52+).

    Usage:
        python -m workflow_kit.cache_analytics_alerting_cli --alert [--max-size=N] [--min-hit-rate=0.5] [--max-evictions=N] [--cache-path=PATH]

    Args:
        argv: list of CLI arguments

    Returns:
        Exit code (0 = no alerts, 1 = alerts triggered, 2 = error)
    """
    if "--alert" not in argv:
        print("Usage: cache_analytics_alerting_cli --alert [--max-size=N] [--min-hit-rate=0.5] [--max-evictions=N]")
        return 2
    # Parse args
    max_size: int | None = None
    min_hit_rate: float | None = None
    max_evictions: int | None = None
    cache_path: str | None = None
    for arg in argv:
        if arg.startswith("--max-size="):
            try:
                max_size = int(arg.split("=", 1)[1])
            except ValueError:
                print("ERROR: invalid --max-size", file=sys.stderr)
                return 2
        elif arg.startswith("--min-hit-rate="):
            try:
                min_hit_rate = float(arg.split("=", 1)[1])
            except ValueError:
                print("ERROR: invalid --min-hit-rate", file=sys.stderr)
                return 2
        elif arg.startswith("--max-evictions="):
            try:
                max_evictions = int(arg.split("=", 1)[1])
            except ValueError:
                print("ERROR: invalid --max-evictions", file=sys.stderr)
                return 2
        elif arg.startswith("--cache-path="):
            cache_path = arg.split("=", 1)[1]
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


if __name__ == "__main__":
    sys.exit(run_alerting_cli(sys.argv[1:]))
