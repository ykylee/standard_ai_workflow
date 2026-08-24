# Quality Dashboard Snapshot

- generated_at: `2026-08-24T03:49:56Z`
- tool_version: `1.4.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-24`
- maturity_surface_changed_at: `2026-08-20`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-24`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 8건)

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

- entries_total: `13`
- entries_by_merge_state: `active`=13
- cue_anchors_unique: `85`
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

- cumulative_total: `267`
- cumulative_pass: `267`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `267`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.4.0 | 267 | 267 |
| Beta-v1.3.0 | 267 | 267 |
| Beta-v1.2.0 | 264 | 264 |
| Beta-v1.1.8 | 252 | 252 |
| Beta-v1.1.7 | 251 | 251 |

## Panel 5 — Recent Release Cycle

- items_total: `11`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-24-main-004 — 레거시 task 본문 라벨 마이그레이션 — 손이 아니라 도구로, 파싱 동일성을 잠금장치로  `[fresh]`
- [1] TASK-2026-08-24-main-003 — bootstrap 이 v0.14.0 이전 daily 템플릿을 낸다 — 새 프로젝트가 첫날부터 혼재한다  `[fresh]`
- [2] TASK-2026-08-24-main-002 — 혼합 표기 결정 재료 — 실측으로 질문을 다시 세웠다  `[fresh]`
- [3] TASK-2026-08-24-main-001 — watch_transient_writer flake — 이벤트 1건이 '내 주입 완결본' 을 뜻하지 않는다  `[fresh]`
- [4] TASK-2026-08-22-main-001 — handoff §5 를 부류별로 가른다 — 산문이 SSOT 를 복제해 갈라지던 자리  `[fresh]`
- [5] TASK-2026-08-20-main-017 — consumer-metrics-digest 가 없는 경로를 부른다 — 옮긴 파일을 워크플로가 못 따라왔다  `[fresh]`
- [6] TASK-2026-08-20-main-016 — okf-validate 가 okf_version 0.1 을 리터럴로 박고 있다 — 그물의 파일 형식 경계  `[fresh]`
- [7] TASK-2026-08-20-main-015 — 포크 후속 — CLAUDE.md 가 놓친 kit 변경을 골라 병합한다  `[fresh]`
- [8] TASK-2026-08-20-main-014 — planned task 가 state.json 에 안 보인다 — main-018 이 6일째 잊혀 있었다  `[fresh]`
- [9] TASK-2026-08-20-main-013 — CLAUDE.md 생성기가 session-end 를 광고 안 한다 — 같은 어긋남의 네 번째 자리  `[fresh]`

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
- entries_total: `13`
- telemetry_events_total: `550`
- telemetry_total_queries: `550`
- telemetry_hit_count: `66`
- telemetry_hit_rate: `0.1200`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 13 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 79 |
| `session-start` | 471 |

