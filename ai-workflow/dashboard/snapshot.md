# Quality Dashboard Snapshot

- generated_at: `2026-09-07T06:05:39Z`
- tool_version: `1.9.4`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-07`
- maturity_surface_changed_at: `2026-09-07`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-07`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 18건)

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

- cumulative_total: `284`
- cumulative_pass: `284`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `284`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.9.4 | 284 | 284 |
| Beta-v1.9.3 | 282 | 282 |
| Beta-v1.9.2 | 280 | 280 |
| Beta-v1.9.1 | 280 | 280 |
| Beta-v1.9.0 | 279 | 279 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-07-main-010 — graph_insights health 가 완료한 일이 늘수록 내려간다 — 100% 발화하는 scope creep 경고와 항등식을 재는 fixture  `[fresh]`
- [1] TASK-2026-09-07-main-008 — v1.9.3 발행 + 이 호스트 소비자 채널 재적용  `[fresh]`
- [2] TASK-2026-09-07-main-007 — 설치본에서 모듈 앵커가 증발해 브랜치 해석이 갈라진다 — 소비자 배포처의 모순 뿌리  `[fresh]`
- [3] TASK-2026-09-07-main-006 — task ID 채번이 로컬만 봐 같은 브랜치의 다른 호스트와 겹친다 — 코드가 거짓 보증을 적고 있다  `[fresh]`
- [4] TASK-2026-09-07-main-005 — INSTALLATION §7.0.2 grok 복구 열이 registry id 를 주는 것처럼 읽힌다  `[fresh]`
- [5] TASK-2026-09-07-main-004 — 발행 게이트가 태그된 노트를 현재 갯수와 재 왕복 편집을 되살린다 — 75차 수리의 사본 잔존  `[fresh]`
- [6] TASK-2026-09-07-main-003 — 체크인된 예제 state.json 을 생성기 출력과 대조하는 검사가 없다  `[fresh]`
- [7] TASK-2026-09-07-main-002 — 거짓말하는 cast 가 문자열을 목록으로 속여 environment_constraints 를 한 글자씩 쪼갠다  `[fresh]`
- [8] TASK-2026-09-07-main-001 — handoff 경로에 legacy fallback 이 없다 — 평평한 workspace 의 기준선이 조용히 사라진다  `[fresh]`
- [9] TASK-2026-09-04-main-002 — v1.9.2 소비 채널 재적용 — 이 호스트 전 채널 동기화  `[fresh]`

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
- telemetry_events_total: `1911`
- telemetry_total_queries: `1911`
- telemetry_hit_count: `167`
- telemetry_hit_rate: `0.0874`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 253 |
| `doc-sync` | 3 |
| `session-start` | 1655 |

