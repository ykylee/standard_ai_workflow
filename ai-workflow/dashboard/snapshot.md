# Quality Dashboard Snapshot

- generated_at: `2026-08-20T03:32:37Z`
- tool_version: `1.3.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-20`
- maturity_surface_changed_at: `2026-08-14`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-20`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 7건)

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

- entries_total: `10`
- entries_by_merge_state: `active`=10
- cue_anchors_unique: `61`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-08-20`

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

- cumulative_total: `264`
- cumulative_pass: `264`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `264`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.3.0 | 264 | 264 |
| Beta-v1.2.0 | 264 | 264 |
| Beta-v1.1.8 | 252 | 252 |
| Beta-v1.1.7 | 251 | 251 |
| Beta-v1.1.6 | 251 | 251 |

## Panel 5 — Recent Release Cycle

- items_total: `11`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-20-main-006 — release-status 의 next_version 이 커밋을 읽지 않는다 — 개수는 세고 판정은 안 센다  `[fresh]`
- [1] TASK-2026-08-20-main-005 — watch_transient_writer 의 고정 sleep 이 병렬 부하에서 깨진다 — 시간이 아니라 관측을 기다린다  `[fresh]`
- [2] TASK-2026-08-20-main-004 — memory_index 3-tuple 관찰 — 저점 고착의 원인은 검색이 아니라 종료 절차 배선  `[fresh]`
- [3] TASK-2026-08-20-main-003 — OKF v0.2 이행 — ADR-026 + status 어휘 매핑 + sources 필드  `[fresh]`
- [4] TASK-2026-08-20-main-002 — 날짜 롤오버 때 열린 task 가 mismatch 로 잡힌다 — linter 가 SSOT 대신 하루치 index 를 본다  `[fresh]`
- [5] TASK-2026-08-20-main-001 — wiki L2 계약을 memory 파생 4종으로 좁힌다 — L1→L2 경로 은퇴 + 지표 분모 재정의  `[fresh]`
- [6] TASK-2026-08-18-main-006 — OKF 상호운용 실측 — 다른 생산자의 번들과 대조  `[fresh]`
- [7] TASK-2026-08-18-main-005 — 드리프트 감지 — 마커가 아니라 페이로드 해시로 비교  `[fresh]`
- [8] TASK-2026-08-18-main-004 — wiki 3-step 파이프라인의 하위 두 단계가 죽어 있다 — 스키마·레이아웃 드리프트  `[fresh]`
- [9] TASK-2026-08-18-main-003 — 배포본에서 죽는 workflow-source 경로 참조 — wk 명령 6종 실측  `[fresh]`

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
- entries_total: `10`
- telemetry_events_total: `339`
- telemetry_total_queries: `339`
- telemetry_hit_count: `41`
- telemetry_hit_rate: `0.1209`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 10 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 45 |
| `session-start` | 294 |

