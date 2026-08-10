# Quality Dashboard Snapshot

- generated_at: `2026-08-10T04:23:04Z`
- tool_version: `v1.1.5-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-08-10`
- maturity_surface_changed_at: `2026-08-10`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-10`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 2건)

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

- entries_total: `7`
- entries_by_merge_state: `active`=7
- cue_anchors_unique: `40`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-07-09`

### Top cue anchors

| anchor | count |
|---|---|
| P0 | 2 |
| audit | 1 |
| workflow | 1 |
| 2026-07-09 | 1 |
| candidates | 1 |
| snapshot | 1 |
| P1 | 1 |
| P2 | 1 |
| ADR-005 | 1 |
| memory-index | 1 |

## Panel 4 — Smoke Trend

- cumulative_total: `261`
- cumulative_pass: `261`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `261`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.1.5 | 261 | 261 |
| Beta-v1.1.4 | 261 | 261 |
| Beta-v1.1.3 | 260 | 260 |
| Beta-v1.1.2 | 259 | 259 |

## Panel 5 — Recent Release Cycle

- items_total: `49`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-10-main-004 — TST-WF-01 측정 재설계 (AST signal 기반, dummy 배제, partial 예외 제거, check_tst_wf01_signals 9/9)  `[fresh]`
- [1] TASK-2026-08-10-main-003 — v1.1.4-beta 를 cmd_release 경로로 발행 (수동 발행 관행 종료, pre_check 5/5 skip 없이 통과, amend 가드 첫 정상 완주)  `[fresh]`
- [2] TASK-2026-08-10-main-001 — cmd_release 사용성 회복 (pre_check 만성 실패 3뿌리 해소 + release 기본 dry-run + 개별 skip 5종 + check_release_…  `[fresh]`
- [3] TASK-2026-08-10-main-002 — check_mavis_attach_e2e 호스트 사본 제거 (darwin 절대경로 하드코딩 → 실제 mcp.json 정본 읽기 + graceful skip / --re…  `[fresh]`
- [4] TASK-2026-08-09-main-017 — v1.1.3-beta release 발행 (TASK-009~016, 11 커밋). 오늘 고친 릴리스 도구 3건이 실제 릴리스에서 검증됨  `[fresh]`
- [5] TASK-2026-08-09-main-016 — 릴리스 절차에 노트 누적 수치 검증 step 3.4 신설 (검증만, 자동 작성 ❌ — 전량 PASS 는 사람의 주장). check_release_wrapper_args…  `[fresh]`
- [6] TASK-2026-08-09-main-015 — check_smoke_trend_cross 오독 정정 (검사가 맞았다). 노트 누적 수치는 살아있는 지표 — 판정 복원 + Beta-v1.1.2 257→259 갱신. …  `[fresh]`
- [7] TASK-2026-08-09-main-014 — memory-index-query beta → stable (error_code 3종 + SKILL.md 실행 예시 + smoke 26/26). skill 14 sta…  `[fresh]`
- [8] TASK-2026-08-09-main-013 — phase_13_followup 전반 실측 대조 (정합 5 / 정정 3) + harness 정본 정의 확정 (NON_OVERLAY_HARNESSES, 검사 하드코딩 →…  `[fresh]`
- [9] TASK-2026-08-09-main-012 — Phase 13 P1 묶음 close. 3건 모두 문서가 실제와 달랐다 (P1-1 구현 이미 존재 / P1-2·P1-3 이미 stable). CHANGELOG 재생성 …  `[fresh]`

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

- phase_15_north_star: `telemetry_hit_rate (1 release ≥ 1 query + hit)`
- entries_total: `7`
- telemetry_events_total: `237`
- telemetry_total_queries: `237`
- telemetry_hit_count: `237`
- telemetry_hit_rate: `1.0000`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 7 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 43 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 192 |

