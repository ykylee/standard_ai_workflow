# Quality Dashboard Snapshot

- generated_at: `2026-11-16T15:18:07Z`
- tool_version: `1.26.0`
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
- silent_failing_cycles_count: `0` (측정 cycle 40건)

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

- cumulative_total: `329`
- cumulative_pass: `329`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `329`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.26.0 | 329 | 329 |
| Beta-v1.25.0 | 325 | 325 |
| Beta-v1.24.0 | 322 | 322 |
| Beta-v1.23.0 | 319 | 319 |
| Beta-v1.22.0 | 309 | 309 |

## Panel 5 — Recent Release Cycle

- items_total: `20`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-16-main-014 — 워크벤치 응답이 작업 세션에 바로 닿지 않는다 — 도착 신호 + hook 자동 반영 · 알림  `[fresh]`
- [1] TASK-2026-11-16-main-013 — 워크벤치 글자가 박스를 넘는다 — 긴 글 · 좁은 폭 · 다른 글꼴에서도 박스 안에  `[fresh]`
- [2] TASK-2026-11-16-main-012 — 대시보드 inline_guard=False 가 가드를 돌리지 않고 guard_cases 7 · pass 0 을 실측처럼 싣는다  `[fresh]`
- [3] TASK-2026-11-16-main-011 — release self_recover 재검사 집계가 cases_pass 7 > cases_total 6 — drift 가드 case 수를 6 으로 박아 둔 사본  `[fresh]`
- [4] TASK-2026-11-16-main-010 — v1.25.0 발행 — 워크벤치 지속 갱신(자동 새로고침 · 실시간 값 · 진행 기록) + 수리 둘  `[fresh]`
- [5] TASK-2026-11-16-main-009 — 작업 중 진행 상황 기록 — 단계마다 Progress 한 줄, 워크벤치가 '지금 하는 일'로 보인다  `[fresh]`
- [6] TASK-2026-11-16-main-008 — 워크벤치 진척이 생성물(state.json · roadmap_state.json)을 기다린다 — 원천에서 같은 생성기로 실시간 계산  `[fresh]`
- [7] TASK-2026-11-16-main-007 — 워크벤치 폼 POST 가 실제 브라우저에서 Origin null 로 403 — Referrer-Policy no-referrer  `[fresh]`
- [8] TASK-2026-11-16-main-006 — 워크벤치 화면 자동 새로고침 — 바뀐 내용만 다시 그리고 답 쓰는 중이면 알림만  `[fresh]`
- [9] TASK-2026-11-16-main-005 — workbench --stop 이 기록의 pid 가 그 포트의 주인인지 대조하지 않는다 — 인스턴스 표식 대조  `[fresh]`

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
- telemetry_events_total: `75`
- telemetry_total_queries: `75`
- telemetry_hit_count: `73`
- telemetry_hit_rate: `0.9733`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 66 |
| `session-start` | 9 |

