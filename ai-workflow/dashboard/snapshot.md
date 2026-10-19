# Quality Dashboard Snapshot

- generated_at: `2026-10-19T14:39:12Z`
- tool_version: `1.21.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-10-19`
- maturity_surface_changed_at: `2026-10-06`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-10-19`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 35건)

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

- cumulative_total: `309`
- cumulative_pass: `309`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `309`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.21.0 | 309 | 309 |
| Beta-v1.20.1 | 309 | 309 |
| Beta-v1.20.0 | 309 | 309 |
| Beta-v1.19.0 | 302 | 302 |
| Beta-v1.18.0 | 300 | 300 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-10-19-main-004 — goal coverage 가 '어느 마일스톤도 섬기지 않는 goal' 을 조용히 uncovered 로 센다 — 닿을 수 없는 goal 을 provenance 로 지목  `[fresh]`
- [1] TASK-2026-10-19-main-003 — check_memory_lint T1a · T1c · T1d 가 legacy 경로라 항상 skip — 은퇴 1 · branch-scoped 재작성 2  `[fresh]`
- [2] TASK-2026-10-19-main-002 — check_memory_lint T1b stale 가 branch-scoped 전환 뒤 공유층 파일만 잰다 — 시간 경과만으로 red  `[fresh]`
- [3] TASK-2026-10-19-main-001 — 진입점 다이어트 harvest 재실행 — v1.20.0 생성물 채취 + '현행 생성물 ⊆ 알려진 생성물' 검사로 재실행 누락 고정  `[fresh]`
- [4] TASK-2026-10-06-main-009 — minimax_plugin --apply 출력이 반영 뒤 상태를 찍어 무엇이 바뀌었는지 오독된다  `[fresh]`
- [5] TASK-2026-10-06-main-008 — RELEASE.md §2.8 에 minimax-code 재적용 · 확인 절차 보강  `[fresh]`
- [6] TASK-2026-10-06-main-007 — v1.20.1 발행 — backlog-update handoff 제목 동기화 수리 (patch)  `[fresh]`
- [7] TASK-2026-10-06-main-006 — backlog-update 의 handoff 동기화가 보존된 task 제목 대신 입력 --task-name 을 쓴다  `[fresh]`
- [8] TASK-2026-10-06-main-005 — v1.20.0 발행 — 진입점 다이어트(규칙 블록 · bootstrap 템플릿 · --diet) + AI-native SDLC A1~A3 + MiniMax Code 채…  `[fresh]`
- [9] TASK-2026-10-06-main-004 — [진입점 다이어트 3] 기존 진입점 다이어트 단계 — 채택 프로젝트의 진입점을 예산 · 현행 템플릿과 대조해 보고/정리  `[fresh]`

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
- telemetry_events_total: `3106`
- telemetry_total_queries: `3106`
- telemetry_hit_count: `1342`
- telemetry_hit_rate: `0.4321`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 590 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2501 |

