# Quality Dashboard Snapshot

- generated_at: `2026-11-24T23:52:33Z`
- tool_version: `3.3.2`
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
- silent_failing_cycles_count: `0` (측정 cycle 56건)

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

- cumulative_total: `358`
- cumulative_pass: `358`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `358`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v3.3.2 | 358 | 358 |
| Beta-v3.3.1 | 358 | 358 |
| Beta-v3.3.0 | 358 | 358 |
| Beta-v3.2.4 | 357 | 357 |
| Beta-v3.2.3 | 357 | 357 |

## Panel 5 — Recent Release Cycle

- items_total: `40`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-24-main-019 — Go 허브 미구현 도구 10종 포팅  `[fresh]`
- [1] TASK-2026-11-24-main-018 — 허브 셋업 완료 판정·MCP 단계·진입 안내 결함 수리  `[fresh]`
- [2] TASK-2026-11-24-main-017 — 프록시 뒤 계정 등록 403 수리와 비밀번호 8자 (v3.2.3)  `[fresh]`
- [3] TASK-2026-11-24-main-015 — v3.2.2 pre-release 및 홈랩 배포  `[fresh]`
- [4] TASK-2026-11-24-main-014 — 에이전트 요청·사람 로그인 승인으로 이관 실행  `[fresh]`
- [5] TASK-2026-11-24-main-013 — Go 허브 1.x 이관 도구 포팅과 홈랩 셀프 이관  `[fresh]`
- [6] TASK-2026-11-24-main-012 — 허브 관리자 콜사인 삭제와 고아 콜사인 정리  `[fresh]`
- [7] TASK-2026-11-24-main-011 — Go 허브 hub_setup_confirm 포팅 — 새 환경 부트스트랩 차단 해소  `[fresh]`
- [8] TASK-2026-11-24-main-010 — 에이전트 확인 요청 메뉴와 A2A 승인 결과 전달  `[fresh]`
- [9] TASK-2026-11-24-main-009 — 3.2.1 pre-release 및 홈랩 파일럿 배포  `[fresh]`

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
- telemetry_events_total: `3875`
- telemetry_total_queries: `3875`
- telemetry_hit_count: `2100`
- telemetry_hit_rate: `0.5419`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 1250 |
| `dispatcher` | 13 |
| `doc-sync` | 33 |
| `session-start` | 2579 |

