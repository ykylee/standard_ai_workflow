"""workflow_kit.common.dashboard_render_html - Quality Dashboard HTML renderer.

`dashboard_data.py` 에서 verbatim 분리 (2026-08-11). snapshot dict → self-contained
HTML page 직렬화만 담당하는 pure renderer (Chart.js CDN + 8 panel widget).
외부 의존 없음 — `typing` 만 사용한다 (`json` 은 `_render_html_charts_js` 내부의
local import).
"""

from __future__ import annotations

from typing import Any, Final

__all__: list[str] = [
    "CHARTJS_CDN_URL",
    "render_dashboard_html",
    "_html_escape",
    "_HTML_CSS",
    "_render_html_panel_1",
    "_render_html_panel_2",
    "_render_html_panel_3",
    "_render_html_panel_4",
    "_render_html_panel_5",
    "_render_html_panel_6",
    "_render_html_panel_7",
    "_render_html_panel_8",
    "_render_html_charts_js",
]


# ---------------------------------------------------------------------------
# Renderer — HTML output (v0.13.2+)
# ---------------------------------------------------------------------------


# Chart.js CDN URL. Released under MIT license.
# https://www.chartjs.org/docs/latest/getting-started/installation.html
CHARTJS_CDN_URL: Final[str] = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def render_dashboard_html(snapshot: dict[str, Any]) -> str:
    """snapshot dict 를 단일 self-contained HTML page 로 직렬화 (v0.13.2+).

    Chart.js CDN + 5 panel widget (gauge / doughnut / line / bar / timeline list).
    prefers-color-scheme 의 dark mode 자동 인식. JavaScript off 시에도 static
    fallback 이 보임.

    Args:
        snapshot: collect_dashboard_snapshot() 의 결과 dict

    Returns:
        str — single HTML doc
    """
    panels = snapshot.get("panels", {})
    if not isinstance(panels, dict):
        panels = {}
    generated_at = str(snapshot.get("generated_at", ""))
    tool_version = str(snapshot.get("tool_version", ""))
    workspace_root = str(snapshot.get("workspace_root", ""))

    html = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>Quality Dashboard · {tool_version}</title>",
        "  <style>",
        _HTML_CSS,
        "  </style>",
        "</head>",
        "<body>",
        "  <header>",
        f"    <h1>Quality Dashboard</h1>",
        f'    <p class="meta">generated_at: <code>{_html_escape(generated_at)}</code> · '
        f'tool_version: <code>{_html_escape(tool_version)}</code></p>',
        f'    <p class="meta">workspace: <code>{_html_escape(workspace_root)}</code></p>',
        "  </header>",
        "  <main>",
    ]
    html.append(_render_html_panel_1(panels.get("drift_prevention", {})))
    html.append(_render_html_panel_2(panels.get("maturity_distribution", {})))
    html.append(_render_html_panel_3(panels.get("memory_index_utilization", {})))
    html.append(_render_html_panel_4(panels.get("smoke_trend", {})))
    html.append(_render_html_panel_5(panels.get("recent_releases", {})))
    # Phase 15 (v0.14.7+) — Panel 6/7/8 HTML render
    html.append(_render_html_panel_6(panels.get("multi_agent_concurrent_write_conflict", {})))
    html.append(_render_html_panel_7(panels.get("deprecation_cycle_progress", {})))
    html.append(_render_html_panel_8(panels.get("memory_index_utilization_v2", {})))
    html.append("  </main>")

    # Charts (Chart.js) — graceful when JS off (canvas + static text fallback)
    html.append("  <script>")
    html.append(_render_html_charts_js(panels))
    html.append("  </script>")
    html.append(f'  <script src="{_html_escape(CHARTJS_CDN_URL)}"></script>')

    html.append("</body>")
    html.append("</html>")
    return "\n".join(html) + "\n"


# ---------------------------------------------------------------------------
# HTML helpers (private)
# ---------------------------------------------------------------------------


