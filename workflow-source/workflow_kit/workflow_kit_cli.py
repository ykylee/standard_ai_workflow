"""workflow_kit.workflow_kit_cli - unified CLI dispatcher (consolidated v0.7.52,
extended v0.7.53 with okf-export / okf-import, v0.7.54 with okf-validate /
cache-migrate / release-doctor, v0.7.55 with okf-version-check / cache-decay /
score-wiki-trend, v0.7.56 with okf-cleanup / cache-prune + score-wiki-trend
in-process).

Replaces 6 per-feature CLI modules (cache_dashboard_cli, v_r13_layer2_cli,
cache_analytics_trend_chart_cli, cache_dashboard_export_cli,
phishing_federation_v5_cli, cache_analytics_alerting_cli).

Usage:
    python -m workflow_kit.workflow_kit_cli --command=<name> [args...]

Commands:
    cache-dashboard    [--cache-path=PATH]
    dashboard-export   --output=PATH [--format=json|markdown|html] [--cache-path=PATH]
    trend-chart        --snapshots=PATH [--metric=total_size|total_hits|total_misses]
    alert              [--max-size=N] [--min-hit-rate=0.5] [--max-evictions=N] [--cache-path=PATH]
    layer2             --layer2 URL [--user=USER --token=TOKEN]
    federate           [--phishtank-key=KEY] [--min-confidence=0.0]
    okf-export         --wiki=PATH --out=PATH [--include=SUBSTR]... [--exclude=SUBSTR]...
                       [--json] [--repo-root=PATH] [--no-resolve]
                       [--vcs-commit=SHA] [--vcs-ref=REF]
    okf-import         --bundle=PATH [--staging=PATH] [--mode=strict|loose|auto]
                       [--promote] [--json]
    okf-validate       --bundle=PATH [--mode=strict|loose] [--json]
    okf-version-check  --okf-version=X.Y  OR  --bundle=PATH [--json]
    okf-cleanup        [--staging=PATH] [--older-than=SECONDS] [--apply] [--json]
    cache-migrate      [--cache-path=PATH] [--mode=migrate|split|both]
                       [--lfu-threshold=N] [--json]
    cache-decay        --scores=PATH [--saved-at=ISO8601] [--output=PATH]
                       [--half-life=N] [--json]
    cache-prune        [--cache-path=PATH] [--older-than=SECONDS]
                       [--min-access-count=N] [--apply] [--json]
    release-doctor     [--skip-packaging] [--skip-doctor] [--skip-state] [--skip-git]
    score-wiki-trend   [--record-current | --record-range=N | --show | --json]

Exit codes: 0 = success (or no alerts), 1 = alerts triggered / operation result, 2 = usage error.

Note: okf-* / cache-* use their own argparse or function-call API internally.
The dispatcher forwards argv verbatim after stripping --command. Their full
arg surface is documented in each module's main() docstring (and via --help).
release-doctor and score-wiki-trend (v0.7.56+) call tools/* scripts via
in-process import (no subprocess overhead).
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


@register("okf-version-check")
def cmd_okf_version_check(argv: list[str]) -> int:
    """Check OKF bundle version compatibility (ADR-011 / OKF spec §11).

    Args:
        --okf-version=X.Y   bundle's okf_version (e.g. "0.1")
        --bundle=PATH       read from okf-bundle.yaml manifest if --okf-version absent
        --json              JSON output
    """
    import json as _json
    version = _parse_flag(argv, "--okf-version")
    bundle = _parse_flag(argv, "--bundle")
    use_json = _has_flag(argv, "--json")
    if version is None and bundle is None:
        print("ERROR: --okf-version=X.Y or --bundle=PATH required", file=sys.stderr)
        return 2
    # If bundle given and no version, read from okf-bundle.yaml manifest
    if version is None and bundle is not None:
        from pathlib import Path as _P
        manifest = _P(bundle) / "okf-bundle.yaml"
        if not manifest.exists():
            print(f"ERROR: --bundle path has no okf-bundle.yaml: {bundle}", file=sys.stderr)
            return 2
        # simple regex: `okf_version: "0.1"` (single-line)
        import re as _re
        text = manifest.read_text(encoding="utf-8")
        m = _re.search(r'^\s*okf_version\s*:\s*["\']?(\d+\.\d+(?:\.\d+)?)["\']?', text, _re.MULTILINE)
        if m is None:
            print(f"ERROR: okf_version not found in {manifest}", file=sys.stderr)
            return 2
        version = m.group(1)
    try:
        from workflow_kit.okf_import import _check_version_compatibility
        result = _check_version_compatibility(version)
        out = {
            "okf_version": result.bundle_version,
            "our_version": result.our_version,
            "status": result.status,
            "message": result.message,
        }
        if use_json:
            print(_json.dumps(out, indent=2))
        else:
            print(f"OKF version check: bundle={out['okf_version']}, our={out['our_version']}")
            print(f"  status: {out['status']}")
            print(f"  message: {out['message']}")
        # rc: 0 = pass, 1 = warn, 2 = error
        if result.status == "error":
            return 2
        if result.status == "warn":
            return 1
        return 0
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


@register("score-wiki-trend")
def cmd_score_wiki_trend(argv: list[str]) -> int:
    """Wiki maintainability score trend (v0.7.1+).

    In-process wrapper (v0.7.56+, previously subprocess) for
    `tools/score_wiki_trend.py`. v0.7.55 의 release-doctor in-process 와 동일
    정공법: `workflow-source/` 를 sys.path 에 insert → `import tools.score_wiki_trend`
    → `main(argv)` 호출.

    v0.7.55 의 subprocess fallback 원인: tools/ 가 *package* 가 아니어서
    `import tools.score_wiki_trend` 가 fail. v0.7.56 에서 `tools/__init__.py`
    추가 + sys.path 조정으로 in-process 가능.

    Args (forwarded verbatim):
        --record-current   record current HEAD score
        --record-range=N   backfill N recent commits
        --show             ASCII chart of trend
        --json             JSON output
        --alert --baseline=X  baseline 비교 (dim alert)
    """
    try:
        from pathlib import Path as _P
        import importlib as _il
        kit_dir = _P(__file__).resolve().parent
        workflow_source_dir = kit_dir.parent
        if str(workflow_source_dir) not in sys.path:
            sys.path.insert(0, str(workflow_source_dir))
        # tools/ is now a package (v0.7.56+ with __init__.py) → import as module
        mod = _il.import_module("tools.score_wiki_trend")
        # main() uses argparse.parse_args() (reads sys.argv[1:]). Patch sys.argv
        # in-place to forward our argv. Restore on exit (incl. exceptions).
        old_argv = sys.argv
        try:
            sys.argv = ["score_wiki_trend", *argv]
            return mod.main()
        finally:
            sys.argv = old_argv
    except SystemExit as e:
        # argparse / main() may call sys.exit — convert to rc
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
                m = all_results["migrate"]
                if m.get("migrated"):
                    print(f"[migrate] OK: {m.get('entries_migrated', 0)} entries → mixed file")
                else:
                    print(f"[migrate] no-op (per-strategy already exist or source absent)")
            if "split" in all_results:
                s = all_results["split"]
                if s.get("split"):
                    print(f"[split] OK: {s.get('lru_entries', 0)} LRU + {s.get('lfu_entries', 0)} LFU (threshold={lfu_threshold})")
                else:
                    print(f"[split] no-op (mixed file absent or empty)")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-doctor")
def cmd_release_doctor(argv: list[str]) -> int:
    """Release pre-flight: 4-source release-readiness check (in-process, v0.7.55+).

    Calls `tools.release_pipeline_lib.cmd_validate` in-process (no subprocess
    overhead, no script-path coupling). 4 checks:
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
        # Find workflow-source/tools dir relative to this module.
        # workflow_kit_cli.py lives at workflow-source/workflow_kit/
        # → tools/release_pipeline_lib.py is at workflow-source/tools/
        from pathlib import Path as _P
        kit_dir = _P(__file__).resolve().parent
        tools_dir = kit_dir.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        from release_pipeline_lib import cmd_validate as _cmd_validate
        results = _cmd_validate(
            skip_packaging=skip["packaging"],
            skip_doctor=skip["doctor"],
            skip_state=skip["state"],
            skip_git=skip["git"],
        )
        print(json.dumps(results, indent=2, default=str))
        # rc: 0 = all OK, 1 = at least one source not ok
        any_fail = any(
            v.get("ok") is False for v in results.values() if isinstance(v, dict)
        )
        return 1 if any_fail else 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("okf-cleanup")
