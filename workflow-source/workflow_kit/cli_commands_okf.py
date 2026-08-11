"""workflow_kit.cli_commands_okf - OKF bundle dispatcher subcommands.

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
부분 분할). 5개 handler: okf-export / okf-import / okf-version-check /
okf-validate / okf-cleanup.

`@register` 가 import 시점에 `cli_registry.COMMANDS` 에 등록하고,
workflow_kit_cli 가 본 모듈의 handler 를 재-export 한다 — arg surface 문서는
workflow_kit_cli 모듈 docstring 이 계속 정본이다.
"""

from __future__ import annotations

import sys
from typing import Any, Literal, cast

from workflow_kit.cli_registry import _has_flag, _parse_flag, register

__all__ = [
    "cmd_okf_export",
    "cmd_okf_import",
    "cmd_okf_version_check",
    "cmd_okf_validate",
    "cmd_okf_cleanup",
]


@register("okf-export")
def cmd_okf_export(argv: list[str]) -> int:
    """Forward argv to okf_export.main() — its own argparse handles all flags.
    See okf_export._build_arg_parser() for the full flag surface.
    """
    try:
        from workflow_kit.okf_export import main as okf_export_main
        return okf_export_main(argv)
    except SystemExit as e:
        # argparse / main() may call sys.exit — convert to rc
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
    mode_literal = cast(Literal["strict", "loose"], mode)
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
        all_issues: list[dict[str, Any]] = []
        for page in pages:
            for issue in lint_page(page, bundle_path, mode_literal):
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
