"""workflow_kit.cache_dashboard_cli - CLI for --cache-dashboard flag (v0.7.48+).

ADR-024 follow-up: per-strategy cache dashboard 의 *CLI opt-in* 의 *operational* 보강.
- run_cache_dashboard(argv) -> int: parses argv for --cache-dashboard flag, runs dashboard
- Prints formatted table to stdout
- Exits 0 on success, 1 on error

CLI 의 *cache_dashboard* opt-in path 의 *low-friction* 정공법.
"""

from __future__ import annotations

import sys


def run_cache_dashboard(argv: list[str]) -> int:
    """Run cache dashboard from CLI argv (v0.7.48+).

    Usage:
        python -m workflow_kit.cache_dashboard_cli --cache-dashboard [--cache-path=PATH]

    Args:
        argv: list of CLI arguments (e.g. sys.argv[1:])

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if "--cache-dashboard" not in argv:
        print("Usage: cache_dashboard_cli --cache-dashboard [--cache-path=PATH]")
        return 1
    # Optional --cache-path
    cache_path = None
    for arg in argv:
        if arg.startswith("--cache-path="):
            cache_path = arg.split("=", 1)[1]
            break
    try:
        from workflow_kit.url_validity import _load_cache, cache_stats_per_strategy
        from workflow_kit.cache_dashboard import cache_dashboard
        # Load all 3 strategy caches and merge into one dict
        from pathlib import Path
        from workflow_kit.url_validity import DEFAULT_CACHE_FILE, cache_file_for_strategy
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
        output = cache_dashboard(merged)
        print(output)
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_cache_dashboard(sys.argv[1:]))
