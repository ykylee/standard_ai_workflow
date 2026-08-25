# Quality Dashboard Snapshot

- generated_at: `2026-08-25T06:18:34Z`
- tool_version: `1.6.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-25`
- maturity_surface_changed_at: `2026-08-25`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-25`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 10건)

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

- cumulative_total: `274`
- cumulative_pass: `274`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `274`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.6.0 | 274 | 274 |
| Beta-v1.5.0 | 274 | 274 |
| Beta-v1.4.0 | 274 | 274 |
| Beta-v1.3.0 | 267 | 267 |
| Beta-v1.2.0 | 264 | 264 |

## Panel 5 — Recent Release Cycle

- items_total: `11`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-25-main-020 — state generator 가 Windows 호스트에서 백슬래시 경로를 쓴다 — safe_relpath 에 POSIX 정규화가 없다  `[fresh]`
- [1] TASK-2026-08-25-main-019 — 전역 도구가 다른 체크아웃의 workflow_kit 을 해결한다 — 이 저장소 대신 semcowork 사본이 실행된다  `[fresh]`
- [2] TASK-2026-08-25-main-018 — emit PYTHONPATH 가 source-checkout 모드에서만 실재 — 순수 신규 프로젝트에서 실재하지 않는 디렉터리를 가리킨다  `[fresh]`
- [3] TASK-2026-08-25-main-016 — roadmap M-006/WBS-6.3 — 로드맵 상시 운용 전환 + exempt 비율 관찰 시작  `[fresh]`
- [4] TASK-2026-08-25-main-015 — roadmap M-006/WBS-6.2 — 소비 채널 재적용 + doctor drift 0  `[fresh]`
- [5] TASK-2026-08-25-main-014 — roadmap M-006/WBS-6.1 — 릴리스 발행 (등급은 RELEASE.md §1.5)  `[fresh]`
- [6] TASK-2026-08-25-main-013 — roadmap M-005/WBS-5.3 — 채널 스킬 문안이 로드맵 게이트·컨텍스트를 안내한다  `[fresh]`
- [7] TASK-2026-08-25-main-012 — roadmap M-005/WBS-5.2 — 기존 프로젝트 온보딩은 draft 로드맵 초안을 받는다  `[fresh]`
- [8] TASK-2026-08-25-main-011 — roadmap M-005/WBS-5.1 — 신규 프로젝트 bootstrap 이 SDLC 로드맵 씨앗을 심는다  `[fresh]`
- [9] TASK-2026-08-25-main-010 — 이 저장소 claude-code 채널 플러그인 단일화 — 프로젝트 레벨 개별 스킬 5종 제거  `[fresh]`

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
- telemetry_events_total: `835`
- telemetry_total_queries: `835`
- telemetry_hit_count: `95`
- telemetry_hit_rate: `0.1138`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 134 |
| `doc-sync` | 1 |
| `session-start` | 700 |

