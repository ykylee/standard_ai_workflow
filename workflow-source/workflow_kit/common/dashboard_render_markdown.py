"""workflow_kit.common.dashboard_render_markdown - Quality Dashboard markdown renderer.

`dashboard_data.py` 에서 verbatim 분리 (2026-08-11). snapshot dict → markdown 직렬화만
담당하는 pure renderer. `DRIFT_LEDGER_RELPATH` 정본은 `dashboard_data.py` 에 남아
있으므로 (drift 원장 경로 single-source), `_render_panel_1` 이 function-level import
로 참조한다 (top-level 순환 import 회피).
"""

from __future__ import annotations

from typing import Any

__all__: list[str] = [
    "render_dashboard_markdown",
    "_render_panel_1",
    "_render_panel_2",
    "_render_panel_3",
    "_render_panel_4",
    "_render_panel_5",
    "_render_panel_6",
    "_render_panel_7",
    "_render_panel_8",
]


# ---------------------------------------------------------------------------
# Renderer — Markdown output (v0.13.0 무료 옵션)
# ---------------------------------------------------------------------------


def render_dashboard_markdown(snapshot: dict[str, Any]) -> str:
    """snapshot dict 를 markdown 표 형식으로 직렬화.

    v0.13.1 release hook 의 preview / Phase 13 wiki 자동 emit 의 자유 옵션.
    """
    lines: list[str] = []
    lines.append("# Quality Dashboard Snapshot")
    lines.append("")
    lines.append(f"- generated_at: `{snapshot.get('generated_at', '')}`")
    lines.append(f"- tool_version: `{snapshot.get('tool_version', '')}`")
    lines.append(f"- workspace_root: `{snapshot.get('workspace_root', '')}`")
    lines.append("")
    panels = snapshot.get("panels", {})
    if isinstance(panels, dict):
        lines.extend(_render_panel_1(panels.get("drift_prevention", {})))
        lines.extend(_render_panel_2(panels.get("maturity_distribution", {})))
        lines.extend(_render_panel_3(panels.get("memory_index_utilization", {})))
        lines.extend(_render_panel_4(panels.get("smoke_trend", {})))
        lines.extend(_render_panel_5(panels.get("recent_releases", {})))
        # Phase 15 (v0.14.3+) — Panel 6/7/8 north-star metric
        lines.extend(_render_panel_6(panels.get("multi_agent_concurrent_write_conflict", {})))
        lines.extend(_render_panel_7(panels.get("deprecation_cycle_progress", {})))
        lines.extend(_render_panel_8(panels.get("memory_index_utilization_v2", {})))
    return "\n".join(lines) + "\n"


def _render_panel_1(p: dict[str, Any]) -> list[str]:
    # local import: `DRIFT_LEDGER_RELPATH` 정본은 dashboard_data.py (drift 원장
    # 경로 single-source). top-level 순환 import 회피를 위해 function-level 로 참조.
    from workflow_kit.common.dashboard_data import DRIFT_LEDGER_RELPATH
    lines: list[str] = ["## Panel 1 — Drift Prevention Status", ""]
    lines.append(f"- guard_status: `{p.get('guard_status', 'unknown')}`")
    lines.append(f"- guard_cases: `{p.get('guard_cases', 0)} / {p.get('expected_cases', 0)}`")
    lines.append(f"- maturity_last_updated: `{p.get('maturity_last_updated', '')}`")
    lines.append(f"- maturity_surface_changed_at: `{p.get('maturity_surface_changed_at', '')}`")
    lines.append(
        f"- maturity_stale: `{p.get('maturity_stale', False)}` "
        f"(source: `{p.get('maturity_staleness_source', 'unknown')}`)"
    )
    lines.append(f"- harness_supported_count: `{p.get('harness_supported_count', 0)}`")
    lines.append(f"- head_commit_date: `{p.get('head_commit_date', '')}`")
    delta = p.get("last_updated_delta_days")
    lines.append(f"- last_updated_delta_days: `{delta if delta is not None else 'unknown'}`")
    if p.get("silent_failing_cycles_measured"):
        lines.append(
            f"- silent_failing_cycles_count: `{p.get('silent_failing_cycles_count', 0)}` "
            f"(측정 cycle {p.get('silent_failing_cycles_measured_cycles', 0)}건)"
        )
    else:
        # 0 을 초록으로 오독하지 않도록 *미측정* 임을 값 자리에 그대로 쓴다.
        lines.append(
            "- silent_failing_cycles_count: `미측정` "
            f"(원장 `{p.get('silent_failing_cycles_source', DRIFT_LEDGER_RELPATH)}` 에 cycle 0건)"
        )
    if p.get("maturity_stale") and p.get("maturity_refresh_hint"):
        lines.append("")
        lines.append(
            "> ⚠️ **maturity 선언이 surface 보다 뒤처짐** "
            f"(surface `{p.get('maturity_surface_changed_at', '')}` > 선언 "
            f"`{p.get('maturity_last_updated', '')}`): "
            # hint 자체가 이미 완결된 `python3 -c "..."` 명령이다 — 접두사를 다시
            # 붙이면 `python3 -c "python3 -c "..."` 로 깨진 명령이 나간다.
            f"refresh hint → `{p.get('maturity_refresh_hint', '')}`"
        )
    return lines + [""]


