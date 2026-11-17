# Quality Dashboard Snapshot

- generated_at: `2026-11-17T06:14:14Z`
- tool_version: `1.27.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-17`
- maturity_surface_changed_at: `2026-11-16`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-17`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 41건)

## Panel 2 — Maturity Distribution

### skills

| metric | value |
|---|---|
| total | 14 |
| stable | 14 |
| beta | 0 |
| alpha | 0 |

### mcp_tools

| metric | value |
|---|---|
| total | 12 |
| stable | 11 |
| beta | 0 |
| alpha | 0 |

### milestones

| metric | value |
|---|---|
| total | 13 |
| done | 12 |
| in_progress | 1 |
| planned | 0 |

### harnesses

- supported: `10`
- names: `aider`, `antigravity`, `claude-code`, `codewhale`, `codex`, `goose`, `grok-build`, `minimax-code`, `opencode`, `pi-dev`

## Panel 3 — Memory Index Utilization

- entries_total: `30`
- entries_by_merge_state: `active`=30
- cue_anchors_unique: `180`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-09-23`

### Top cue anchors

| anchor | count |
|---|---|
| P0 | 2 |
| memory-index | 2 |
| audit | 1 |
| workflow | 1 |
| 2026-07-09 | 1 |
| candidates | 1 |
| snapshot | 1 |
| P1 | 1 |
| P2 | 1 |
| ADR-005 | 1 |

## Panel 4 — Smoke Trend

- cumulative_total: `332`
- cumulative_pass: `332`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `332`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.27.0 | 332 | 332 |
| Beta-v1.26.0 | 329 | 329 |
| Beta-v1.25.0 | 325 | 325 |
| Beta-v1.24.0 | 322 | 322 |
| Beta-v1.23.0 | 319 | 319 |

## Panel 5 — Recent Release Cycle

- items_total: `26`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-17-claude-remote-sync-check-234c32-005 — 한 호스트에 워크벤치 여러 개 — 포트 분배 + 화면에 저장소 · 브랜치 표시  `[fresh]`
- [1] TASK-2026-11-17-claude-remote-sync-check-234c32-003 — 작업 중 워크벤치 진행 기록(--progress-note) 지침 강화 — 정본 · 모든 하네스 진입점으로  `[fresh]`
- [2] TASK-2026-11-17-claude-remote-sync-check-234c32-001 — 브랜치 네임스페이스 자동 seed — `main` 에서 이어받음  `[fresh]`
- [3] TASK-2026-11-16-main-018 — v1.26.0 발행 — 워크벤치 todo · 응답 자동 반영 + 대시보드 · 워크벤치 수리 넷  `[fresh]`
- [4] TASK-2026-11-16-main-017 — 워크벤치 todo 화면 · 편집 + 작업 세션 알림  `[fresh]`
- [5] TASK-2026-11-16-main-016 — todo 저장소 + todo CLI — 브랜치 할 일 · task 체크리스트  `[fresh]`
- [6] TASK-2026-11-16-main-015 — 대시보드 drift 가드가 오류로 끝나면 guard_cases 0 을 실어 '0/0 pass' 로 그린다  `[fresh]`
- [7] TASK-2026-11-16-main-014 — 워크벤치 응답이 작업 세션에 바로 닿지 않는다 — 도착 신호 + hook 자동 반영 · 알림  `[fresh]`
- [8] TASK-2026-11-16-main-013 — 워크벤치 글자가 박스를 넘는다 — 긴 글 · 좁은 폭 · 다른 글꼴에서도 박스 안에  `[fresh]`
- [9] TASK-2026-11-16-main-012 — 대시보드 inline_guard=False 가 가드를 돌리지 않고 guard_cases 7 · pass 0 을 실측처럼 싣는다  `[fresh]`

## Panel 6 — Multi-Agent Concurrent Write Conflict

- north_star: `multi_agent_concurrent_write_conflict_count`
- conflict_count: `0` (source: `working_tree+git_log+task_id_remote`)
- threshold: `0`
- status: `pass`

## Panel 7 — Deprecation Cycle Progress

- stage: `v0.15.0`
- bak_present: `False`
- legacy_present: `False`
- deprecation_warning_supported: `True`
- next_release: `(complete)`

### Timeline

| Version | Stage |
|---|---|
| `v0.14.0` | 1st cycle 시작 (silent fallback) |
| `v0.14.1` | 1st cycle 종결 (warning stage) |
| `v0.14.5` | 2nd cycle 시작 (--legacy-memory opt-out flag) |
| `v0.15.0` | 2nd cycle 종결 (.bak drop) ← **current** |

## Panel 8 — Memory Index + Telemetry Utilization v2

- phase_15_north_star: `utilization_3tuple (query_diversity / entries_new_30d / distinct_entries_retrieved — ADR-006 W-4; hit_rate 는 보조)`
- entries_total: `30`
- telemetry_events_total: `3214`
- telemetry_total_queries: `3214`
- telemetry_hit_count: `1444`
- telemetry_hit_rate: `0.4493`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 682 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2517 |

