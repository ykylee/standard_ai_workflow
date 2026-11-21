# Quality Dashboard Snapshot

- generated_at: `2026-11-21T22:52:51Z`
- tool_version: `1.30.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow-1x`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-11-21`
- maturity_surface_changed_at: `2026-11-21`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-11-21`
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

- cumulative_total: `336`
- cumulative_pass: `336`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `336`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.30.0 | 336 | 336 |
| Beta-v1.29.1 | 333 | 333 |
| Beta-v1.29.0 | 333 | 333 |
| Beta-v1.28.0 | 332 | 332 |
| Beta-v1.27.0 | 332 | 332 |

## Panel 5 — Recent Release Cycle

- items_total: `24`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-11-21-main-025 — 2.0 줄에서 kit 플러그인 채널 내리기 — marketplace.json · 발행 zip (R16.6 · Q10, M-040 WBS-40.2)  `[fresh]`
- [1] TASK-2026-11-21-main-024 — 2.0.0-beta 발행 범위 확정 · 허브 운영 가이드 (M-040 WBS-40.1)  `[fresh]`
- [2] TASK-2026-11-21-main-023 — /setup.md 가이드 실측 — Codex · MiniMax Code · Antigravity (Linux, 빈 폴더) (M-039 WBS-39.1)  `[fresh]`
- [3] TASK-2026-11-21-main-022 — 허브 에이전트용 셋업 가이드 /setup.md — 페이지만 읽고 스스로 부트스트랩 + 원격 없는 저장소 등록 (M-039 WBS-39.1)  `[fresh]`
- [4] TASK-2026-11-21-main-021 — 이 저장소를 테스트베드 허브에 실제 등록 — 등록 · 셋업 · 들여오기, 표식 보류 (M-039 WBS-39.2)  `[fresh]`
- [5] TASK-2026-11-21-main-020 — 이 호스트 테스트베드 허브 — 이 저장소 clone 을 2.0 으로 전환해 실사용 시험 (M-039 WBS-39.2)  `[fresh]`
- [6] TASK-2026-11-21-main-019 — run_all_checks 잠금 파일 보유자 정보가 깨진다 — a+b 모드에서 seek 가 쓰기 위치를 못 바꿈  `[fresh]`
- [7] TASK-2026-11-21-main-018 — 허브 서버 간 프로젝트 이전 — HTTP 경로 (같은 묶음, 소유자 2026-11-21 '둘 다')  `[fresh]`
- [8] TASK-2026-11-21-main-017 — 허브 서버 간 프로젝트 이전 — 묶음 · 관리자 CLI export/import · 원본 봉인 (M-039 WBS-39.4)  `[fresh]`
- [9] TASK-2026-11-21-main-016 — 1.x 전환 범위 확장 — 아카이브 브랜치 · 결정 응답 · baselines · PURPOSE/PROFILE · 날짜별 backlog (소유자 2026-11-21)  `[fresh]`

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
- telemetry_events_total: `9`
- telemetry_total_queries: `9`
- telemetry_hit_count: `9`
- telemetry_hit_rate: `1.0000`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 8 |
| `session-start` | 1 |

