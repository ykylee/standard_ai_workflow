# Quality Dashboard Snapshot

- generated_at: `2026-08-29T14:45:40Z`
- tool_version: `1.7.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-28`
- maturity_surface_changed_at: `2026-08-28`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-08-29`
- last_updated_delta_days: `1`
- silent_failing_cycles_count: `0` (측정 cycle 11건)

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

- entries_total: `15`
- entries_by_merge_state: `active`=15
- cue_anchors_unique: `101`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-08-24`

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

- cumulative_total: `276`
- cumulative_pass: `276`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `276`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.7.0 | 276 | 276 |
| Beta-v1.6.0 | 275 | 275 |
| Beta-v1.5.0 | 274 | 274 |
| Beta-v1.4.0 | 274 | 274 |
| Beta-v1.3.0 | 267 | 267 |

## Panel 5 — Recent Release Cycle

- items_total: `52`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-14-main-010 — 검증 결과 주입이 작업 결과 묶음을 갈라 다음 갱신에서 고아 줄을 만든다  `[fresh]`
- [1] TASK-2026-08-14-main-008 — task SSOT 를 구조화 — markdown-as-database 결함 계열 제거  `[fresh]`
- [2] TASK-2026-08-14-main-007 — handoff 기준선 롤오프 — §1 이 handoff 의 66%  `[fresh]`
- [3] TASK-2026-08-14-main-006 — 아카이브가 '살아 있는 대상' 상대 링크를 안 고친다 — 같은 함정 2회째  `[fresh]`
- [4] TASK-2026-08-14-main-003 — 변경 범위 기반 선택 실행 — run_all_checks --changed  `[fresh]`
- [5] TASK-2026-08-14-main-002 — 배포 채널 확정 — PyPI 발행 안 함 (소유자 최종 결정) + 재론 방지 기록  `[fresh]`
- [6] TASK-2026-08-14-main-001 — 브랜치 정리 — fix/archive-history-integrity 종료 + 아카이브, 그리고 자기 적용 검사의 위양성  `[fresh]`
- [7] TASK-2026-08-13-main-009 — 전량 검사 시간 — 정숙 구간 직렬화가 벽시계의 36%  `[fresh]`
- [8] TASK-2026-08-13-main-008 — TestPyPI 리허설  `[fresh]`
- [9] TASK-2026-08-13-main-007 — 공개 배포 전 필수 수리 3건 — LICENSE 부재 / 버전 체계 모순 / 저자 이메일  `[fresh]`

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
- entries_total: `15`
- telemetry_events_total: `722`
- telemetry_total_queries: `722`
- telemetry_hit_count: `328`
- telemetry_hit_rate: `0.4543`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 63 |
| `dispatcher` | 1 |
| `doc-sync` | 3 |
| `session-start` | 655 |

