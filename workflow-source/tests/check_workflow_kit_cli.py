"""workflow_kit.workflow_kit_cli test (v0.7.52).

Replaces 6 per-feature CLI test files.
"""

from __future__ import annotations

import importlib.util

# 단독 27s 실측 (2026-08-14) — 병렬 부하에서 2배로 늘어지면 기본 60s 상한을 넘는다
# (같은 날 slash 축 전량에서 TIMEOUT flake 실측). 행 검출은 150s 로 충분.
CHECK_TIMEOUT_S = 150
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
    """release-doctor with all sources skipped returns 0 (all ok).

    The --skip-* flags disable each release-readiness check (packaging,
    doctor, state, git, mypy). With all disabled, the validate result is
    "all skipped = ok" and exit code is 0.

    mypy 는 v0.11.12 에 5번째 source 로 붙었는데 이 test 는 따라오지 않아, '전부
    skip' 이라면서 mypy 를 매번 실제로 돌렸다 (~3.9s, TASK-2026-09-28-main-008 —
    `check_release_pipeline_lib` 에서 main-007 이 고친 것과 같은 모양).
    """
    import contextlib
    import io
    import json
    mod = _import_cli()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.run_workflow_kit_cli([
            "--command=release-doctor",
            "--skip-packaging", "--skip-doctor", "--skip-state", "--skip-git",
            "--skip-mypy",
        ])
    assert code == 0, buf.getvalue()[-500:]
    # 플래그가 버려지면 mypy 가 돌고도 ok 라 rc 만으로는 안 보인다 — skipped 를 단언.
    assert json.loads(buf.getvalue()).get("mypy") == {"ok": True, "skipped": True}, buf.getvalue()[-500:]


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


def test_score_wiki_trend_json_in_process_v0_7_56() -> None:
    """score-wiki-trend --json in-process (v0.7.56, was subprocess in v0.7.55).

    Verifies `tools/__init__.py` (v0.7.56 NEW) + workflow_kit_cli 의
    in-process import 가 정상 동작. --json 은 read-only 라 side effect 없음.
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=score-wiki-trend", "--json"])
    assert code == 0


def test_score_wiki_trend_record_current_in_process_v0_7_56(tmp_path=None) -> None:
    """score-wiki-trend --record-current in-process (v0.7.56).

    dispatcher 가 in-process 로 `record_current` 에 닿아 history 에 row 1개를
    append 하는지 잰다.

    **history 는 임시 사본에 쓰고 점수는 stub 한다** (TASK-2026-09-28-main-008).
    예전에는 git 추적 파일인 실제 `.score_history.jsonl` 에 append 했다가 되돌렸다 —
    그 ~9s 동안 병렬 구간의 `check_wiki_trend` 가 같은 파일을 읽는다. 그 9s 는
    전부 실제 점수 도구 실행이었고, 점수 자체는 `check_wiki_score` 가 잰다.
    기록 경로를 임시로 돌리는 방식은 `check_v0_7_15_config_thresholds` 와 같다.
    """
    import importlib
    import json
    import tempfile
    from unittest import mock
    mod = _import_cli()
    swt = importlib.import_module("workflow_kit.tools.score_wiki_trend")
    real_history = SOURCE_ROOT / "workflow_kit" / "tools" / ".score_history.jsonl"
    real_before = real_history.read_bytes() if real_history.exists() else b""
    stub_score = {"scores": {d: 4.0 for d in swt.DIMS}, "overall": 4.0, "grade": "A"}
    with tempfile.TemporaryDirectory() as tmp:
        history_path = Path(tmp) / ".score_history.jsonl"
        history_path.write_bytes(real_before)  # 실물 모양 그대로에 append
        before_lines = len([ln for ln in real_before.decode("utf-8").splitlines() if ln.strip()])
        with mock.patch.object(swt, "HISTORY_PATH", history_path), \
                mock.patch.object(swt, "compute_score_at_commit", lambda c: dict(stub_score)):
            code = mod.run_workflow_kit_cli(["--command=score-wiki-trend", "--record-current"])
        assert code == 0
        after = history_path.read_text(encoding="utf-8")
        after_lines = len([ln for ln in after.splitlines() if ln.strip()])
        assert after_lines == before_lines + 1, f"expected 1 new row, got {after_lines - before_lines}"
        # last row is valid JSON — stub 점수가 dispatcher 를 거쳐 기록됐다
        last = json.loads(after.splitlines()[-1])
        assert "commit" in last and last.get("overall") == 4.0, f"기록된 row: {last}"
    real_after = real_history.read_bytes() if real_history.exists() else b""
    assert real_after == real_before, "실제 .score_history.jsonl 이 바뀌었다 — 기록이 임시 사본으로 안 갔다"


def test_okf_cleanup_dry_run_v0_7_56() -> None:
    """okf-cleanup --dry-run (default) returns 0, doesn't remove (v0.7.56+)."""
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "staging"
        sp.mkdir()
        (sp / "page1.md").write_text("content", encoding="utf-8")
        (sp / "page2.md").write_text("content", encoding="utf-8")
        code = mod.run_workflow_kit_cli([
            "--command=okf-cleanup", f"--staging={sp}", "--json",
        ])
        assert code == 0
        # dry-run by default — files still exist
        assert (sp / "page1.md").exists()
        assert (sp / "page2.md").exists()


