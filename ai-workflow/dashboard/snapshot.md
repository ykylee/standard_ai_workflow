# Quality Dashboard Snapshot

- generated_at: `2026-09-22T02:30:34Z`
- tool_version: `1.10.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-22`
- maturity_surface_changed_at: `2026-09-22`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-22`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 19건)

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

- cumulative_total: `290`
- cumulative_pass: `290`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `290`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.10.0 | 290 | 290 |
| Beta-v1.9.4 | 284 | 284 |
| Beta-v1.9.3 | 282 | 282 |
| Beta-v1.9.2 | 280 | 280 |
| Beta-v1.9.1 | 280 | 280 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-21-main-009 — 하한 호환 축의 범위가 workflow-source/ 로 좁다 — git 추적 소스 8개가 그 밖에 있다  `[fresh]`
- [1] TASK-2026-09-21-main-008 — 경고 게이트가 두 구멍으로 눈이 먼다 — 부모 프로세스 경고 미수집(kit 44/196) + 판정이 __pycache__ 에 달려 1차 red → 2차 green  `[fresh]`
- [2] TASK-2026-09-21-main-007 — 해석기별로 갈리는 경고가 게이트 신호가 아니다 — SyntaxWarning 류는 exit 0 이라 4셀 전부 green 이었다  `[fresh]`
- [3] TASK-2026-09-21-main-006 — 검사를 CI 인터프리터로도 돌리는 축이 없다 — 로컬 3.13 / CI smoke 3.11 이라 검사 자신의 판정이 갈린다  `[fresh]`
- [4] TASK-2026-09-21-main-005 — 최소 Python 문법 호환을 재는 축이 없다 — 로컬 3.13 / 선언 하한 3.10 이라 CI 에서만 터지는 문법을 쓸 수 있다  `[fresh]`
- [5] TASK-2026-09-21-main-004 — smoke 수가 8곳에 손으로 복제돼 있고 게이트는 2곳만 덮는다 — 나머지는 162/52 로 갈라졌다  `[fresh]`
- [6] TASK-2026-09-21-main-003 — 검사가 강제하는 요구를 선언한다 — 산문 §인용 671건 중 661건은 기계가 어느 문서인지도 모른다 (OpenSpec concept 흡수)  `[fresh]`
- [7] TASK-2026-09-21-main-002 — check_wiki_trend 가 살아있는 저장소 점수에 rc==0 을 걸어 두었다 — lifecycle 0.42→0.00 으로 만성 red  `[fresh]`
- [8] TASK-2026-09-21-main-001 — graph_insights 판정식 재검토 — coverage 성분이 구조적으로 0 이고 classification 성분은 동음이의 잡음이다  `[fresh]`
- [9] TASK-2026-09-18-main-006 — doctor 의 content_drift 가 서빙되지 않는 사본을 재고 있다 — 마켓플레이스 소스 유형을 읽어야 한다  `[fresh]`

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
- telemetry_events_total: `2014`
- telemetry_total_queries: `2014`
- telemetry_hit_count: `700`
- telemetry_hit_rate: `0.3476`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 351 |
| `dispatcher` | 1 |
| `doc-sync` | 2 |
| `session-start` | 1660 |

