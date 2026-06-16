"""workflow_kit.workflow_kit_cli - unified CLI dispatcher (consolidated v0.7.52,
extended v0.7.53 with okf-export / okf-import, v0.7.54 with okf-validate /
cache-migrate / release-doctor).

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
    okf-export    --wiki=PATH --out=PATH [--include=SUBSTR]... [--exclude=SUBSTR]...
                  [--json] [--repo-root=PATH] [--no-resolve]
                  [--vcs-commit=SHA] [--vcs-ref=REF]
    okf-import    --bundle=PATH [--staging=PATH] [--mode=strict|loose|auto]
                  [--promote] [--json]
    okf-validate  --bundle=PATH [--mode=strict|loose] [--json]
    cache-migrate [--cache-path=PATH] [--json]
    release-doctor[--skip-packaging] [--skip-doctor] [--skip-state] [--skip-git]

Exit codes: 0 = success (or no alerts), 1 = alerts triggered / operation result, 2 = usage error.

Note: okf-* / cache-* use their own argparse or function-call API internally.
The dispatcher forwards argv verbatim after stripping --command. Their full
arg surface is documented in each module's main() docstring (and via --help).
release-doctor is dispatcher-internal (calls tools.release_pipeline via subprocess).
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


@register("okf-export")
def cmd_okf_export(argv: list[str]) -> int:
    """Forward argv to okf_export.main() — its own argparse handles all flags.
    See okf_export._build_arg_parser() for the full flag surface.
    """
    try:
        from workflow_kit.okf_export import main as okf_export_main
        return okf_export_main(argv)
    except SystemExit as e:
        # argparse calls sys.exit on parse error — convert to rc 2 (usage)
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("okf-import")
def cmd_okf_import(argv: list[str]) -> int:
    """Forward argv to okf_import.main() — its own argparse handles all flags.
    See okf_import._build_arg_parser() for the full flag surface.
    """
    try:
        from workflow_kit.okf_import import main as okf_import_main
        return okf_import_main(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("okf-validate")
def cmd_okf_validate(argv: list[str]) -> int:
    """Validate an OKF v0.1 bundle (lint only, no import / staging / promote).

    Uses okf_import's lint_page() for all 8 rules (V-1 / V-4 / V-R9 / V-T1 /
    OKF §4.1 hard 3 + broken link + unknown key). No subprocess, no staging —
    pure read-only validation. Args:
        --bundle=PATH     OKF bundle root (required)
        --mode=strict|loose  default = strict
        --json            JSON output (otherwise human-readable)
    """
    import json as _json
    bundle = _parse_flag(argv, "--bundle")
    if bundle is None:
        print("ERROR: --bundle=PATH required", file=sys.stderr)
        return 2
    mode = _parse_flag(argv, "--mode") or "strict"
    if mode not in ("strict", "loose"):
        print(f"ERROR: --mode must be 'strict' or 'loose', got {mode!r}", file=sys.stderr)
        return 2
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.okf_import import _parse_bundle_pages, lint_page
        bundle_path = _P(bundle).resolve()
        if not bundle_path.exists():
            print(f"ERROR: --bundle path not found: {bundle_path}", file=sys.stderr)
            return 2
        pages = _parse_bundle_pages(bundle_path)
        # mode is Literal["strict", "loose"] — pass string directly (lint_page signature).
        all_issues: list[dict] = []
        for page in pages:
            for issue in lint_page(page, bundle_path, mode):
                all_issues.append({
                    "page": str(issue.page.relative_to(bundle_path)),
                    "rule": issue.rule,
                    "severity": issue.severity,
                    "message": issue.message,
                })
        if use_json:
            err_count = sum(1 for i in all_issues if i["severity"] == "error")
            print(_json.dumps({
                "bundle": str(bundle_path),
                "mode": mode,
                "pages_checked": len(pages),
                "issues_total": len(all_issues),
                "errors": err_count,
                "issues": all_issues,
            }, indent=2))
        else:
            err_count = sum(1 for i in all_issues if i["severity"] == "error")
            warn_count = sum(1 for i in all_issues if i["severity"] == "warn")
            print(f"OKF validate (mode={mode}): {len(pages)} pages, {err_count} errors, {warn_count} warnings")
            for i in all_issues:
                print(f"  [{i['severity']}] {i['rule']} {i['page']}: {i['message']}")
        return 1 if err_count else 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("cache-migrate")
def cmd_cache_migrate(argv: list[str]) -> int:
    """Migrate v0.7.41 single-strategy cache → 3 per-strategy files (ADR-024).

    Idempotent: re-running on already-migrated cache returns ok without
    touching existing per-strategy files. Args:
        --cache-path=PATH   base cache file (default: DEFAULT_CACHE_FILE)
        --json              JSON output (otherwise human-readable)
    """
    import json as _json
    cache_path_s = _parse_flag(argv, "--cache-path")
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        from workflow_kit.cache_migration import migrate_to_per_strategy_cache
        base = _P(cache_path_s) if cache_path_s else None
        result = migrate_to_per_strategy_cache(base_path=base)
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            if result.get("migrated"):
                print(f"Cache migrated: {result.get('entries_migrated', 0)} entries")
                print(f"  source:  {result.get('source')}")
                print(f"  lru:     {result.get('lru_file')}")
                print(f"  lfu:     {result.get('lfu_file')}")
                print(f"  mixed:   {result.get('mixed_file')}")
            else:
                # No `reason` field in result; infer from per-strategy file existence.
                from pathlib import Path as _P2
                lru_f = _P2(result["lru_file"])
                lfu_f = _P2(result["lfu_file"])
                mixed_f = _P2(result["mixed_file"])
                src_f = _P2(result["source"])
                if lru_f.exists() or lfu_f.exists() or mixed_f.exists():
                    print("No migration needed: per-strategy files already exist")
                elif not src_f.exists():
                    print("No migration needed: source single file does not exist")
                else:
                    print("No migration needed: source file is empty")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-doctor")
def cmd_release_doctor(argv: list[str]) -> int:
    """Release pre-flight: 4-source release-readiness check.

    Wraps `tools/release_pipeline.py validate` (4 checks):
      1. check_packaging: pyproject [tool.setuptools.packages] ↔ disk
      2. workflow_kit.cli.doctor: 7 baseline evaluate
      3. state.json freshness
      4. git status: working tree clean

    Args:
        --skip-packaging   skip check 1
        --skip-doctor      skip check 2
        --skip-state       skip check 3
        --skip-git         skip check 4
    """
    skip = {
        "packaging": _has_flag(argv, "--skip-packaging"),
        "doctor": _has_flag(argv, "--skip-doctor"),
        "state": _has_flag(argv, "--skip-state"),
        "git": _has_flag(argv, "--skip-git"),
    }
    try:
        import subprocess as _sp
        # tools/release_pipeline.py 는 script (package 아님). 절대경로 호출.
        repo_root = _sp.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, timeout=10,
        ).strip()
        release_pipeline = _sp.os.path.join(repo_root, "workflow-source", "tools", "release_pipeline.py")
        cmd = [sys.executable, release_pipeline, "validate", "--json"]
        if skip["packaging"]:
            cmd.append("--skip-packaging")
        if skip["doctor"]:
            cmd.append("--skip-doctor")
        if skip["state"]:
            cmd.append("--skip-state")
        if skip["git"]:
            cmd.append("--skip-git")
        proc = _sp.run(
            cmd, capture_output=True, text=True, timeout=180,
            cwd=repo_root,
        )
        sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        # 0 = all OK, non-zero = at least one failed
        return proc.returncode
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