def test_okf_cleanup_apply_removes_v0_7_56() -> None:
    """okf-cleanup --apply actually removes files (v0.7.56+)."""
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "staging"
        sp.mkdir()
        (sp / "old.md").write_text("content", encoding="utf-8")
        # Make file old
        import time
        old_time = time.time() - 86400 * 2  # 2 days old
        import os
        os.utime(sp / "old.md", (old_time, old_time))
        code = mod.run_workflow_kit_cli([
            "--command=okf-cleanup", f"--staging={sp}",
            "--older-than=86400", "--apply", "--json",
        ])
        assert code == 0
        # file removed
        assert not (sp / "old.md").exists()


def test_cache_prune_dry_run_v0_7_56() -> None:
    """cache-prune --dry-run returns 0, doesn't modify cache (v0.7.56+)."""
    import json
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        # write a small per-strategy cache (mixed)
        cache_data = {
            "https://example.com/a": {
                "timestamp": 0.0,  # very old
                "issues": [],
                "access_count": 0,
            },
            "https://example.com/b": {
                "timestamp": 9999999999.0,  # future
                "issues": [],
                "access_count": 100,
            },
        }
        from workflow_kit.url_validity import cache_file_for_strategy
        cf = cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        # dry-run: report only
        code = mod.run_workflow_kit_cli([
            "--command=cache-prune", f"--cache-path={base}", "--json",
        ])
        assert code == 0
        # file still exists with same data
        assert cf.exists()
        after = json.loads(cf.read_text(encoding="utf-8"))
        assert len(after) == 2


def test_cache_prune_apply_removes_old_v0_7_56() -> None:
    """cache-prune --apply actually removes old entries (v0.7.56+)."""
    import json
    import tempfile
    import time
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "cache.json"
        cache_data = {
            "https://example.com/old": {
                "timestamp": time.time() - 86400 * 7,  # 7 days old
                "issues": [],
                "access_count": 0,
            },
            "https://example.com/fresh": {
                "timestamp": time.time(),
                "issues": [],
                "access_count": 5,
            },
        }
        from workflow_kit.url_validity import cache_file_for_strategy
        cf = cache_file_for_strategy(base, "mixed")
        cf.write_text(json.dumps(cache_data), encoding="utf-8")
        # apply: remove entries older than 1 day with access_count < 5
        code = mod.run_workflow_kit_cli([
            "--command=cache-prune", f"--cache-path={base}",
            "--older-than=86400", "--min-access-count=5", "--apply", "--json",
        ])
        assert code == 0
        after = json.loads(cf.read_text(encoding="utf-8"))
        # only 'fresh' should remain (it's new AND has access_count >= 5)
        assert "https://example.com/fresh" in after
        assert "https://example.com/old" not in after


def test_release_bump_dry_run_v0_7_56() -> None:
    """release-bump (dry-run, --patch) returns 0 with mode=dry-run (v0.7.56+)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=release-bump", "--patch", "--json"])
    assert code == 0


def test_release_create_missing_version_returns_2_v0_7_56() -> None:
    """release-create without --version returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=release-create", "--json"])
    assert code == 2


def test_release_rollback_missing_tag_returns_2_v0_7_56() -> None:
    """release-rollback without --tag returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=release-rollback", "--json"])
    assert code == 2


def test_release_dist_dry_run_v0_7_56() -> None:
    """release-dist (dry-run) returns 0 with mode=dry-run (v0.7.56+)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=release-dist", "--json"])
    assert code == 0


