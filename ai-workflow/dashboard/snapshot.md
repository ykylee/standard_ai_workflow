# Quality Dashboard Snapshot

- generated_at: `2026-09-29T05:15:02Z`
- tool_version: `1.14.4`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-29`
- maturity_surface_changed_at: `2026-09-29`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-29`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 27건)

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

- cumulative_total: `296`
- cumulative_pass: `296`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `296`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.14.4 | 296 | 296 |
| Beta-v1.14.3 | 296 | 296 |
| Beta-v1.14.2 | 296 | 296 |
| Beta-v1.14.1 | 296 | 296 |
| Beta-v1.14.0 | 296 | 296 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-29-main-013 — Windows: doctor MCP 해석기 탐침이 python3.CMD shim 경유 시 cmd.exe 가 -c 다줄 스크립트를 첫 개행에서 자른다 (소유자 전달 버그…  `[fresh]`
- [1] TASK-2026-09-29-main-012 — wiki 스탬프 단일화 — frontmatter updated: 를 정본으로, 게이트·doc-headers-update 가 그것을 판정·갱신 (100차 후속)  `[fresh]`
- [2] TASK-2026-09-29-main-011 — claude runtime_load 재시작 확인 (100차 후속, v1.14.3)  `[fresh]`
- [3] TASK-2026-09-29-main-010 — 상태 헤더 없는 wiki 6건의 스탬프 판정 범위  `[fresh]`
- [4] TASK-2026-09-29-main-009 — v1.14.3 발행 — 스탬프 형식 판정 + backlog-update kind 표식 수리  `[fresh]`
- [5] TASK-2026-09-29-main-008 — backlog-update 가 kind 규약을 모른다 — session kind 무source 생성 허용 + update 시 daily index kind 표식 미갱신  `[fresh]`
- [6] TASK-2026-09-29-main-007 — 스탬프 게이트가 주석 달린 스탬프 줄을 조용히 건너뛰는 것  `[fresh]`
- [7] TASK-2026-09-29-main-006 — claude runtime_load 재시작 확인 (98차 후속)  `[fresh]`
- [8] TASK-2026-09-29-main-005 — v1.14.2 발행 — 공유 AGENTS.md 마커로 opencode 오버레이가 생기던 것 수리  `[fresh]`
- [9] TASK-2026-09-29-main-004 — 공유 AGENTS.md 마커 때문에 opencode 가 적용된 하네스로 판정돼 session-start 가 opencode 오버레이를 만든다  `[fresh]`

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
- telemetry_events_total: `2982`
- telemetry_total_queries: `2982`
- telemetry_hit_count: `1230`
- telemetry_hit_rate: `0.4125`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 496 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2471 |

