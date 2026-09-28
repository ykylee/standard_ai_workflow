# Quality Dashboard Snapshot

- generated_at: `2026-09-28T08:47:00Z`
- tool_version: `1.12.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-28`
- maturity_surface_changed_at: `2026-09-23`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-28`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 21건)

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
| Beta-v1.12.0 | 296 | 296 |
| Beta-v1.11.0 | 292 | 292 |
| Beta-v1.10.0 | 290 | 290 |
| Beta-v1.9.4 | 284 | 284 |
| Beta-v1.9.3 | 282 | 282 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-28-main-013 — 세션 시작 컨텍스트 예산 — implementation (출구 먼저, red 나중)  `[fresh]`
- [1] TASK-2026-09-28-main-012 — 세션 시작 컨텍스트 예산 — design (ADR-029 + core 스펙 절)  `[fresh]`
- [2] TASK-2026-09-28-main-011 — 세션 시작 컨텍스트 예산 — requirements (출구 + 예산)  `[fresh]`
- [3] TASK-2026-09-28-main-010 — task ID 충돌 검출을 session-start warning 으로도 낸다  `[fresh]`
- [4] TASK-2026-09-28-main-009 — release validate 의 source 목록 사본이 따로 낡는다 — '전부 skip' 이 새 source 를 못 따라감  `[fresh]`
- [5] TASK-2026-09-28-main-008 — 게이트 상위 검사 3개(run_all_checks · workflow_kit_cli · wiki_trend)의 검사 내 반복 계산  `[fresh]`
- [6] TASK-2026-09-28-main-007 — release 계열 검사 4개가 같은 인자의 subprocess 를 반복한다 — 게이트 CPU 합 상위  `[fresh]`
- [7] TASK-2026-09-28-main-006 — 검사 5개가 실제 저장소 telemetry 에 session-start 를 기록해 사용 지표를 게이트마다 +10 부풀린다  `[fresh]`
- [8] TASK-2026-09-28-main-005 — 대시보드가 telemetry events.jsonl 을 패널마다 따로 읽어, 게이트 중 추가된 이벤트로 Panel 3·8 hit_rate 가 갈린다  `[fresh]`
- [9] TASK-2026-09-28-main-004 — check_wiki_score 가 점수 도구를 3회 돈다 — 멱등성 case 가 공유 실행을 안 쓴다  `[fresh]`

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
- telemetry_events_total: `2924`
- telemetry_total_queries: `2924`
- telemetry_hit_count: `1172`
- telemetry_hit_rate: `0.4008`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 448 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2461 |