def _render_panel_2(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 2 — Maturity Distribution", ""]
    for kind in ("skills", "mcp_tools", "milestones"):
        bucket = p.get(kind, {})
        if isinstance(bucket, dict):
            lines.append(f"### {kind}")
            lines.append("")
            lines.append("| metric | value |")
            lines.append("|---|---|")
            lines.append(f"| total | {bucket.get('total', 0)} |")
            if kind != "milestones":
                lines.append(f"| stable | {bucket.get('stable', 0)} |")
                lines.append(f"| beta | {bucket.get('beta', 0)} |")
                lines.append(f"| alpha | {bucket.get('alpha', 0)} |")
            else:
                lines.append(f"| done | {bucket.get('done', 0)} |")
                lines.append(f"| in_progress | {bucket.get('in_progress', 0)} |")
                lines.append(f"| planned | {bucket.get('planned', 0)} |")
            lines.append("")
    harnesses = p.get("harnesses", {})
    if isinstance(harnesses, dict):
        lines.append("### harnesses")
        lines.append("")
        lines.append(f"- supported: `{harnesses.get('supported', 0)}`")
        names = harnesses.get("supported_names", [])
        if isinstance(names, list) and names:
            lines.append(f"- names: {', '.join(f'`{n}`' for n in names)}")
        lines.append("")
    return lines


def _render_panel_3(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 3 — Memory Index Utilization", ""]
    lines.append(f"- entries_total: `{p.get('entries_total', 0)}`")
    by_state = p.get("entries_by_merge_state", {})
    if isinstance(by_state, dict):
        if by_state:
            state_str = ", ".join(f"`{k}`={v}" for k, v in by_state.items())
        else:
            state_str = "(none)"
        lines.append(f"- entries_by_merge_state: {state_str}")
    lines.append(f"- cue_anchors_unique: `{p.get('cue_anchors_unique', 0)}`")
    lines.append(f"- first_entry_date: `{p.get('first_entry_date', '')}`")
    lines.append(f"- last_entry_date: `{p.get('last_entry_date', '')}`")
    top = p.get("cue_anchors_top", [])
    if isinstance(top, list) and top:
        lines.append("")
        lines.append("### Top cue anchors")
        lines.append("")
        lines.append("| anchor | count |")
        lines.append("|---|---|")
        for entry in top[:10]:
            if isinstance(entry, dict):
                lines.append(
                    f"| {entry.get('anchor', '')} | {entry.get('count', 0)} |"
                )
    return lines + [""]


def _render_panel_4(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 4 — Smoke Trend", ""]
    lines.append(f"- cumulative_total: `{p.get('cumulative_total', 0)}`")
    lines.append(f"- cumulative_pass: `{p.get('cumulative_pass', 0)}`")
    rate = p.get("cumulative_pass_rate", 0.0)
    lines.append(f"- cumulative_pass_rate: `{rate:.4f}`")
    lines.append(f"- smoke_files_count: `{p.get('smoke_files_count', 0)}`")
    recent = p.get("recent_releases", [])
    if isinstance(recent, list) and recent:
        lines.append("")
        lines.append("### Recent release smoke counts")
        lines.append("")
        lines.append("| version | pass | total |")
        lines.append("|---|---|---|")
        for entry in recent:
            if isinstance(entry, dict):
                lines.append(
                    f"| {entry.get('version', '')} "
                    f"| {entry.get('pass', 0)} "
                    f"| {entry.get('total', 0)} |"
                )
    return lines + [""]


def _render_panel_5(p: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Panel 5 — Recent Release Cycle", ""]
    lines.append(f"- items_total: `{p.get('items_total', 0)}`")
    lines.append(f"- top_n: `{p.get('top_n', 0)}`")
    # v0.15.22+ (TASK-2026-08-08-main-014, §0.8 #2) — 4-level confidence 분포.
    counts = p.get("confidence_counts", {})
    if isinstance(counts, dict) and counts:
        lines.append(
            "- confidence: "
            + " · ".join(
                f"`{k}={v}`" for k, v in counts.items() if v
            )
        )
    timeline = p.get("timeline", [])
    if isinstance(timeline, list) and timeline:
        lines.append("")
        lines.append("### Timeline (preview, first 120 char)")
        lines.append("")
        for entry in timeline:
            if isinstance(entry, dict):
                idx = entry.get("index", 0)
                preview = entry.get("preview", "")
                # inline badge: 4-level enum (fresh / recent / stale / orphan)
                conf = entry.get("confidence", "fresh")
                badge = f"  `[{conf}]`" if conf else ""
                lines.append(f"- [{idx}] {preview}{badge}")
    return lines + [""]


def _render_panel_6(p: dict[str, Any]) -> list[str]:
    """Panel 6 — Multi-Agent Concurrent Write Conflict (Phase 15 north-star)."""
    lines: list[str] = ["## Panel 6 — Multi-Agent Concurrent Write Conflict", ""]
    lines.append(f"- north_star: `{p.get('north_star', 'unknown')}`")
    if p.get("conflict_count_measured"):
        lines.append(
            f"- conflict_count: `{p.get('conflict_count', 0)}` "
            f"(source: `{p.get('conflict_count_source', 'unknown')}`)"
        )
    else:
        # 측정원이 하나도 안 돌았으면 0 을 초록으로 보여주지 않는다.
        lines.append("- conflict_count: `미측정` (측정원 없음 — working_tree / git_log 모두 불가)")
    lines.append(f"- threshold: `{p.get('threshold', 0)}`")
    lines.append(f"- status: `{p.get('status', 'unknown')}`")
    locations = p.get("conflict_locations", [])
    if locations:
        lines.append("")
        lines.append("### Conflict locations")
        lines.append("")
        for loc in locations[:10]:  # max 10 표시
            lines.append(f"- `{loc}`")
    return lines + [""]


def _render_panel_7(p: dict[str, Any]) -> list[str]:
    """Panel 7 — Deprecation Cycle Progress."""
    lines: list[str] = ["## Panel 7 — Deprecation Cycle Progress", ""]
    lines.append(f"- stage: `{p.get('stage', 'unknown')}`")
    lines.append(f"- bak_present: `{p.get('bak_present', False)}`")
    lines.append(f"- legacy_present: `{p.get('legacy_present', False)}`")
    lines.append(f"- deprecation_warning_supported: `{p.get('deprecation_warning_supported', False)}`")
    lines.append(f"- next_release: `{p.get('next_release', 'unknown')}`")
    timeline = p.get("timeline", {})
    if isinstance(timeline, dict) and timeline:
        lines.append("")
        lines.append("### Timeline")
        lines.append("")
        lines.append("| Version | Stage |")
        lines.append("|---|---|")
        for ver, desc in timeline.items():
            # current stage marker
            marker = " ← **current**" if ver == p.get("stage") else ""
            lines.append(f"| `{ver}` | {desc}{marker} |")
    return lines + [""]


def _render_panel_8(p: dict[str, Any]) -> list[str]:
    """Panel 8 — Memory Index + Telemetry Utilization v2."""
    lines: list[str] = ["## Panel 8 — Memory Index + Telemetry Utilization v2", ""]
    lines.append(f"- phase_15_north_star: `{p.get('phase_15_north_star', '')}`")
    lines.append(f"- entries_total: `{p.get('entries_total', 0)}`")
    lines.append(f"- telemetry_events_total: `{p.get('telemetry_events_total', 0)}`")
    lines.append(f"- telemetry_total_queries: `{p.get('telemetry_total_queries', 0)}`")
    lines.append(f"- telemetry_hit_count: `{p.get('telemetry_hit_count', 0)}`")
    lines.append(f"- telemetry_hit_rate: `{p.get('telemetry_hit_rate', 0.0):.4f}`")
    by_ms = p.get("entries_by_merge_state", {})
    if isinstance(by_ms, dict) and by_ms:
        lines.append("")
        lines.append("### Entries by merge_state")
        lines.append("")
        lines.append("| merge_state | count |")
        lines.append("|---|---|")
        for state, count in sorted(by_ms.items()):
            lines.append(f"| `{state}` | {count} |")
    by_src = p.get("telemetry_by_source", {})
    if isinstance(by_src, dict) and by_src:
        lines.append("")
        lines.append("### Telemetry by source")
        lines.append("")
        lines.append("| source | events |")
        lines.append("|---|---|")
        for src, count in sorted(by_src.items()):
            lines.append(f"| `{src}` | {count} |")
    return lines + [""]
