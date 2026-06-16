"""workflow_kit.cache_dashboard_export_cli - CLI for dashboard export (v0.7.51+).

ADR-024 follow-up: dashboard export 의 *CLI opt-in* 의 *operational* 보강.
- run_dashboard_export_cli(argv) -> int
- Reads cache files from --cache-path, exports in json/markdown/html
- Default format: json

CLI 의 *dashboard export* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

import sys


def run_dashboard_export_cli(argv: list[str]) -> int:
    """Run dashboard export CLI from argv (v0.7.51+).

    Usage:
        python -m workflow_kit.cache_dashboard_export_cli --dashboard-export --output=PATH [--format=json|markdown|html] [--cache-path=PATH]

    Args:
        argv: list of CLI arguments (e.g. sys.argv[1:])

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if "--dashboard-export" not in argv:
        print("Usage: cache_dashboard_export_cli --dashboard-export --output=PATH [--format=FORMAT] [--cache-path=PATH]")
        return 1
    output_path = None
    fmt = "json"
    cache_path = None
    for arg in argv:
        if arg.startswith("--output="):
            output_path = arg.split("=", 1)[1]
        elif arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]
        elif arg.startswith("--cache-path="):
            cache_path = arg.split("=", 1)[1]
    if output_path is None:
        print("ERROR: --output=PATH required", file=sys.stderr)
        return 1
    if fmt not in ("json", "markdown", "html"):
        print(f"ERROR: invalid format '{fmt}' (use json|markdown|html)", file=sys.stderr)
        return 1
    try:
        from pathlib import Path
        from workflow_kit.url_validity import _load_cache, cache_file_for_strategy, DEFAULT_CACHE_FILE
        from workflow_kit.cache_dashboard_export import write_dashboard
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
        write_dashboard(merged, output_path, format=fmt)
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_dashboard_export_cli(sys.argv[1:]))
