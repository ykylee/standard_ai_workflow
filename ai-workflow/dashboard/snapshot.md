# Quality Dashboard Snapshot

- generated_at: `2026-09-02T22:52:29Z`
- tool_version: `1.9.1`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-02`
- maturity_surface_changed_at: `2026-09-03`
- maturity_stale: `True` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-03`
- last_updated_delta_days: `1`
- silent_failing_cycles_count: `0` (측정 cycle 15건)

> ⚠️ **maturity 선언이 surface 보다 뒤처짐** (surface `2026-09-03` > 선언 `2026-09-02`): refresh hint → `python3 -c "from workflow_kit.common.state.cache import refresh_maturity_last_updated; from pathlib import Path; print(refresh_maturity_last_updated(Path('workflow-source/core/maturity_matrix.json')))"`

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

- cumulative_total: `280`
- cumulative_pass: `280`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `280`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.9.1 | 280 | 280 |
| Beta-v1.9.0 | 279 | 279 |
| Beta-v1.8.1 | 277 | 277 |
| Beta-v1.8.0 | 276 | 276 |
| Beta-v1.7.0 | 276 | 276 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-02-main-002 — session-start 의 상태 불일치 경고가 handoff 를 하루치 backlog 와 비교해 영구 오탐이다  `[fresh]`
- [1] TASK-2026-09-02-main-001 — v1.9.0 발행 — 필수 CI 게이트 + done 강등 보존  `[fresh]`
- [2] TASK-2026-09-01-main-005 — 발행 게이트가 CI 워크플로 9개 중 1개만 보고 그마저 advisory — v1.8.0 이 smoke red 위에서 나갔다  `[fresh]`
- [3] TASK-2026-09-01-main-004 — check_deploy_doctor 가 macOS 전용 경로를 박아 CI smoke 가 10 커밋 연속 red — v1.8.0 이 그 위에서 발행됐다  `[fresh]`
- [4] TASK-2026-09-01-main-003 — done 강등이 handoff 를 되돌리는데 최상위 status 는 ok — 강등이 이미 기록된 완료를 취소한다  `[fresh]`
- [5] TASK-2026-09-01-main-002 — 인덱스 검사의 EXPECTED_LAST_UPDATED 가 하드코딩 — 발행마다 손이 간다  `[fresh]`
- [6] TASK-2026-09-01-main-001 — workflow_kit.cli 가 휠에 실리지 않는다 — 손 목록이 빠뜨린 세 번째 하위 패키지  `[fresh]`
- [7] TASK-2026-08-31-main-005 — v1.8.0 발행 — 지원 하네스 개편 + 탐침 침묵 제거 사이클  `[fresh]`
- [8] TASK-2026-08-31-main-004 — codex marketplace source 가 휘발 경로를 가리켜도 탐침이 침묵한다 — 사본과 경유지는 따로 깨진다  `[fresh]`
- [9] TASK-2026-08-31-main-003 — backlog-update update 가 열거 필드를 교체해 이전 세션 기록을 지운다 — 손실에 경고가 없다  `[fresh]`

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
- telemetry_events_total: `1601`
- telemetry_total_queries: `1601`
- telemetry_hit_count: `151`
- telemetry_hit_rate: `0.0943`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 224 |
| `doc-sync` | 2 |
| `session-start` | 1375 |