def test_release_changelog_dry_run_v0_7_56() -> None:
    """release-changelog (dry-run) returns 0 with mode=dry-run (v0.7.56+)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=release-changelog", "--json"])
    assert code == 0


def test_cache_decay_csv_inplace_v0_7_56() -> None:
    """cache-decay --inplace on CSV file (v0.7.56+)."""
    import os
    import tempfile
    import time
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "scores.csv"
        cp.write_text("url,decay_score\nhttps://hot.com/,100.0\nhttps://warm.com/,50.0\n", encoding="utf-8")
        old = time.time() - 86400 * 7
        os.utime(cp, (old, old))
        code = mod.run_workflow_kit_cli([
            "--command=cache-decay", f"--scores={cp}",
            "--inplace", "--half-life=86400", "--json",
        ])
        assert code == 0
        # CSV was modified (decayed)
        content = cp.read_text(encoding="utf-8")
        # Decayed values are << 100 / 50
        assert "100.0" not in content, f"CSV should be decayed, got: {content}"


def test_cache_decay_inplace_rejects_non_csv_v0_7_56() -> None:
    """cache-decay --inplace rejects non-CSV file (v0.7.56+)."""
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        jp = Path(tmp) / "scores.json"
        jp.write_text("{}", encoding="utf-8")
        code = mod.run_workflow_kit_cli([
            "--command=cache-decay", f"--scores={jp}",
            "--inplace", "--json",
        ])
        assert code == 2  # usage error


def test_cache_import_csv_no_arg_returns_2_v0_7_57() -> None:
    """cache-import-csv without --csv returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-import-csv", "--json"])
    assert code == 2


def test_cache_import_csv_roundtrip_v0_7_57() -> None:
    """cache-import-csv imports CSV into cache file (v0.7.57+)."""
    import json
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "cache.json"
        csv_p = Path(tmp) / "urls.csv"
        csv_p.write_text(
            "url,status,timestamp,access_count\n"
            "https://a.com/,ok,1000.0,5\n"
            "https://b.com/,ok,2000.0,10\n",
            encoding="utf-8",
        )
        code = mod.run_workflow_kit_cli([
            "--command=cache-import-csv", f"--csv={csv_p}",
            f"--cache-path={cp}", "--json",
        ])
        assert code == 0
        # Verify entries exist in cache file
        assert cp.exists()
        data = json.loads(cp.read_text(encoding="utf-8"))
        assert "https://a.com/" in data
        assert "https://b.com/" in data


