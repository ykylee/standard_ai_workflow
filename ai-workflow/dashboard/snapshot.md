# Quality Dashboard Snapshot

- generated_at: `2026-09-23T06:50:26Z`
- tool_version: `1.11.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-23`
- maturity_surface_changed_at: `2026-09-22`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-23`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 20건)

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

- entries_total: `29`
- entries_by_merge_state: `active`=29
- cue_anchors_unique: `174`
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

- cumulative_total: `292`
- cumulative_pass: `292`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `292`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.11.0 | 292 | 292 |
| Beta-v1.10.0 | 290 | 290 |
| Beta-v1.9.4 | 284 | 284 |
| Beta-v1.9.3 | 282 | 282 |
| Beta-v1.9.2 | 280 | 280 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-23-main-007 — case 수 대조 축 잔여 22건 — 흐름이 둘인 검사가 무엇이 case 인지 스스로 말하게 (main-006 follow-up)  `[fresh]`
- [1] TASK-2026-09-23-main-006 — case 수 대조 축의 사각지대 — 개수 선언이 없는 검사를 실측으로 가른다 (main-004 follow-up)  `[fresh]`
- [2] TASK-2026-09-23-main-005 — memory_index 검색이 매칭된 entry 자신을 안 돌려준다 (seed 가 확장분에 ID순으로 밀림) + 한국어 질의는 기본 경로에서 0  `[fresh]`
- [3] TASK-2026-09-23-main-004 — 검사 요약의 총 개수가 상수라 case 증감을 못 본다 (전수 20건 중 4건 현재 불일치)  `[fresh]`
- [4] TASK-2026-09-23-main-003 — memory_index 승격 후보 판정을 어휘 겹침에서 선언(source_paths)으로  `[fresh]`
- [5] TASK-2026-09-23-main-002 — check_release_wrapper_args case 6 이 git 인덱스 락을 잡아 병렬에서 flake  `[fresh]`
- [6] TASK-2026-09-23-main-001 — memory_index 승격 — 후보 판정식이 잡음이라 도구 순위가 아니라 판단으로 고른다  `[fresh]`
- [7] TASK-2026-09-22-main-008 — 전량 검사 시간 단축 — 저장소 write 감시를 러너에 흡수 (재실행 76.7s 제거)  `[fresh]`
- [8] TASK-2026-09-22-main-007 — CI 의 Python 하한 측정을 부분 → 전수로 — 소유자 보류 번복  `[fresh]`
- [9] TASK-2026-09-22-main-006 — 뒤처진 스탬프 소급 교정 — doc-headers-update 범위를 손 목록에서 파생으로  `[fresh]`

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
- entries_total: `29`
- telemetry_events_total: `2595`
- telemetry_total_queries: `2595`
- telemetry_hit_count: `880`
- telemetry_hit_rate: `0.3391`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 29 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 391 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2189 |

