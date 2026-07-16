# Beta v0.14.7 — Phase 15 follow-up (HTML renderer Panel 6/7/8 + git reflog) (2026-07-16)

> **Phase 15 dashboard 의 8 panel HTML renderer 완전 정합 + Panel 6 의 git reflog 통합.**
> breaking change ❌.

## 1. 핵심 변경 (3 deliverable)

### 1.1 Panel 6 — git reflog 통합

기존 working tree `<<<<<<<` marker scan 만 → **git history 까지 확장**:

```python
# subprocess `git log --all --merges --pretty=format:%H %s` + CONFLICT keyword filter
proc = _subprocess.run(
    ["git", "log", "--all", "--merges", "--pretty=format:%H %s"],
    cwd=str(root), capture_output=True, text=True, timeout=10, check=False,
)
if proc.returncode == 0:
    git_log_conflict_count = sum(
        1 for line in proc.stdout.splitlines()
        if "CONFLICT" in line.upper()
    )
```

- output field 추가: `working_tree_conflict_count` + `git_log_conflict_count`.
- `conflict_count = working + git_log` (combined, total indicator).
- 기존 `conflict_locations` + `status` + `threshold` 유지.
- **timeout 10s + graceful error fallback** (subprocess 실패 시 Panel 6 status='warning').

### 1.2 HTML Panel 6/7/8 render 함수 신규

- `_render_html_panel_6`: north_star / conflict_count / status / threshold + breakdown
  (`working_tree=N · git_log=M`) + conflict_locations `<ul>`.
- `_render_html_panel_7`: stage / declared_stage / bak_present / legacy_present /
  deprecation_warning_supported / next_release + timeline `<table>` with current marker.
- `_render_html_panel_8`: phase_15_north_star / entries_total / telemetry_events_total /
  queries / hits / hit_rate + by_merge_state + by_source 2 table.

### 1.3 `render_dashboard_html` panels 순회 부분

Panel 5 다음에 Panel 6/7/8 HTML render 함수 호출 추가.

`snapshot.html` regen (9884 bytes, Panel 6/7/8 정합 emit).

## 2. smoke 정합

`tests/check_phase15_dashboard_panels.py` 의 case_1_panel_6_conflict 에 v0.14.7+ 검증 추가 — `working_tree_conflict_count` + `git_log_conflict_count` (둘 다 non-negative int). **4/4 PASS 유지**.

## 3. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 · git_history_summarizer 5/5 · smart_context_reader 5/5 · apply_robust_patch 5/5 · **phase15_dashboard_panels 4/4** · deprecation_cycle_v0_14_5 4/4 · refresh_maturity_v0_14_6 4/4

## 4. 의의

- Phase 15 dashboard 의 8 panel HTML renderer 완전 정합.
- Panel 6 의 multi-agent write conflict metric 이 working tree + git history 양쪽 통합 검출.
- 기존 markdown snapshot 외 HTML consumer (browser / Slack preview) 도 정합 panel 데이터 확인 가능.

## 5. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.7/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.7/backlog/2026-07-16.md)

## 6. 다음 step

- 2nd deprecation cycle 종결 (`.bak` drop, ⚠️ BREAKING) → **v0.15.0**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.7-beta>