def _html_escape(text: str) -> str:
    """HTML escape — `<`, `>`, `&`, `"`, `'` 만 처리."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


_HTML_CSS: Final[str] = """
:root {
  color-scheme: light dark;
  --bg: #fff;
  --fg: #1a1a1a;
  --muted: #666;
  --border: #ddd;
  --panel: #f9f9f9;
  --pass: #1b8a3a;
  --fail: #c0392b;
  --error: #d68910;
  --link: #1d6fb8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a1a; --fg: #e0e0e0; --muted: #aaa;
    --border: #333; --panel: #252525;
    --pass: #58c47e; --fail: #ff6b5b; --error: #ffd066;
    --link: #5aa7e8;
  }
}
body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0; padding: 2rem; }
h1 { font-size: 1.8rem; margin-bottom: 0.3rem; }
.meta { color: var(--muted); font-size: 0.85rem; }
code { background: var(--panel); padding: 0.1em 0.3em; border-radius: 3px; font-size: 0.9em; }
main { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-top: 2rem; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 1.2rem; }
.panel h2 { font-size: 1.1rem; margin: 0 0 0.8rem; }
.panel .stat { font-size: 1.6rem; font-weight: 600; }
.panel .stat.pass { color: var(--pass); }
.panel .stat.fail { color: var(--fail); }
.panel .stat.error { color: var(--error); }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.35rem 0.5rem; text-align: left; border-bottom: 1px solid var(--border); }
canvas { max-width: 100%; }
.timeline li { margin-bottom: 0.4rem; font-size: 0.85rem; color: var(--muted); }
ul.timeline { padding-left: 1.2rem; }
/* v0.15.22+ (TASK-2026-08-08-main-014, §0.8 #2) — in-flight 신뢰도 4-level badge */
.confidence { display: inline-block; padding: 0.1em 0.45em; border-radius: 3px; font-size: 0.75rem; font-weight: 600; margin-left: 0.3em; }
.confidence-fresh { background: rgba(27, 138, 58, 0.15); color: var(--pass); }
.confidence-recent { background: rgba(214, 137, 16, 0.15); color: var(--error); }
.confidence-stale { background: rgba(192, 57, 43, 0.15); color: var(--fail); }
.confidence-orphan { background: rgba(102, 102, 102, 0.2); color: var(--muted); text-decoration: line-through; }
""".strip()


def _render_html_panel_1(p: dict[str, Any]) -> str:
    """Panel 1 HTML — drift guard status."""
    status = str(p.get("guard_status", "unknown"))
    guard_cases_pass = int(p.get("guard_cases_pass", 0))
    guard_cases = int(p.get("guard_cases", 0))
    expected = int(p.get("expected_cases", 0))
    runtime_ms = int(p.get("guard_runtime_ms", 0))
    maturity_last_updated = str(p.get("maturity_last_updated", ""))
    head_commit_date = str(p.get("head_commit_date", ""))
    delta = p.get("last_updated_delta_days")
    harness_supported_count = int(p.get("harness_supported_count", 0))
    silent_failing = int(p.get("silent_failing_cycles_count", 0))
    silent_failing_measured = bool(p.get("silent_failing_cycles_measured", False))
    silent_failing_cycles = int(p.get("silent_failing_cycles_measured_cycles", 0))
    silent_failing_text = (
        f"{silent_failing} (측정 cycle {silent_failing_cycles}건)"
        if silent_failing_measured
        else "미측정 (원장 cycle 0건)"
    )
    surface_changed_at = str(p.get("maturity_surface_changed_at", ""))
    staleness_source = str(p.get("maturity_staleness_source", "unknown"))
    phase = str(p.get("phase", ""))

    status_class = status if status in ("pass", "fail", "error") else "unknown"
    return f"""  <section class="panel">
    <h2>Panel 1 — Drift Prevention Status</h2>
    <p>guard_status: <span class="stat {status_class}">{_html_escape(status)}</span></p>
    <p>guard: {guard_cases_pass}/{guard_cases} pass (expected {expected})</p>
    <p>guard_runtime_ms: {runtime_ms}</p>
    <p>maturity_last_updated: <code>{_html_escape(maturity_last_updated)}</code></p>
    <p>maturity_surface_changed_at: <code>{_html_escape(surface_changed_at)}</code> (source: {_html_escape(staleness_source)})</p>
    <p>head_commit_date: <code>{_html_escape(head_commit_date)}</code></p>
    <p>last_updated_delta_days: {delta if delta is not None else 'unknown'}</p>
    <p>harness_supported_count: {harness_supported_count}</p>
    <p><strong>silent_failing_cycles_count: {_html_escape(silent_failing_text)}</strong> (Phase 13 AC1 north-star)</p>
    <p class="meta">{_html_escape(phase)}</p>
  </section>"""


def _render_html_panel_2(p: dict[str, Any]) -> str:
    """Panel 2 HTML — maturity distribution + chart canvas."""
    skills = p.get("skills", {}) if isinstance(p.get("skills"), dict) else {}
    mcp = p.get("mcp_tools", {}) if isinstance(p.get("mcp_tools"), dict) else {}
    harnesses = p.get("harnesses", {}) if isinstance(p.get("harnesses"), dict) else {}
    milestones = p.get("milestones", {}) if isinstance(p.get("milestones"), dict) else {}
    return f"""  <section class="panel">
    <h2>Panel 2 — Maturity Distribution</h2>
    <table>
      <thead><tr><th>bucket</th><th>total</th><th>stable</th><th>beta</th><th>alpha</th></tr></thead>
      <tbody>
        <tr><td>skills</td><td>{int(skills.get('total', 0))}</td><td>{int(skills.get('stable', 0))}</td><td>{int(skills.get('beta', 0))}</td><td>{int(skills.get('alpha', 0))}</td></tr>
        <tr><td>mcp_tools</td><td>{int(mcp.get('total', 0))}</td><td>{int(mcp.get('stable', 0))}</td><td>{int(mcp.get('beta', 0))}</td><td>{int(mcp.get('alpha', 0))}</td></tr>
      </tbody>
    </table>
    <p>harnesses.supported: <strong>{int(harnesses.get('supported', 0))}</strong></p>
    <p>milestones: total={int(milestones.get('total', 0))} done={int(milestones.get('done', 0))} in_progress={int(milestones.get('in_progress', 0))}</p>
    <canvas id="chart-maturity" height="160"></canvas>
  </section>"""


def _render_html_panel_3(p: dict[str, Any]) -> str:
    """Panel 3 HTML — memory index utilization + chart canvas.

    v0.13.1+ Phase 13 AC2 telemetry 정합: retrieval_hit_rate 가 telemetry events.jsonl
    집계값으로 emit. by_source 분해 + events_parsed/skipped 도 표시.
    """
    entries_total = int(p.get("entries_total", 0))
    cue_unique = int(p.get("cue_anchors_unique", 0))
    first_date = str(p.get("first_entry_date", ""))
    last_date = str(p.get("last_entry_date", ""))
    hit_rate = float(p.get("retrieval_hit_rate", 0.0))
    by_state = p.get("entries_by_merge_state", {})
    state_str = ", ".join(
        f"{_html_escape(str(k))}={int(v)}" for k, v in (by_state.items() if isinstance(by_state, dict) else [])
    )
    telemetry = p.get("telemetry", {})
    if not isinstance(telemetry, dict):
        telemetry = {}
    t_total_calls = int(telemetry.get("total_calls", 0))
    t_total_hits = int(telemetry.get("total_hits", 0))
    t_by_source = telemetry.get("by_source", {})
    t_source_str = ", ".join(
        f"{_html_escape(str(k))}:calls={int(v.get('calls', 0))},hits={int(v.get('hits', 0))}"
        for k, v in (sorted(t_by_source.items()) if isinstance(t_by_source, dict) else [])
    )
    return f"""  <section class="panel">
    <h2>Panel 3 — Memory Index Utilization</h2>
    <p class="stat">{entries_total}</p>
    <p class="meta">total entries · unique cue anchors: {cue_unique}</p>
    <p class="meta">first_entry_date: <code>{_html_escape(first_date)}</code></p>
    <p class="meta">last_entry_date: <code>{_html_escape(last_date)}</code></p>
    <p class="meta">retrieval_hit_rate: <strong>{hit_rate:.4f}</strong> (Phase 13 AC2 telemetry)</p>
    <p class="meta">telemetry calls/hits: {t_total_calls}/{t_total_hits} · by_source: {t_source_str or '(none)'}</p>
    <p class="meta">by merge_state: {state_str or '(none)'}</p>
    <canvas id="chart-memory" height="160"></canvas>
  </section>"""


def _render_html_panel_4(p: dict[str, Any]) -> str:
    """Panel 4 HTML — smoke trend + chart canvas."""
    cum_total = int(p.get("cumulative_total", 0))
    cum_pass = int(p.get("cumulative_pass", 0))
    cum_rate = float(p.get("cumulative_pass_rate", 0.0))
    smoke_files = int(p.get("smoke_files_count", 0))
    return f"""  <section class="panel">
    <h2>Panel 4 — Smoke Trend</h2>
    <p class="stat pass">{cum_pass}/{cum_total}</p>
    <p class="meta">cumulative pass rate: {cum_rate:.4f}</p>
    <p class="meta">smoke test files: {smoke_files}</p>
    <canvas id="chart-smoke" height="160"></canvas>
  </section>"""


def _render_html_panel_5(p: dict[str, Any]) -> str:
    """Panel 5 HTML — recent releases timeline."""
    items_total = int(p.get("items_total", 0))
    top_n = int(p.get("top_n", 0))
    timeline = p.get("timeline", [])
    # v0.15.22+ (TASK-2026-08-08-main-014, §0.8 #2) — confidence 분포 + inline badge
    counts = p.get("confidence_counts", {})
    counts_html = ""
    if isinstance(counts, dict) and counts:
        badges: list[str] = []
        for level, n in counts.items():
            if n <= 0:
                continue
            badges.append(
                f'<span class="confidence confidence-{_html_escape(str(level))}">'
                f'{_html_escape(str(level))}={n}</span>'
            )
        if badges:
            counts_html = (
                '<p class="meta">confidence: ' + " ".join(badges) + "</p>"
            )
    items: list[str] = []
    if isinstance(timeline, list):
        for entry in timeline:
            if isinstance(entry, dict):
                idx = entry.get("index", 0)
                preview = entry.get("preview", "")
                conf = str(entry.get("confidence", "fresh") or "fresh")
                badge_html = (
                    f' <span class="confidence confidence-{_html_escape(conf)}">'
                    f'[{_html_escape(conf)}]</span>'
                )
                items.append(
                    f"      <li>[{idx}] {_html_escape(str(preview))}{badge_html}</li>"
                )
    timeline_html = "\n".join(items) if items else "      <li>(no items)</li>"
    return f"""  <section class="panel">
    <h2>Panel 5 — Recent Release Cycle</h2>
    <p>items_total: <strong>{items_total}</strong> (top_n={top_n})</p>
    {counts_html}
    <ul class="timeline">
{timeline_html}
    </ul>
  </section>"""


def _render_html_panel_6(p: dict[str, Any]) -> str:
    """Panel 6 HTML — multi-agent concurrent write conflict (Phase 15 north-star)."""
    north_star = _html_escape(str(p.get("north_star", "")))
    working_tree_count = int(p.get("working_tree_conflict_count", 0))
    git_log_count = int(p.get("git_log_conflict_count", 0))
    conflict_count = int(p.get("conflict_count", 0))
    status = _html_escape(str(p.get("status", "")))
    threshold = int(p.get("threshold", 0))
    locations = p.get("conflict_locations", [])
    loc_items: list[str] = []
    if isinstance(locations, list):
        for loc in locations[:10]:
            loc_items.append(f"      <li><code>{_html_escape(str(loc))}</code></li>")
    loc_html = "\n".join(loc_items) if loc_items else "      <li>(none)</li>"
    return f"""  <section class="panel panel-6">
    <h2>Panel 6 — Multi-Agent Concurrent Write Conflict</h2>
    <p class="meta">north_star: <code>{north_star}</code></p>
    <p class="meta">conflict_count: <strong>{conflict_count}</strong> (threshold={threshold})</p>
    <p class="meta">status: <strong>{status}</strong></p>
    <p class="meta">breakdown: working_tree={working_tree_count} · git_log={git_log_count}</p>
    <ul class="conflict-locations">
{loc_html}
    </ul>
  </section>"""


def _render_html_panel_7(p: dict[str, Any]) -> str:
    """Panel 7 HTML — deprecation cycle progress."""
    stage = _html_escape(str(p.get("stage", "")))
    declared = _html_escape(str(p.get("declared_stage", "")))
    bak = bool(p.get("bak_present", False))
    legacy = bool(p.get("legacy_present", False))
    warn = bool(p.get("deprecation_warning_supported", False))
    next_rel = _html_escape(str(p.get("next_release", "")))
    timeline = p.get("timeline", {})
    rows: list[str] = []
    if isinstance(timeline, dict):
        for ver, desc in timeline.items():
            marker = " ← <strong>current</strong>" if ver == stage else ""
            rows.append(
                f"      <tr><td><code>{_html_escape(str(ver))}</code></td>"
                f"<td>{_html_escape(str(desc))}{marker}</td></tr>"
            )
    rows_html = "\n".join(rows) if rows else "      <tr><td>(none)</td><td></td></tr>"
    return f"""  <section class="panel panel-7">
    <h2>Panel 7 — Deprecation Cycle Progress</h2>
    <p class="meta">stage: <strong>{stage}</strong></p>
    <p class="meta">declared_stage: <code>{declared}</code></p>
    <p class="meta">bak_present: <strong>{bak}</strong> · legacy_present: <strong>{legacy}</strong></p>
    <p class="meta">deprecation_warning_supported: <strong>{warn}</strong></p>
    <p class="meta">next_release: <code>{next_rel}</code></p>
    <table class="timeline">
      <thead><tr><th>Version</th><th>Stage</th></tr></thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
  </section>"""


def _render_html_panel_8(p: dict[str, Any]) -> str:
    """Panel 8 HTML — memory index + telemetry utilization v2."""
    entries_total = int(p.get("entries_total", 0))
    events_total = int(p.get("telemetry_events_total", 0))
    queries = int(p.get("telemetry_total_queries", 0))
    hits = int(p.get("telemetry_hit_count", 0))
    hit_rate = float(p.get("telemetry_hit_rate", 0.0))
    by_ms = p.get("entries_by_merge_state", {})
    by_src = p.get("telemetry_by_source", {})
    ms_rows = ""
    if isinstance(by_ms, dict):
        ms_rows = "".join(
            f"<tr><td><code>{_html_escape(str(k))}</code></td><td>{v}</td></tr>"
            for k, v in sorted(by_ms.items())
        )
    src_rows = ""
    if isinstance(by_src, dict):
        src_rows = "".join(
            f"<tr><td><code>{_html_escape(str(k))}</code></td><td>{v}</td></tr>"
            for k, v in sorted(by_src.items())
        )
    return f"""  <section class="panel panel-8">
    <h2>Panel 8 — Memory Index + Telemetry Utilization v2</h2>
    <p class="meta">phase_15_north_star: <code>{_html_escape(str(p.get('phase_15_north_star', '')))}</code></p>
    <p class="meta">entries_total: <strong>{entries_total}</strong></p>
    <p class="meta">telemetry_events_total: <strong>{events_total}</strong> · queries: {queries} · hits: {hits}</p>
    <p class="meta">telemetry_hit_rate: <strong>{hit_rate:.4f}</strong></p>
    <h4>Entries by merge_state</h4>
    <table><tbody>{ms_rows}</tbody></table>
    <h4>Telemetry by source</h4>
    <table><tbody>{src_rows}</tbody></table>
  </section>"""


def _render_html_charts_js(panels: dict[str, Any]) -> str:
    """Chart.js 초기화 JS — graceful: JS off 시 static fallback 그대로 보임.

    Chart.js 가 로드된 후 chart 인스턴스 생성. 미로드 시 catch 후 silent.
    """
    # Panel 2: maturity (bar — skills stable/beta/alpha vs mcp stable/beta/alpha)
    p2 = panels.get("maturity_distribution", {}) if isinstance(panels.get("maturity_distribution"), dict) else {}
    skills = p2.get("skills", {}) if isinstance(p2.get("skills"), dict) else {}
    mcp = p2.get("mcp_tools", {}) if isinstance(p2.get("mcp_tools"), dict) else {}

    # Panel 3: memory cumulative timeline (line)
    p3 = panels.get("memory_index_utilization", {}) if isinstance(panels.get("memory_index_utilization"), dict) else {}
    timeline = p3.get("cumulative_timeline", [])
    timeline_dates: list[str] = []
    timeline_counts: list[int] = []
    if isinstance(timeline, list):
        for entry in timeline:
            if isinstance(entry, dict):
                timeline_dates.append(str(entry.get("date", "")))
                try:
                    timeline_counts.append(int(entry.get("count", 0)))
                except (TypeError, ValueError):
                    timeline_counts.append(0)

    # Panel 4: smoke trend (line — release versions)
    p4 = panels.get("smoke_trend", {}) if isinstance(panels.get("smoke_trend"), dict) else {}
    recent = p4.get("recent_releases", [])
    smoke_versions: list[str] = []
    smoke_counts: list[int] = []
    if isinstance(recent, list):
        for entry in recent:
            if isinstance(entry, dict):
                smoke_versions.append(str(entry.get("version", "")))
                try:
                    smoke_counts.append(int(entry.get("pass", 0)))
                except (TypeError, ValueError):
                    smoke_counts.append(0)
    smoke_versions.reverse()
    smoke_counts.reverse()

    import json as _json

    chart_data = {
        "maturity": {
            "labels": ["skills", "mcp_tools"],
            "stable": [int(skills.get("stable", 0)), int(mcp.get("stable", 0))],
            "beta": [int(skills.get("beta", 0)), int(mcp.get("beta", 0))],
            "alpha": [int(skills.get("alpha", 0)), int(mcp.get("alpha", 0))],
        },
        "memory": {
            "dates": timeline_dates,
            "counts": timeline_counts,
        },
        "smoke": {
            "versions": smoke_versions,
            "counts": smoke_counts,
        },
    }
    json_str = _json.dumps(chart_data, ensure_ascii=False)
    return f"""    (function() {{
      var data = {json_str};
      function ready(fn) {{
        if (typeof window.Chart !== 'undefined') {{ fn(); }}
        else {{ window.addEventListener('load', function() {{ if (typeof window.Chart !== 'undefined') fn(); }}); }}
      }}
      ready(function() {{
        try {{
          new Chart(document.getElementById('chart-maturity'), {{
            type: 'bar',
            data: {{
              labels: data.maturity.labels,
              datasets: [
                {{ label: 'stable', data: data.maturity.stable, backgroundColor: '#1b8a3a' }},
                {{ label: 'beta', data: data.maturity.beta, backgroundColor: '#d68910' }},
                {{ label: 'alpha', data: data.maturity.alpha, backgroundColor: '#c0392b' }},
              ],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }} }}
          }});
          new Chart(document.getElementById('chart-memory'), {{
            type: 'line',
            data: {{
              labels: data.memory.dates,
              datasets: [{{ label: 'cumulative entries', data: data.memory.counts, borderColor: '#1d6fb8', fill: false, tension: 0.1 }}],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
          }});
          new Chart(document.getElementById('chart-smoke'), {{
            type: 'line',
            data: {{
              labels: data.smoke.versions,
              datasets: [{{ label: 'pass count', data: data.smoke.counts, borderColor: '#1b8a3a', fill: false, tension: 0.1 }}],
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }} }} }}
          }});
        }} catch (e) {{ /* silent — static fallback already visible */ }}
      }});
    }})();"""