def test_cache_export_json_no_output_returns_2_v0_7_57() -> None:
    """cache-export-json without --output returns 2 (usage error)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-export-json", "--json"])
    assert code == 2


def test_cache_export_json_roundtrip_v0_7_57() -> None:
    """cache-export-json exports cache entries to JSON file (v0.7.57+)."""
    import json
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "cache.json"
        op = Path(tmp) / "export.json"
        # Seed cache
        cp.write_text(json.dumps({
            "https://a.com/": {"timestamp": 1000.0, "issues": [], "access_count": 5},
        }), encoding="utf-8")
        code = mod.run_workflow_kit_cli([
            "--command=cache-export-json", f"--output={op}",
            f"--cache-path={cp}", "--json",
        ])
        assert code == 0
        # Verify exported file
        assert op.exists()
        data = json.loads(op.read_text(encoding="utf-8"))
        assert "https://a.com/" in data
        assert data["https://a.com/"]["access_count"] == 5


def test_cache_merge_multi_no_op_v0_7_57() -> None:
    """cache-merge-multi with no LRU/LFU files returns 0 with merged=False (v0.7.57+)."""
    import json
    import tempfile
    from pathlib import Path
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "cache.json"
        # No LRU/LFU files exist
        code = mod.run_workflow_kit_cli([
            "--command=cache-merge-multi", f"--cache-path={cp}", "--json",
        ])
        assert code == 0


def test_consumer_metrics_registered_v0_7_58() -> None:
    """consumer-metrics is registered as dispatcher subcommand 27 (v0.7.58+)."""
    mod = _import_cli()
    assert "consumer-metrics" in mod.COMMANDS
    assert callable(mod.COMMANDS["consumer-metrics"])


def test_consumer_metrics_invalid_days_returns_2_v0_7_58() -> None:
    """consumer-metrics with --days=0 or --days=100 returns 2 (usage error)."""
    mod = _import_cli()
    # days=0
    code = mod.run_workflow_kit_cli(["--command=consumer-metrics", "--days=0", "--json"])
    assert code == 2
    # days=100 (out of 1-90 range)
    code = mod.run_workflow_kit_cli(["--command=consumer-metrics", "--days=100", "--json"])
    assert code == 2


def _fake_gh_run():  # type: ignore[no-untyped-def]
    """`gh` 호출만 가로채는 `subprocess.run` 대역 (TASK-2026-09-28-main-008).

    consumer-metrics test 들은 rc 0(인증됨)과 1(미인증)을 둘 다 받아들였다 —
    실제 GitHub API 호출 5종 × 2 test 가 판정에 기여하는 것이 없었고, 게이트를
    네트워크에 묶었다 (~4s). 대역은 인증 성공 + 빈 응답을 돌려줘 rc=0 경로를
    결정적으로 밟게 한다. 호출 목록을 남겨 경로가 실제로 gh 층까지 갔는지 본다.
    """
    import subprocess as _sp
    real_run = _sp.run
    calls: list[list[str]] = []

    def run(cmd, *a, **k):  # type: ignore[no-untyped-def]
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "gh":
            calls.append(list(cmd))
            return _sp.CompletedProcess(cmd, 0, "", "")
        return real_run(cmd, *a, **k)

    return run, calls


def test_consumer_metrics_default_argv_v0_7_58() -> None:
    """consumer-metrics with no args uses defaults (--days=14, --repo=ykylee/standard_ai_workflow).

    Skips when gh CLI is not authenticated (e.g. CI without GITHUB_TOKEN) — returns
    1 (gh auth fail) or 0 (success) are both acceptable; the test only fails on
    rc=2 (usage error) which would mean the dispatcher is broken.
    """
    from unittest import mock
    mod = _import_cli()
    fake_run, calls = _fake_gh_run()
    with mock.patch("subprocess.run", fake_run):
        code = mod.run_workflow_kit_cli(["--command=consumer-metrics", "--json"])
    # 대역이 인증 성공을 주므로 rc 는 0 이어야 한다 (2 = usage error = dispatcher 고장)
    assert code == 0, f"expected 0, got {code}"
    # 기본 repo 가 gh 층까지 전달됐다
    assert any("ykylee/standard_ai_workflow" in " ".join(c) for c in calls), f"gh 호출: {calls}"


def test_consumer_metrics_in_process_v0_7_59() -> None:
    """consumer-metrics dispatcher uses in-process import (v0.7.59+, was subprocess in v0.7.58).

    Verifies:
    1. dispatcher argv forwarding reaches consumer_metrics.main() (default repo applies)
    2. workflow_kit.tools.consumer_metrics is imported in-process (no subprocess fork)
    3. days validation remains single-source (consumer_metrics.main() rc=2 on out-of-range)
    """
    import importlib
    import sys as _sys
    # Reset import state so we observe the dispatcher's import
    for mod_name in list(_sys.modules.keys()):
        if mod_name == "workflow_kit.tools.consumer_metrics" or mod_name.startswith("workflow_kit.tools.consumer_metrics."):
            del _sys.modules[mod_name]
    mod = _import_cli()
    # Invoke dispatcher with default argv. gh 는 대역 (`_fake_gh_run`) — rc=2 would
    # indicate the dispatcher broke argv forwarding.
    from unittest import mock
    fake_run, calls = _fake_gh_run()
    with mock.patch("subprocess.run", fake_run):
        code = mod.run_workflow_kit_cli(["--command=consumer-metrics", "--json"])
    assert code == 0, f"expected 0, got {code}"
    assert calls, "consumer-metrics 가 gh 층에 닿지 않았다"
    # After dispatcher run, workflow_kit.tools.consumer_metrics must be in
    # sys.modules (proof that in-process import path was taken, not subprocess).
    # v1.2.0 (2nd cycle): 구경로 tools.* shim drop — 정위치 모듈명으로 판정.
    assert "workflow_kit.tools.consumer_metrics" in _sys.modules, (
        "workflow_kit.tools.consumer_metrics not in sys.modules — dispatcher may have used subprocess"
    )
    # Days validation single-source: consumer_metrics.main() returns 2 for out-of-range
    cm_mod = importlib.import_module("workflow_kit.tools.consumer_metrics")
    old_argv = _sys.argv
    try:
        _sys.argv = ["consumer_metrics", "--days=0", "--json"]
        assert cm_mod.main() == 2
        _sys.argv = ["consumer_metrics", "--days=100", "--json"]
        assert cm_mod.main() == 2
    finally:
        _sys.argv = old_argv


def test_consumer_metrics_argv_forwarded_v0_7_59() -> None:
    """consumer-metrics dispatcher forwards --repo / --days to consumer_metrics.main() (v0.7.59+).

    days=0 invalid → rc=2 (validation in main() argparse).
    days=100 invalid → rc=2 (validation in main() argparse).
    Confirms argv flows from dispatcher → consumer_metrics argparse without dispatcher-side
    double-parsing (v0.7.58 had dispatcher-side validation + main()-side validation).
    """
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(
        ["--command=consumer-metrics", "--days=0", "--repo=ykylee/standard_ai_workflow"]
    )
    assert code == 2
    code = mod.run_workflow_kit_cli(
        ["--command=consumer-metrics", "--days=100", "--repo=ykylee/standard_ai_workflow"]
    )
    assert code == 2


def test_cache_lfu_decay_persist_registered_v0_7_60() -> None:
    """cache-lfu-decay-persist is registered as dispatcher subcommand 28 (v0.7.60+)."""
    mod = _import_cli()
    assert "cache-lfu-decay-persist" in mod.COMMANDS
    assert callable(mod.COMMANDS["cache-lfu-decay-persist"])


def test_cache_lfu_decay_persist_missing_args_v0_7_60() -> None:
    """cache-lfu-decay-persist without --url or --score returns 2 (usage error)."""
    mod = _import_cli()
    # missing both
    code = mod.run_workflow_kit_cli(["--command=cache-lfu-decay-persist"])
    assert code == 2
    # missing score
    code = mod.run_workflow_kit_cli(["--command=cache-lfu-decay-persist", "--url=https://a.com/"])
    assert code == 2
    # invalid score (not a number)
    code = mod.run_workflow_kit_cli(
        ["--command=cache-lfu-decay-persist", "--url=https://a.com/", "--score=not-a-number"]
    )
    assert code == 2


def test_cache_lfu_decay_persist_dry_run_v0_7_60() -> None:
    """cache-lfu-decay-persist dry-run (default) simulates update without writing (v0.7.60+)."""
    import json
    import tempfile
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        scores_path = Path(tmp) / "scores.json"
        scores_path.write_text(json.dumps({"version": 1, "saved_at": 0, "scores": {"https://existing.com/": 0.5}}), encoding="utf-8")
        # Dry-run with new URL — file unchanged
        code = mod.run_workflow_kit_cli(
            [
                "--command=cache-lfu-decay-persist",
                "--url=https://new.com/",
                "--score=0.9",
                f"--scores-path={scores_path}",
                "--json",
            ]
        )
        assert code == 0
        # File should NOT contain the new URL (dry-run)
        # File should NOT contain the new URL (dry-run) — file format is wrapped {"scores": {...}}
        data = json.loads(scores_path.read_text(encoding="utf-8"))
        assert "https://new.com/" not in data.get("scores", {})
        assert "https://existing.com/" in data["scores"]


def test_cache_lfu_decay_persist_apply_v0_7_60() -> None:
    """cache-lfu-decay-persist --apply actually writes to disk (v0.7.60+)."""
    import json
    import tempfile
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        scores_path = Path(tmp) / "scores.json"
        code = mod.run_workflow_kit_cli(
            [
                "--command=cache-lfu-decay-persist",
                "--url=https://applied.com/",
                "--score=0.75",
                f"--scores-path={scores_path}",
                "--apply",
                "--json",
            ]
        )
        assert code == 0
        # File should contain the new URL
        # File format: {"version": 1, "saved_at": ..., "scores": {...}}
        data = json.loads(scores_path.read_text(encoding="utf-8"))
        assert data["scores"]["https://applied.com/"] == 0.75


def test_cache_lru_decay_registered_v0_8_9() -> None:
    """cache-lru-decay subcommand 29 is registered (v0.8.9+)."""
    mod = _import_cli()
    assert "cache-lru-decay" in mod.COMMANDS


def test_cache_lru_decay_missing_args_v0_8_9() -> None:
    """cache-lru-decay without --max-bytes returns 2 (v0.8.9+)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-lru-decay"])
    assert code == 2


