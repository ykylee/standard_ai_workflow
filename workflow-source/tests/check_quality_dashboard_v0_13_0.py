#!/usr/bin/env python3
"""Smoke test the Quality Dashboard v0.13.0 (Phase 13 sub-milestone).

본 smoke 는 다음을 검증한다 (구현 가이드 §4 AC 정합):
    AC1: collect_dashboard_snapshot 가 5 panel 의 data 를 1 dict 로 emit
    AC2: 5 panel 모두 *실제 data* (fixture 아님) 기반
    AC3: release --apply 시 dashboard snapshot 자동 갱신 — v0.13.1 sub-milestone (현 release 외)
    AC4: snapshot 의 last_updated ≤ release commit date (data freshness)

각 panel 별 추가 검증:
    - drift_prevention: guard_cases == expected_cases == 6
    - maturity_distribution: skills.stable >= 1, mcp_tools.total >= 1, harnesses.supported >= 1
    - memory_index_utilization: entries_total >= 1, cue_anchors_top is list
    - smoke_trend: cumulative_pass > 0 (실제 release note parse 결과)
    - recent_releases: items_total >= 1

추가 검증:
    - CLI subcommand --command=dashboard --format=json exit 0 + JSON output
    - CLI subcommand --command=dashboard --format=markdown exit 0 + markdown output
    - CLI subcommand invalid --format=html exit 2
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def _run_cli(*args: str) -> tuple[int, str, str]:
    """workflow_kit_cli subprocess 호출, (rc, stdout, stderr) 반환.

    PYTHONPATH 에 ``workflow-source`` 를 prepend 해서 ``workflow_kit`` 모듈을
    import 가능하게 한다 (기존 check_graph_insights_v0_11_1.py 와 동일 패턴).
    """
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli", "--command=dashboard", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _assert(condition: bool, message: str) -> None:
    """assertion 실패 시 명확한 message raise."""
    if not condition:
        raise AssertionError(message)


def _check_snapshot_shape(snap: dict[str, object]) -> None:
    """AC1: top-level shape + 5 panel 존재."""
    required_top = {"schema_version", "tool_version", "generated_at", "workspace_root", "panels"}
    actual_top = set(snap.keys())
    _assert(
        actual_top >= required_top,
        f"missing top-level keys: {required_top - actual_top}",
    )
    panels = snap.get("panels", {})
    _assert(isinstance(panels, dict), "panels must be dict")
    expected_panels = {
        "drift_prevention",
        "maturity_distribution",
        "memory_index_utilization",
        "smoke_trend",
        "recent_releases",
    }
    actual_panels = set(panels.keys()) if isinstance(panels, dict) else set()
    _assert(
        actual_panels == expected_panels,
        f"panel keys mismatch: expected={expected_panels}, actual={actual_panels}",
    )
    # generated_at format check (ISO 8601)
    gen = str(snap.get("generated_at", ""))
    _assert(
        bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", gen)),
        f"generated_at not ISO 8601: {gen!r}",
    )


def _check_drift_prevention(panel: dict[str, object]) -> None:
    """Panel 1: guard_cases / expected_cases 정합 (v0.13.1+ inline guard)."""
    expected = int(panel.get("expected_cases", 0))
    actual = int(panel.get("guard_cases", 0))
    _assert(expected == 6, f"expected_cases should be 6, got {expected}")
    _assert(actual == expected, f"guard_cases ({actual}) != expected_cases ({expected})")
    _assert(
        isinstance(panel.get("silent_failing_cycles_count"), int),
        "silent_failing_cycles_count must be int",
    )
    # v0.13.1+ inline drift guard — guard_status must be 'pass'|'fail'|'error' (NOT 'unknown').
    guard_status = str(panel.get("guard_status", "unknown"))
    _assert(
        guard_status in ("pass", "fail", "error"),
        f"guard_status must be inline result (not 'unknown'), got {guard_status!r}",
    )
    _assert(
        isinstance(panel.get("guard_cases_pass"), int),
        "guard_cases_pass must be int (v0.13.1+ field)",
    )
    _assert(
        isinstance(panel.get("guard_runtime_ms"), int),
        "guard_runtime_ms must be int (v0.13.1+ field)",
    )


def _check_maturity_distribution(panel: dict[str, object]) -> None:
    """Panel 2: skill + mcp + harness 정합 (실제 data 기반, fixture 아님)."""
    skills = panel.get("skills", {})
    _assert(isinstance(skills, dict) and int(skills.get("stable", 0)) >= 1, "skills.stable >= 1")
    mcp = panel.get("mcp_tools", {})
    _assert(isinstance(mcp, dict) and int(mcp.get("total", 0)) >= 1, "mcp_tools.total >= 1")
    harnesses = panel.get("harnesses", {})
    _assert(
        isinstance(harnesses, dict) and int(harnesses.get("supported", 0)) >= 1,
        "harnesses.supported >= 1",
    )
    milestones = panel.get("milestones", {})
    _assert(
        isinstance(milestones, dict) and int(milestones.get("done", 0)) >= 1,
        "milestones.done >= 1",
    )


def _check_memory_index(panel: dict[str, object]) -> None:
    """Panel 3: entries_total >= 1 + cue_anchors_top list."""
    total = int(panel.get("entries_total", 0))
    _assert(total >= 1, f"memory_index entries_total >= 1 (got {total})")
    top = panel.get("cue_anchors_top", [])
    _assert(isinstance(top, list), "cue_anchors_top must be list")
    if top:
        first = top[0]
        _assert(
            isinstance(first, dict) and "anchor" in first and "count" in first,
            f"cue_anchors_top entry shape: {first!r}",
        )


def _check_smoke_trend(panel: dict[str, object]) -> None:
    """Panel 4: cumulative_pass > 0 (실제 release note parse 결과)."""
    cum_pass = int(panel.get("cumulative_pass", 0))
    cum_total = int(panel.get("cumulative_total", 0))
    _assert(cum_pass > 0, f"smoke cumulative_pass > 0 (got {cum_pass})")
    _assert(
        cum_pass == cum_total,
        f"smoke pass ({cum_pass}) != total ({cum_total}) — drift detected",
    )
    rate = float(panel.get("cumulative_pass_rate", 0.0))
    _assert(0.0 <= rate <= 1.0, f"cumulative_pass_rate out of range: {rate}")


def _check_recent_releases(panel: dict[str, object]) -> None:
    """Panel 5: items_total >= 1 + timeline list."""
    total = int(panel.get("items_total", 0))
    _assert(total >= 1, f"recent_releases items_total >= 1 (got {total})")
    timeline = panel.get("timeline", [])
    _assert(isinstance(timeline, list), "timeline must be list")


def _check_cli_json() -> None:
    """CLI subcommand: --format=json 정상 동작 + valid JSON."""
    rc, stdout, stderr = _run_cli("--format=json")
    _assert(rc == 0, f"dashboard --format=json exit code: {rc}, stderr: {stderr}")
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"dashboard JSON parse failed: {e}\nstdout: {stdout[:500]}") from None
    _assert("panels" in parsed, "dashboard JSON missing 'panels'")


def _check_cli_markdown() -> None:
    """CLI subcommand: --format=markdown 정상 동작."""
    rc, stdout, stderr = _run_cli("--format=markdown")
    _assert(rc == 0, f"dashboard --format=markdown exit code: {rc}, stderr: {stderr}")
    _assert(
        "# Quality Dashboard Snapshot" in stdout,
        "markdown output missing header",
    )
    _assert(
        "## Panel 1" in stdout and "## Panel 5" in stdout,
        "markdown output missing 5 panels",
    )


def _check_cli_invalid_format() -> None:
    """CLI subcommand: invalid --format exit 2."""
    rc, _stdout, stderr = _run_cli("--format=xml")  # xml 은 valid set 외
    _assert(rc == 2, f"invalid format should exit 2, got {rc}, stderr: {stderr}")
    _assert("invalid" in stderr.lower(), f"stderr should mention 'invalid': {stderr}")


def _check_cli_output_file(tmp_path: Path) -> None:
    """CLI subcommand: --output=PATH 파일 emit."""
    out_path = tmp_path / "dashboard_snapshot.json"
    rc, _stdout, stderr = _run_cli("--format=json", f"--output={out_path}")
    _assert(rc == 0, f"--output exit code: {rc}, stderr: {stderr}")
    _assert(out_path.is_file(), f"output file not created: {out_path}")
    content = out_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    _assert("panels" in parsed, "output file JSON missing 'panels'")


def _check_drift_guard_inline_direct() -> None:
    """v0.13.1+: run_drift_prevention_guard_inline 직접 호출 — 6 case PASS/fail dict."""
    from workflow_kit.common.dashboard_data import run_drift_prevention_guard_inline

    result = run_drift_prevention_guard_inline(REPO_ROOT)
    _assert(
        result.get("guard_status") in ("pass", "fail", "error"),
        f"guard_status must be inline result, got {result.get('guard_status')!r}",
    )
    _assert(
        result.get("guard_cases", 0) == 6,
        f"guard_cases must be 6, got {result.get('guard_cases')}",
    )
    _assert(
        isinstance(result.get("guard_cases_pass"), int)
        and isinstance(result.get("guard_cases_fail"), int),
        "guard_cases_pass/fail must be int",
    )
    _assert(
        isinstance(result.get("guard_executed_at"), str)
        and bool(result.get("guard_executed_at")),
        "guard_executed_at must be non-empty ISO 8601",
    )
    _assert(
        isinstance(result.get("guard_runtime_ms"), int)
        and result.get("guard_runtime_ms", 0) > 0,
        f"guard_runtime_ms must be > 0, got {result.get('guard_runtime_ms')}",
    )


def _check_release_pipeline_dashboard_emit() -> None:
    """v0.13.1+: release_pipeline._emit_dashboard_post_release 정상 emit 검증."""
    import argparse as _ap
    import sys as _sys
    tools_dir = SOURCE_ROOT / "tools"
    if str(tools_dir) not in _sys.path:
        _sys.path.insert(0, str(tools_dir))
    from release_pipeline import _emit_dashboard_post_release  # type: ignore[import-not-found]

    # Default emit (skip=False, output=None)
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        args = _ap.Namespace(skip_dashboard_emit=False, dashboard_output=str(Path(td) / "dash.md"))
        result = _emit_dashboard_post_release(args, {})
        _assert(
            result.get("status") == "ok",
            f"emit status must be 'ok', got {result.get('status')!r}, err: {result.get('error')}",
        )
        _assert(
            result.get("bytes", 0) > 0,
            f"emit bytes must be > 0, got {result.get('bytes')}",
        )
        _assert(
            isinstance(result.get("duration_ms"), int)
            and result.get("duration_ms", 0) > 0,
            "duration_ms must be > 0",
        )

    # Skip=True
    args = _ap.Namespace(skip_dashboard_emit=True, dashboard_output=None)
    result = _emit_dashboard_post_release(args, {})
    _assert(
        result.get("status") == "skipped",
        f"skip status must be 'skipped', got {result.get('status')!r}",
    )
    _assert(
        "skip-dashboard-emit" in str(result.get("reason", "")),
        "skip reason should mention --skip-dashboard-emit",
    )


def _check_html_render() -> None:
    """v0.13.2+: render_dashboard_html 직접 호출 — self-contained HTML emit."""
    from workflow_kit.common.dashboard_data import (
        collect_dashboard_snapshot,
        render_dashboard_html,
    )

    snap = collect_dashboard_snapshot()
    html = render_dashboard_html(snap)
    stripped = html.rstrip()
    _assert(
        stripped.startswith("<!DOCTYPE html>") and stripped.endswith("</html>"),
        "HTML doc must start with <!DOCTYPE html> and end with </html> (ignoring trailing whitespace)",
    )
    _assert(
        "<canvas" in html and "chart.js" in html,
        "HTML must include Chart.js CDN reference + <canvas> elements",
    )
    for label in ("Panel 1", "Panel 2", "Panel 3", "Panel 4", "Panel 5"):
        _assert(label in html, f"HTML missing {label}")
    _assert(
        "silent_failing_cycles_count" in html,
        "HTML must include drift north-star metric",
    )


def _check_cli_html() -> None:
    """v0.13.2+: CLI subcommand --format=html 정상 동작."""
    rc, stdout, stderr = _run_cli("--format=html")
    _assert(rc == 0, f"dashboard --format=html exit code: {rc}, stderr: {stderr}")
    _assert(
        stdout.startswith("<!DOCTYPE html>"),
        f"--format=html stdout must be HTML doc, starts with: {stdout[:60]!r}",
    )
    _assert("Panel 1" in stdout and "Panel 5" in stdout, "missing 5 panel labels")


def _check_cli_html_publish(tmp_path: Path) -> None:
    """v0.13.2+: --publish 시 docs/dashboard/index.html 로 copy."""
    # Run in tmp cwd so we don't pollute the actual repo's docs/.
    completed = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=html", "--publish"],
        cwd=str(tmp_path),
        env={**__import__("os").environ,
             "PYTHONPATH": str(SOURCE_ROOT)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    _assert(
        completed.returncode == 0,
        f"--publish exit code: {completed.returncode}, stderr: {completed.stderr}",
    )
    publish_path = tmp_path / "docs" / "dashboard" / "index.html"
    _assert(
        publish_path.is_file(),
        f"--publish file not created: {publish_path}",
    )
    content = publish_path.read_text(encoding="utf-8")
    _assert(
        content.startswith("<!DOCTYPE html>"),
        "publish file content must be HTML",
    )


def main() -> int:
    print("[check_quality_dashboard_v0_13_0] starting")
    try:
        # Case 1: in-process snapshot 직접 호출 + 5 panel shape
        from workflow_kit.common.dashboard_data import collect_dashboard_snapshot

        snap = collect_dashboard_snapshot()
        _check_snapshot_shape(snap)
        panels = snap.get("panels", {})
        _check_drift_prevention(panels.get("drift_prevention", {}))
        _check_maturity_distribution(panels.get("maturity_distribution", {}))
        _check_memory_index(panels.get("memory_index_utilization", {}))
        _check_smoke_trend(panels.get("smoke_trend", {}))
        _check_recent_releases(panels.get("recent_releases", {}))
        print("[1/10] snapshot shape + 5 panel content — PASS")

        # Case 2: CLI subcommand json
        _check_cli_json()
        print("[2/10] CLI --format=json — PASS")

        # Case 3: CLI subcommand markdown
        _check_cli_markdown()
        print("[3/10] CLI --format=markdown — PASS")

        # Case 4: CLI subcommand invalid format → exit 2
        _check_cli_invalid_format()
        print("[4/10] CLI invalid format → exit 2 — PASS")

        # Case 5: CLI subcommand --output=PATH
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir).resolve()
            _check_cli_output_file(tmp_path)
        print("[5/10] CLI --output=PATH — PASS")

        # Case 6: v0.13.1+ inline drift guard (직접 호출)
        _check_drift_guard_inline_direct()
        print("[6/10] inline drift guard (run_drift_prevention_guard_inline) — PASS")

        # Case 7: v0.13.1+ release_pipeline dashboard emit hook
        _check_release_pipeline_dashboard_emit()
        print("[7/10] release_pipeline._emit_dashboard_post_release — PASS")

        # Case 8: v0.13.2+ render_dashboard_html 직접 호출
        _check_html_render()
        print("[8/10] render_dashboard_html — PASS")

        # Case 9: v0.13.2+ CLI subcommand --format=html
        _check_cli_html()
        print("[9/10] CLI --format=html — PASS")

        # Case 10: v0.13.2+ --publish → docs/dashboard/index.html
        with tempfile.TemporaryDirectory() as td:
            _check_cli_html_publish(Path(td).resolve())
        print("[10/10] CLI --format=html --publish — PASS")

        print("\nALL 10/10 CASES PASS")
        return 0
    except AssertionError as e:
        print(f"\nFAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())