def cmd_okf_cleanup(argv: list[str]) -> int:
    """Clean up OKF staging directory (v0.7.56+, dispatcher subcommand 15).

    Removes files in `--staging` directory older than `--older-than` seconds
    (mtime check). Default `--dry-run` reports what would be removed without
    touching disk. Args:
        --staging=PATH         staging directory (default = cwd/.okf-staging)
        --older-than=SECONDS   max age in seconds (default = no age filter = all)
        --apply                actually remove (default is dry-run)
        --json                 JSON output
    """
    import json as _json
    staging_s = _parse_flag(argv, "--staging")
    older_than_s = _parse_flag(argv, "--older-than")
    apply = _has_flag(argv, "--apply")
    use_json = _has_flag(argv, "--json")
    older_than = float(older_than_s) if older_than_s else None
    try:
        from pathlib import Path as _P
        from workflow_kit.okf_import import cleanup_staging
        staging_path = _P(staging_s) if staging_s else _P.cwd() / ".okf-staging"
        result = cleanup_staging(
            staging_path,
            older_than_seconds=older_than,
            dry_run=not apply,
        )
        if use_json:
            print(_json.dumps(result, indent=2))
        else:
            mode = "APPLY" if apply else "DRY-RUN"
            print(f"OKF cleanup ({mode}): {result['staging_dir']}")
            print(f"  scanned: {result['scanned']}")
            print(f"  removed: {result['removed']}")
            print(f"  kept:    {result['kept']}")
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
# release-pipeline wrappers (v0.7.56+, dispatcher subcommand 17-23)
# ---------------------------------------------------------------------------

