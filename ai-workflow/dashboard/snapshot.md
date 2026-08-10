# Quality Dashboard Snapshot

- generated_at: `2026-08-10T11:30:53Z`
- tool_version: `v1.1.6-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-08-10`
- maturity_surface_changed_at: `2026-08-10`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-10`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 3건)

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

- supported: `11`
- names: `aider`, `antigravity`, `claude-code`, `codewhale`, `codex`, `gemini-cli`, `goose`, `grok-build`, `minimax-code`, `opencode`, `pi-dev`

## Panel 3 — Memory Index Utilization

- entries_total: `8`
- entries_by_merge_state: `active`=8
- cue_anchors_unique: `47`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-08-10`

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

- cumulative_total: `266`
- cumulative_pass: `266`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `266`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.1.6 | 266 | 266 |
| Beta-v1.1.5 | 266 | 266 |
| Beta-v1.1.4 | 261 | 261 |
| Beta-v1.1.3 | 260 | 260 |
| Beta-v1.1.2 | 259 | 259 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-10-main-014 — ADR-006 W-4: memory_index 지표 재정의 (3-tuple)  `[fresh]`
- [1] TASK-2026-08-10-main-013 — ADR-006 W-3: entry 간 링크 (expansion 이 사는 전제)  `[fresh]`
- [2] TASK-2026-08-10-main-012 — ADR-006 W-2: memory_index 질의 다양화  `[fresh]`
- [3] TASK-2026-08-10-main-011 — ADR-006 W-1: memory_index write-path advisory 루프  `[fresh]`
- [4] TASK-2026-08-10-main-010 — P2-1 ADR-006 Memory Index 회고 본문 작성  `[fresh]`
- [5] TASK-2026-08-10-main-009 — registry server 비-loopback bind 실측  `[fresh]`
- [6] TASK-2026-08-10-main-008 — title drift 임계 0.6 실측 보정  `[fresh]`
- [7] TASK-2026-08-10-main-007 — v0.15.18 dummy wrapper 물리 제거  `[fresh]`
- [8] TASK-2026-08-10-main-006 — v1.1.5-beta 발행 (cmd_release 2번째 실전)  `[fresh]`
- [9] TASK-2026-08-10-main-005 — dist 기본값 dry-run 반전 (release 와 정합)  `[fresh]`

## Panel 6 — Multi-Agent Concurrent Write Conflict

- north_star: `multi_agent_concurrent_write_conflict_count`
- conflict_count: `0` (source: `working_tree+git_log`)
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
- entries_total: `8`
- telemetry_events_total: `273`
- telemetry_total_queries: `273`
- telemetry_hit_count: `262`
- telemetry_hit_rate: `0.9597`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 8 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 43 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 228 |

