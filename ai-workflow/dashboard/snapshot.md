# Quality Dashboard Snapshot

- generated_at: `2026-11-24T06:01:22Z`
- tool_version: `3.2.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-24`
- maturity_surface_changed_at: `2026-11-24`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-24`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 49건)

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

- cumulative_total: `357`
- cumulative_pass: `357`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `357`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v3.2.0 | 357 | 357 |
| Beta-v3.1.0 | 354 | 354 |
| Beta-v3.0.1 | 353 | 353 |
| Beta-v3.0.0 | 353 | 353 |
| Beta-v2.1.0 | 350 | 350 |

## Panel 5 — Recent Release Cycle

- items_total: `40`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-24-main-005 — 1.x → Hub 전환 뒤 진입 파일의 이전 경로 잔존 수정  `[fresh]`
- [1] TASK-2026-11-24-main-004 — 허브 task 목록 분류·페이지네이션·카드 보기  `[fresh]`
- [2] TASK-2026-11-24-main-003 — 미등록 하네스 제보와 승인 등록 흐름  `[fresh]`
- [3] TASK-2026-11-24-main-001 — 3.1.0 pre-release 및 홈랩 허브 배포  `[fresh]`
- [4] TASK-2026-11-23-main-022 — 3단계 작업 카테고리와 roadmap·WBS·테스트 관리 연결  `[fresh]`
- [5] TASK-2026-11-23-main-021 — 허브 release 버전과 kit 호환 버전을 API·페이지에 함께 표시  `[fresh]`
- [6] TASK-2026-11-23-main-020 — 프로젝트 목록 화면에 null 문자열 노출 수정  `[fresh]`
- [7] TASK-2026-11-23-main-019 — 허브 셋업에서 로컬 중계 필요 여부와 상태 확인  `[fresh]`
- [8] TASK-2026-11-23-main-018 — 홈랩 3.0.1 허브 배포 및 dacpi /workflow 프록시 연결  `[fresh]`
- [9] TASK-2026-11-23-main-017 — 허브 배포 위치 검토: 개발 호스트 vs 홈랩  `[fresh]`

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
- telemetry_events_total: `3802`
- telemetry_total_queries: `3802`
- telemetry_hit_count: `2027`
- telemetry_hit_rate: `0.5331`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 1188 |
| `dispatcher` | 13 |
| `doc-sync` | 26 |
| `session-start` | 2575 |

