"""workflow_kit.workflow_kit_cli test (v0.7.52).

Replaces 6 per-feature CLI test files.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_cli():
    spec = importlib.util.spec_from_file_location(
        "workflow_kit_cli", str(WORKFLOW_KIT_DIR / "workflow_kit_cli.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["workflow_kit_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_no_args_returns_2_v0_7_52() -> None:
    """run_workflow_kit_cli with no args returns 2 (usage error)."""
    mod = _import_cli()
    assert mod.run_workflow_kit_cli([]) == 2


def test_unknown_command_returns_2_v0_7_52() -> None:
    """run_workflow_kit_cli with unknown command returns 2."""
    mod = _import_cli()
    assert mod.run_workflow_kit_cli(["--command=bogus"]) == 2


def test_alert_no_thresholds_returns_0_v0_7_52() -> None:
    """alert subcommand with no thresholds + no cache returns 0 (no alerts)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli([
        "--command=alert", "--cache-path=/tmp/nonexistent_v0_7_52_cache.json",
    ])
    assert code == 0


def test_dashboard_export_missing_output_returns_2_v0_7_52() -> None:
    """dashboard-export subcommand without --output returns 2."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=dashboard-export"])
    assert code == 2


def test_trend_chart_missing_snapshots_returns_2_v0_7_52() -> None:
    """trend-chart subcommand without --snapshots returns 2."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=trend-chart"])
    assert code == 2


def test_layer2_missing_url_returns_2_v0_7_52() -> None:
    """layer2 subcommand without URL returns 2."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=layer2"])
    assert code == 2


def test_okf_export_missing_wiki_returns_2_v0_7_53() -> None:
    """okf-export subcommand without --wiki returns 2 (argparse usage error).

    v0.7.53 dispatcher extension — okf-export forwards argv to okf_export.main()
    whose argparse requires --wiki. Without it, argparse exits with code 2.
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-export"])
    assert code == 2


def test_okf_import_missing_bundle_returns_2_v0_7_53() -> None:
    """okf-import subcommand without --bundle returns 2 (argparse usage error).

    v0.7.53 dispatcher extension — okf-import forwards argv to okf_import.main()
    whose argparse requires --bundle. Without it, argparse exits with code 2.
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-import"])
    assert code == 2


def test_okf_help_returns_0_v0_7_53() -> None:
    """okf-export --help returns 0 (argparse help exits 0).

    Verifies that the dispatcher's SystemExit passthrough correctly forwards
    argparse's --help exit code (0) rather than converting to 2.
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-export", "--help"])
    assert code == 0


def test_okf_validate_missing_bundle_returns_2_v0_7_54() -> None:
    """okf-validate subcommand without --bundle returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-validate"])
    assert code == 2


def test_okf_validate_invalid_mode_returns_2_v0_7_54() -> None:
    """okf-validate subcommand with invalid --mode returns 2."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-validate", "--bundle=/tmp/none", "--mode=invalid"])
    assert code == 2


def test_cache_migrate_no_op_returns_0_v0_7_54() -> None:
    """cache-migrate on non-existent cache returns 0 (idempotent no-op)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-migrate", "--cache-path=/tmp/nonexistent_v0754_cache.json"])
    assert code == 0


def test_release_doctor_all_skip_returns_0_v0_7_54() -> None:
    """release-doctor with all 4 sources skipped returns 0 (all ok).

    The --skip-* flags disable each of the 4 release-readiness checks
    (packaging, doctor, state, git). With all 4 disabled, the validate
    result is "all skipped = ok" and exit code is 0.
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli([
        "--command=release-doctor",
        "--skip-packaging", "--skip-doctor", "--skip-state", "--skip-git",
    ])
    assert code == 0


def test_cache_migrate_invalid_mode_returns_2_v0_7_55() -> None:
    """cache-migrate with --mode=invalid returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-migrate", "--mode=invalid"])
    assert code == 2


def test_okf_version_check_no_arg_returns_2_v0_7_55() -> None:
    """okf-version-check without --okf-version or --bundle returns 2."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-version-check"])
    assert code == 2


def test_okf_version_check_match_returns_0_v0_7_55() -> None:
    """okf-version-check with matching version (0.1 == 0.1) returns 0."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-version-check", "--okf-version=0.1"])
    assert code == 0


def test_okf_version_check_major_higher_returns_2_v0_7_55() -> None:
    """okf-version-check with major higher (1.0) returns 2 (breaking change)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=okf-version-check", "--okf-version=1.0"])
    assert code == 2


def test_cache_decay_no_scores_returns_2_v0_7_55() -> None:
    """cache-decay without --scores returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-decay"])
    assert code == 2


def test_cache_decay_returns_0_v0_7_55() -> None:
    """cache-decay on a valid scores file returns 0 (decay applied)."""
    import json
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "scores.json"
        sp.write_text(json.dumps({"url1": 1.0, "url2": 0.5}))
        code = mod.run_workflow_kit_cli([
            "--command=cache-decay", f"--scores={sp}", "--half-life=86400",
        ])
        assert code == 0


def test_score_wiki_trend_show_returns_0_v0_7_55() -> None:
    """score-wiki-trend --show returns 0 (subprocess wrapper, no in-process dataclass bug)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=score-wiki-trend", "--show"])
    assert code == 0


def main() -> int:
    test_funcs = [
        test_no_args_returns_2_v0_7_52,
        test_unknown_command_returns_2_v0_7_52,
        test_alert_no_thresholds_returns_0_v0_7_52,
        test_dashboard_export_missing_output_returns_2_v0_7_52,
        test_trend_chart_missing_snapshots_returns_2_v0_7_52,
        test_layer2_missing_url_returns_2_v0_7_52,
        test_okf_export_missing_wiki_returns_2_v0_7_53,
        test_okf_import_missing_bundle_returns_2_v0_7_53,
        test_okf_help_returns_0_v0_7_53,
        test_okf_validate_missing_bundle_returns_2_v0_7_54,
        test_okf_validate_invalid_mode_returns_2_v0_7_54,
        test_cache_migrate_no_op_returns_0_v0_7_54,
        test_release_doctor_all_skip_returns_0_v0_7_54,
        test_cache_migrate_invalid_mode_returns_2_v0_7_55,
        test_okf_version_check_no_arg_returns_2_v0_7_55,
        test_okf_version_check_match_returns_0_v0_7_55,
        test_okf_version_check_major_higher_returns_2_v0_7_55,
        test_cache_decay_no_scores_returns_2_v0_7_55,
        test_cache_decay_returns_0_v0_7_55,
        test_score_wiki_trend_show_returns_0_v0_7_55,
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
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
