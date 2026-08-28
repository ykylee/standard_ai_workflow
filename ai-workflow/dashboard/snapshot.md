# Quality Dashboard Snapshot

- generated_at: `2026-08-28T09:30:10Z`
- tool_version: `1.7.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-28`
- maturity_surface_changed_at: `2026-08-25`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-28`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 11건)

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

- cumulative_total: `275`
- cumulative_pass: `275`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `275`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.7.0 | 275 | 275 |
| Beta-v1.6.0 | 275 | 275 |
| Beta-v1.5.0 | 274 | 274 |
| Beta-v1.4.0 | 274 | 274 |
| Beta-v1.3.0 | 267 | 267 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-28-main-009 — mcp 2.1.1 이 fastmcp 모듈을 되살리되 FastMCP 심볼만 제거 — CI mypy-strict 3연속 red (로컬 1.27 은 green)  `[fresh]`
- [1] TASK-2026-08-28-main-008 — M-011/WBS-11.1 — meta-watch 구현: 러너 채취 주입·판정 + WATCHES_ALL_REASON 어휘 + 선언 교정 7건  `[fresh]`
- [2] TASK-2026-08-28-main-007 — M-010/WBS-10.2 — core 스펙 절 작성: 분류·계층 계약의 kit 표준화 (test_impact_tiering_spec)  `[fresh]`
- [3] TASK-2026-08-28-main-006 — M-010/WBS-10.1 — ADR-028 작성: 메타 검증 채취 방식 실측 비교 + 전역 선언 리터럴 + 전수/순환 기준  `[fresh]`
- [4] TASK-2026-08-28-main-005 — M-009/WBS-9.1 — 계층별 회귀 실행 계약 requirements 확정 (보급 판정 기준·메타 검증 요구사항·이득 실측)  `[fresh]`
- [5] TASK-2026-08-28-main-004 — M-008/WBS-8.1 — 계층별 회귀 실행 계약 concept 검토 (검사 입력 표면 선언 기반 선택 실행)  `[fresh]`
- [6] TASK-2026-08-28-main-002 — backlog-update update 모드가 --wbs 를 무시한다 — 기존 task 의 WBS 재링크 수단 부재  `[fresh]`
- [7] TASK-2026-08-28-main-001 — 운영 축 상설 마일스톤 M-007 선언 — exempt 상시화 흡수  `[fresh]`
- [8] TASK-2026-08-25-main-023 — suggest-memory-entries 기본 경로가 자기 설치 디렉터리 기준 — uv tool 실행 시 handoff 부재로 즉시 실패  `[fresh]`
- [9] TASK-2026-08-25-main-022 — release-status local_mypy 탐침이 자기 인터프리터를 잰다 — uv tool venv 에 mypy 가 없어 상시 오탐 FAIL  `[fresh]`

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
- telemetry_events_total: `1045`
- telemetry_total_queries: `1045`
- telemetry_hit_count: `110`
- telemetry_hit_rate: `0.1053`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 161 |
| `doc-sync` | 1 |
| `session-start` | 883 |

