# Quality Dashboard Snapshot

- generated_at: `2026-11-16T06:31:54Z`
- tool_version: `1.25.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow-main`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-16`
- maturity_surface_changed_at: `2026-11-16`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-16`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 39건)

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

- cumulative_total: `325`
- cumulative_pass: `325`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `325`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.25.0 | 325 | 325 |
| Beta-v1.24.0 | 322 | 322 |
| Beta-v1.23.0 | 319 | 319 |
| Beta-v1.22.0 | 309 | 309 |
| Beta-v1.21.0 | 309 | 309 |

## Panel 5 — Recent Release Cycle

- items_total: `20`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-16-main-003 — 워크벤치 화면 개편 — 대시보드형 진척 · 카드형 계획 화면  `[fresh]`
- [1] TASK-2026-11-16-main-002 — 워크벤치 자동 기동 — session-start 가 띄우고 세션 종료 hook 이 내린다  `[fresh]`
- [2] TASK-2026-11-16-main-001 — 워크벤치 개방 모드 — 토큰 없이 IP 로 접속해 보고 답한다 (--open)  `[fresh]`
- [3] TASK-2026-11-15-main-002 — MCP 오류 신호 불일치 — summarize_git_history 가 git 아닌 경로에 ok, invoke_tool 이 status error 를 rc 0 으로  `[fresh]`
- [4] TASK-2026-11-15-main-001 — 경고 분류기가 /tmp · /var/tmp 경로를 정규화한 뒤 분류해 서드파티 경고를 저장소 경고로 오판한다  `[fresh]`
- [5] TASK-2026-11-15-claude-remote-sync-check-234c32-003 — 합류 반영이 완료 task 를 archived/ 로만 보내 main 집계가 근거를 잃는다 — 완료 task 도 모 브랜…  `[fresh]`
- [6] TASK-2026-11-15-claude-remote-sync-check-234c32-002 — v1.23.0 발행 — main 합류 · 발행 준비 · 태그 · GitHub Release  `[fresh]`
- [7] TASK-2026-11-15-claude-remote-sync-check-234c32-001 — MCP 도구 4종 성공 경로 output contract 미등록 수리 (main-002 대응, 발행 차단 결함)  `[fresh]`
- [8] TASK-2026-11-14-claude-remote-sync-check-234c32-003 — M-029 ② MCP plan_inbox · plan_import + 체크인 생성물  `[fresh]`
- [9] TASK-2026-11-14-claude-remote-sync-check-234c32-002 — M-029 ② 워크벤치 서버 · 화면 · 검사 넷 · 스킬 (MCP 두 도구는 다음 task)  `[fresh]`

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
- telemetry_events_total: `39`
- telemetry_total_queries: `39`
- telemetry_hit_count: `37`
- telemetry_hit_rate: `0.9487`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 33 |
| `session-start` | 6 |