def test_cache_lru_decay_dry_run_v0_8_9() -> None:
    """cache-lru-decay on missing cache file returns 0 with 0 evicted (v0.8.9+)."""
    import tempfile
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        code = mod.run_workflow_kit_cli(
            [
                "--command=cache-lru-decay",
                "--max-bytes=100",
                f"--cache-path={tmp}/nonexistent.json",
                "--json",
            ]
        )
        assert code == 0


def test_cache_merge_csv_registered_v0_8_9() -> None:
    """cache-merge-csv subcommand 30 is registered (v0.8.9+)."""
    mod = _import_cli()
    assert "cache-merge-csv" in mod.COMMANDS


def test_cache_merge_csv_no_csv_returns_2_v0_8_9() -> None:
    """cache-merge-csv without --csv returns 2 (v0.8.9+)."""
    mod = _import_cli()
    code = mod.run_workflow_kit_cli(["--command=cache-merge-csv"])
    assert code == 2


def test_cache_merge_csv_roundtrip_v0_8_9() -> None:
    """cache-merge-csv merges 2 CSV files into a single cache (v0.8.9+)."""
    import json
    import tempfile
    mod = _import_cli()
    with tempfile.TemporaryDirectory() as tmp:
        csv1 = Path(tmp) / "first.csv"
        csv2 = Path(tmp) / "second.csv"
        cache_path = Path(tmp) / "merged.json"
        csv1.write_text(
            "url,status,timestamp,access_count\n"
            "https://a.com/,200,1700000000,1\n"
            "https://b.com/,200,1700000001,2\n",
            encoding="utf-8",
        )
        csv2.write_text(
            "url,status,timestamp,access_count\n"
            "https://c.com/,200,1700000002,3\n"
            "https://b.com/,200,1700000003,5\n",
            encoding="utf-8",
        )
        code = mod.run_workflow_kit_cli(
            [
                "--command=cache-merge-csv",
                f"--csv={csv1}",
                f"--csv={csv2}",
                f"--cache-path={cache_path}",
                "--json",
            ]
        )
        assert code == 0
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        urls = set(data.keys())
        assert "https://a.com/" in urls
        assert "https://b.com/" in urls
        assert "https://c.com/" in urls


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
        test_score_wiki_trend_json_in_process_v0_7_56,
        test_score_wiki_trend_record_current_in_process_v0_7_56,
        test_okf_cleanup_dry_run_v0_7_56,
        test_okf_cleanup_apply_removes_v0_7_56,
        test_cache_prune_dry_run_v0_7_56,
        test_cache_prune_apply_removes_old_v0_7_56,
        test_release_bump_dry_run_v0_7_56,
        test_release_create_missing_version_returns_2_v0_7_56,
        test_release_rollback_missing_tag_returns_2_v0_7_56,
        test_release_dist_dry_run_v0_7_56,
        test_release_changelog_dry_run_v0_7_56,
        test_cache_decay_csv_inplace_v0_7_56,
        test_cache_decay_inplace_rejects_non_csv_v0_7_56,
        test_cache_import_csv_no_arg_returns_2_v0_7_57,
        test_cache_import_csv_roundtrip_v0_7_57,
        test_cache_export_json_no_output_returns_2_v0_7_57,
        test_cache_export_json_roundtrip_v0_7_57,
        test_cache_merge_multi_no_op_v0_7_57,
        test_consumer_metrics_registered_v0_7_58,
        test_consumer_metrics_invalid_days_returns_2_v0_7_58,
        test_consumer_metrics_default_argv_v0_7_58,
        test_consumer_metrics_in_process_v0_7_59,
        test_consumer_metrics_argv_forwarded_v0_7_59,
        test_cache_lfu_decay_persist_registered_v0_7_60,
        test_cache_lfu_decay_persist_missing_args_v0_7_60,
        test_cache_lfu_decay_persist_dry_run_v0_7_60,
        test_cache_lfu_decay_persist_apply_v0_7_60,
        test_cache_lru_decay_registered_v0_8_9,
        test_cache_lru_decay_missing_args_v0_8_9,
        test_cache_lru_decay_dry_run_v0_8_9,
        test_cache_merge_csv_registered_v0_8_9,
        test_cache_merge_csv_no_csv_returns_2_v0_8_9,
        test_cache_merge_csv_roundtrip_v0_8_9,
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
