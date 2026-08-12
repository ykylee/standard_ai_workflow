# Quality Dashboard Snapshot

- generated_at: `2026-08-12T04:11:20Z`
- tool_version: `v1.1.7-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-08-12`
- maturity_surface_changed_at: `2026-08-12`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-12`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 4건)

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

- entries_total: `9`
- entries_by_merge_state: `active`=9
- cue_anchors_unique: `53`
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

- cumulative_total: `251`
- cumulative_pass: `251`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `251`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.1.7 | 251 | 251 |
| Beta-v1.1.6 | 251 | 251 |
| Beta-v1.1.5 | 266 | 266 |
| Beta-v1.1.4 | 261 | 261 |
| Beta-v1.1.3 | 260 | 260 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-12-main-001 — federation self-host add — plex 상시 serving 편입  `[fresh]`
- [1] TASK-2026-08-11-main-028 — 잔여 렌더러 14개 §11 주입 (1순위 진입점 6개 우선)  `[fresh]`
- [2] TASK-2026-08-11-main-027 — 소비자 안내 표면 정리 (SKILL.md 미배포 경로 + packaging 검사 공백)  `[fresh]`
- [3] TASK-2026-08-11-main-026 — §11 단일출처 검사 강화 + goose hook 깨진 경로  `[fresh]`
- [4] TASK-2026-08-11-main-025 — MCP 도구 목록 단일출처화 (MiniMax 손 목록 + manifest 유령 경로)  `[fresh]`
- [5] TASK-2026-08-11-main-024 — MCP readOnlyHint 허위 주석 정정 + ADR-003 개정  `[fresh]`
- [6] TASK-2026-08-11-main-023 — wk backlog-update update 모드 파괴적 재생성 수정  `[fresh]`
- [7] TASK-2026-08-11-main-022 — 하네스 파생본 통일 (정본 블록 + 전 렌더러 주입)  `[fresh]`
- [8] TASK-2026-08-11-main-021 — `wk` 에 session-start / backlog-update / doc-sync 노출  `[fresh]`
- [9] TASK-2026-08-11-main-020 — 하네스 진입점이 kit 스크립트를 안 가리킨다  `[fresh]`

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
- entries_total: `9`
- telemetry_events_total: `588`
- telemetry_total_queries: `588`
- telemetry_hit_count: `305`
- telemetry_hit_rate: `0.5187`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 9 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 69 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 517 |

