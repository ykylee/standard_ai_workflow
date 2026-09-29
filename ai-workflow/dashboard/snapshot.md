# Quality Dashboard Snapshot

- generated_at: `2026-09-29T02:21:59Z`
- tool_version: `1.14.1`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-29`
- maturity_surface_changed_at: `2026-09-29`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-29`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 24건)

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
| Beta-v1.14.1 | 296 | 296 |
| Beta-v1.14.0 | 296 | 296 |
| Beta-v1.13.0 | 296 | 296 |
| Beta-v1.12.0 | 296 | 296 |
| Beta-v1.11.0 | 292 | 292 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-29-main-002 — minimax-code 하네스 경로 대소문자 불일치로 session-start 가 매 세션 빈 bootstrap task 를 만든다 (GitHub #29)  `[fresh]`
- [1] TASK-2026-09-29-main-001 — backlog-update update 가 날짜 경계를 넘으면 새 daily index 에 kind 를 generic 으로 적는다  `[fresh]`
- [2] TASK-2026-09-28-main-021 — v1.14.0 발행 — antigravity MCP 도구 이름 수리 + doctor plugin_enabled 4채널  `[fresh]`
- [3] TASK-2026-09-28-main-020 — antigravity 에서 플러그인 MCP 도구 11개가 전부 거부된다 — 합성 도구 이름이 64자 제한 초과  `[fresh]`
- [4] TASK-2026-09-28-main-019 — wk doctor plugin_enabled 미실측 2건 실측 — grok 목록 부재 시 로드 · antigravity 워크스페이스 exclude  `[fresh]`
- [5] TASK-2026-09-28-main-018 — wk doctor plugin_enabled 절을 4채널로 — codex·grok-build·antigravity 의 활성 선언 자리 실측  `[fresh]`
- [6] TASK-2026-09-28-main-017 — wk doctor 가 claude-code 플러그인의 enabled 여부를 재지 않는다 — 설치됐는데 꺼진 상태(enabledPlugins 부재)를 못 잡아 스킬이 조…  `[fresh]`
- [7] TASK-2026-09-28-main-016 — v1.13.0 발행 — 은퇴 shim 제거 + check_self_application telemetry 오염 수리  `[fresh]`
- [8] TASK-2026-09-28-main-015 — v1.12.0 은퇴 shim 2종 제거 — verify_required_ci · REQUIRED_CI_WORKFLOWS (v1.13.0)  `[fresh]`
- [9] TASK-2026-09-28-main-014 — v1.12.0 발행 준비 — 삭제된 공개 API 에 deprecation shim 복원 + 버전 bump  `[fresh]`

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
- telemetry_events_total: `2955`
- telemetry_total_queries: `2955`
- telemetry_hit_count: `1203`
- telemetry_hit_rate: `0.4071`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 473 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2467 |

