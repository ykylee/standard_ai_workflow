# Quality Dashboard Snapshot

- generated_at: `2026-11-23T07:35:49Z`
- tool_version: `3.0.1`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-23`
- maturity_surface_changed_at: `2026-11-23`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-23`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 47건)

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

- cumulative_total: `353`
- cumulative_pass: `353`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `353`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v3.0.1 | 353 | 353 |
| Beta-v3.0.0 | 353 | 353 |
| Beta-v2.1.0 | 350 | 350 |
| Beta-v2.0.0 | 346 | 346 |
| Beta-v1.29.0 | 333 | 333 |

## Panel 5 — Recent Release Cycle

- items_total: `28`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-23-main-004 — 3.0.0 Go 런타임 릴리즈 준비 점검  `[fresh]`
- [1] TASK-2026-11-23-main-003 — 세션·오케스트레이션 Python/Go 실사용 차분 검사  `[fresh]`
- [2] TASK-2026-11-23-main-002 — Go 허브 오케스트레이터 lease · 배정 · 승인 포팅  `[fresh]`
- [3] TASK-2026-11-23-main-001 — Go 허브 세션 · 받은편지함 · 오케스트레이션 포팅 1 — 세션/인박스 저장 계층  `[fresh]`
- [4] TASK-2026-11-22-main-041 — hub-go tools · mcpserver · httpapi · workflow-hub CLI 및 Go/Python 적합성 테스트 (M-055 WBS-55.3)  `[fresh]`
- [5] TASK-2026-11-22-main-040 — hub-go/internal/store 저장 계층 구현 (M-055 WBS-55.2)  `[fresh]`
- [6] TASK-2026-11-22-main-039 — hub-go/internal/db · assets · check_go_assets_sync 구현 (M-055 WBS-55.1)  `[fresh]`
- [7] TASK-2026-11-22-main-038 — judge/1 corpus 및 check_judge_parity 차분 검사 구현 (M-054 WBS-54.3)  `[fresh]`
- [8] TASK-2026-11-22-main-037 — wbs.gate · roadmap.derive · handoff.parse · state.build 순수 판정 구현 (M-054 WBS-54.2)  `[fresh]`
- [9] TASK-2026-11-22-main-036 — judge/1 CLI 프로토콜 + plan.lint · plan.states · task.status 순수 판정 구현 (M-054 WBS-54.1)  `[fresh]`

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
- telemetry_events_total: `3665`
- telemetry_total_queries: `3665`
- telemetry_hit_count: `1890`
- telemetry_hit_rate: `0.5157`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 1081 |
| `dispatcher` | 13 |
| `doc-sync` | 11 |
| `session-start` | 2560 |

