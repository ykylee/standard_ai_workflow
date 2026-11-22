# Quality Dashboard Snapshot

- generated_at: `2026-11-22T08:24:37Z`
- tool_version: `2.1.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-22`
- maturity_surface_changed_at: `2026-11-21`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-22`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 45건)

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

- cumulative_total: `350`
- cumulative_pass: `350`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `350`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v2.1.0 | 350 | 350 |
| Beta-v2.0.0 | 346 | 346 |
| Beta-v1.29.0 | 333 | 333 |
| Beta-v1.28.0 | 332 | 332 |
| Beta-v1.27.0 | 332 | 332 |

## Panel 5 — Recent Release Cycle

- items_total: `28`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-22-main-020 — SDK · 해석기 매트릭스의 기본 임시 폴더가 저장소 안이라 git 밖 fixture 가 이 저장소 하위가 된다 — 매트릭스 위양성  `[fresh]`
- [1] TASK-2026-11-22-main-018 — 저장소 README 재작성 — 2.0 허브 · 2.1 오케스트레이션 구성 · 아키텍처 · 시스템 구성도  `[fresh]`
- [2] TASK-2026-11-22-main-017 — 2.1 진입 지침 세션 끝 — 샌드박스로 push 못 하는 일하는 세션은 우회 없이 보고 (M-048 WBS-48.2)  `[fresh]`
- [3] TASK-2026-11-22-main-016 — VS Code 확장 실제 로드 실측 — 활성화 · 명령 · webview 안 중계 화면 · 상태 표시줄 · .vsix 패키징 (M-048 WBS-48.1)  `[fresh]`
- [4] TASK-2026-11-22-main-015 — VS Code 확장 껍데기 — 중계 화면 webview · 상태 표시줄 · 프레임 정책 · 게이트 검사 (M-047 WBS-47.1)  `[fresh]`
- [5] TASK-2026-11-22-main-014 — Codex 일하는 세션이 workspace-write 샌드박스에서 .git 이 읽기 전용이라 커밋 · push 를 못 한다 — 중계 세션의 커밋 경로  `[fresh]`
- [6] TASK-2026-11-22-main-013 — PC 중계 실제 어댑터 실측 — Claude Code · Codex 세션 띄우기 · 배정 전달 · 수락/보고 · 멈춤 (M-046 WBS-46.3)  `[fresh]`
- [7] TASK-2026-11-22-main-012 — 로드맵 형식 위반(WBS 제목 200자 초과 등)이 session-start · refresh-state 를 런타임 오류로 죽인다  `[fresh]`
- [8] TASK-2026-11-22-main-011 — PC 중계 — 허브 쪽 API · 중계 패키지 · 어댑터 · 게이트 검사 (M-046 WBS-46.1 · 46.2)  `[fresh]`
- [9] TASK-2026-11-22-main-010 — 허브 오케스트레이션 구현 2 — 오케스트레이터 lease · 배정 상태 기계 · 보고 · 정지 · 진입 규칙 (M-045 WBS-45.1)  `[fresh]`

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
- telemetry_events_total: `3497`
- telemetry_total_queries: `3497`
- telemetry_hit_count: `1722`
- telemetry_hit_rate: `0.4924`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 940 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2542 |