def _wrap_release_pipeline(argv: list[str], wrapper_name: str, **kwargs) -> int:
    """Helper: call a release_pipeline_lib wrapper with JSON output + rc conversion.

    Args:
        argv: dispatcher argv
        wrapper_name: name of the function in release_pipeline_lib
        **kwargs: forwarded to the wrapper

    Returns:
        rc: 0 = success, 1 = warn, 2 = error/usage
    """
    import json as _json
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        kit_dir = _P(__file__).resolve().parent
        tools_dir = kit_dir.parent / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import release_pipeline_lib as _lib
        fn = getattr(_lib, wrapper_name)
        result = fn(**kwargs)
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            mode = result.get("mode", "?")
            print(f"{wrapper_name}: mode={mode}")
            for k, v in result.items():
                if k == "mode":
                    continue
                print(f"  {k}: {v}")
        # rc: success if mode=apply or dry-run OK; error if mode=error
        if result.get("mode") == "error":
            return 2
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-bump")
def cmd_release_bump(argv: list[str]) -> int:
    """Bump pyproject.toml version (v0.7.56+, dispatcher subcommand 17).

    Args:
        --to=VERSION    explicit target version (e.g. "0.7.56")
        --patch         increment patch (default if no --to)
        --minor         increment minor
        --major         increment major
        --no-init       skip workflow_kit/__init__.py __version__ sync
        --apply         actually write (default dry-run)
        --json          JSON output
    """
    to = _parse_flag(argv, "--to")
    kwargs = {
        "apply": _has_flag(argv, "--apply"),
        "no_init": _has_flag(argv, "--no-init"),
        "to": to,
        "patch": _has_flag(argv, "--patch"),
        "minor": _has_flag(argv, "--minor"),
        "major": _has_flag(argv, "--major"),
    }
    return _wrap_release_pipeline(argv, "cmd_version_bump", **kwargs)


