"""workflow_kit.cache_analytics_trend_chart_cli - CLI for trend chart (v0.7.51+).

ADR-024 follow-up: cache trend chart 의 *CLI opt-in* 의 *operational* 보강.
- run_trend_chart_cli(argv) -> int
- Reads --snapshots=PATH, renders ASCII chart, prints to stdout
- Optional --metric=total_size (default)
- Exits 0 on success, 1 on error

CLI 의 *trend chart* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

import sys


def run_trend_chart_cli(argv: list[str]) -> int:
    """Run trend chart CLI from argv (v0.7.51+).

    Usage:
        python -m workflow_kit.cache_analytics_trend_chart_cli --trend-chart --snapshots=PATH [--metric=METRIC]

    Args:
        argv: list of CLI arguments (e.g. sys.argv[1:])

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if "--trend-chart" not in argv:
        print("Usage: cache_analytics_trend_chart_cli --trend-chart --snapshots=PATH [--metric=METRIC]")
        return 1
    # Parse args
    snapshots_path = None
    metric = "total_size"
    for arg in argv:
        if arg.startswith("--snapshots="):
            snapshots_path = arg.split("=", 1)[1]
        elif arg.startswith("--metric="):
            metric = arg.split("=", 1)[1]
    if snapshots_path is None:
        print("ERROR: --snapshots=PATH required", file=sys.stderr)
        return 1
    try:
        from workflow_kit.cache_analytics_trend import load_snapshots
        from workflow_kit.cache_analytics_trend_chart import render_trend_chart_ascii
        snapshots = load_snapshots(snapshots_path)
        if not snapshots:
            print("ERROR: no snapshots found", file=sys.stderr)
            return 1
        output = render_trend_chart_ascii(snapshots, metric=metric)
        print(output)
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_trend_chart_cli(sys.argv[1:]))