@register("release-note")
def cmd_release_note(argv: list[str]) -> int:
    """Draft release note (v0.7.56+, dispatcher subcommand 18).

    Args:
        --to=VERSION       target version (required)
        --from-tag=TAG     source tag (required)
        --apply            actually write Beta-v<X>.md (default dry-run)
        --json             JSON output
    """
    to = _parse_flag(argv, "--to")
    from_tag = _parse_flag(argv, "--from-tag")
    if to is None or from_tag is None:
        print("ERROR: --to=VERSION and --from-tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_note_draft",
        to=to, from_tag=from_tag, dry_run=not _has_flag(argv, "--apply"),
    )


@register("release-changelog")
def cmd_release_changelog(argv: list[str]) -> int:
    """Generate CHANGELOG.md body (v0.7.56+, dispatcher subcommand 19).

    Args:
        --from-tag=TAG     start tag (default = all history)
        --to-tag=REF       end tag/REF (default = HEAD)
        --apply            actually write CHANGELOG.md (default dry-run)
        --json             JSON output
    """
    from_tag = _parse_flag(argv, "--from-tag")
    to_tag = _parse_flag(argv, "--to-tag") or "HEAD"
    return _wrap_release_pipeline(
        argv, "cmd_changelog_gen",
        from_tag=from_tag, to_tag=to_tag, dry_run=not _has_flag(argv, "--apply"),
    )


@register("release-create")
def cmd_release_create(argv: list[str]) -> int:
    """Create GitHub Release (v0.7.56+, dispatcher subcommand 20, destructive).

    Args:
        --version=VERSION        target version (required)
        --notes-template=PATH    notes template file (optional)
        --skip-validate          skip 4-source validate (not recommended)
        --auto-bump              auto-bump if remote tag exists
        --apply                  actually create release (default dry-run)
        --json                   JSON output
    """
    version = _parse_flag(argv, "--version")
    if version is None:
        print("ERROR: --version=VERSION required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_release",
        version=version,
        notes_template=_parse_flag(argv, "--notes-template"),
        skip_validate=_has_flag(argv, "--skip-validate"),
        auto_bump=_has_flag(argv, "--auto-bump"),
        apply=_has_flag(argv, "--apply"),
    )


@register("release-verify")
def cmd_release_verify(argv: list[str]) -> int:
    """Verify GitHub Release (v0.7.56+, dispatcher subcommand 21, read-only).

    Args:
        --tag=TAG    tag to verify (e.g. v0.7.56 or 0.7.56, required)
        --json       JSON output
    """
    tag = _parse_flag(argv, "--tag")
    if tag is None:
        print("ERROR: --tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(argv, "cmd_verify", tag=tag)


@register("release-rollback")
def cmd_release_rollback(argv: list[str]) -> int:
    """Delete GitHub Release + git tag (v0.7.56+, dispatcher subcommand 22, destructive).

    Args:
        --tag=TAG     tag to delete (required)
        --apply       actually delete (default dry-run)
        --json        JSON output
    """
    tag = _parse_flag(argv, "--tag")
    if tag is None:
        print("ERROR: --tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_rollback",
        tag=tag, apply=_has_flag(argv, "--apply"),
    )


@register("release-dist")
def cmd_release_dist(argv: list[str]) -> int:
    """Build wheel + sdist (v0.7.56+, dispatcher subcommand 23).

    Args:
        --apply     actually run `python3 -m build` (default dry-run)
        --json      JSON output
    """
    return _wrap_release_pipeline(argv, "cmd_dist", apply=_has_flag(argv, "--apply"))


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
