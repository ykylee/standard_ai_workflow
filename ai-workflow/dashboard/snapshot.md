# Quality Dashboard Snapshot

- generated_at: `2026-10-06T01:27:19Z`
- tool_version: `1.20.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-10-06`
- maturity_surface_changed_at: `2026-10-02`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-10-06`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 33건)

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

- cumulative_total: `309`
- cumulative_pass: `309`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `309`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.20.0 | 309 | 309 |
| Beta-v1.19.0 | 302 | 302 |
| Beta-v1.18.0 | 300 | 300 |
| Beta-v1.17.0 | 299 | 299 |
| Beta-v1.16.0 | 298 | 298 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-10-06-main-004 — [진입점 다이어트 3] 기존 진입점 다이어트 단계 — 채택 프로젝트의 진입점을 예산 · 현행 템플릿과 대조해 보고/정리  `[fresh]`
- [1] TASK-2026-10-06-main-003 — [진입점 다이어트 2] bootstrap 생성 진입점 템플릿 다이어트 + 하네스별 진입점 바이트 예산 검사  `[fresh]`
- [2] TASK-2026-10-06-main-002 — [진입점 다이어트 1] 정본 생성 규칙 블록(§1 · §8 · §11) 압축 — 모든 진입점 · 스킬 공통 3.6KB  `[fresh]`
- [3] TASK-2026-10-06-main-001 — CLAUDE.md 다이어트 — 12,184B 중 고칠 수 있는 8.5KB 를 걷는다 (생성 규칙 블록 3.6KB 는 그대로)  `[fresh]`
- [4] TASK-2026-10-05-main-004 — [A3] 검사 약화 차단 가드 hook — --no-verify push · --no-lock 전량 · gate_evidence 직접 쓰기를 이유와 함께 막는다  `[fresh]`
- [5] TASK-2026-10-05-main-002 — [A1] 작업 전 계획을 task 파일 Plan 절로 남긴다 — 바뀌는 파일 · 작업 순서 · 위험 · 검증 방법  `[fresh]`
- [6] TASK-2026-10-05-main-001 — Anthropic 'The AI-native SDLC playbook' 조사·정리 + 워크플로우 적용 검토  `[fresh]`
- [7] TASK-2026-10-02-main-008 — v1.19.0 발행 — Windows: cp949 stdio/텍스트 I/O UTF-8 고정 + 하네스 호출 python -m workflow_kit 전환  `[fresh]`
- [8] TASK-2026-10-02-main-005 — v1.18.0 발행 — worktree 합류 반영 (병합된 브랜치 메모리를 모 브랜치 메모리에 기록)  `[fresh]`
- [9] TASK-2026-10-02-main-004 — worktree 합류 반영 — 모 브랜치에 병합된 브랜치 메모리를 모 브랜치 메모리에 기록하고 아카이브  `[fresh]`

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
- telemetry_events_total: `3061`
- telemetry_total_queries: `3061`
- telemetry_hit_count: `1302`
- telemetry_hit_rate: `0.4254`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 559 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2487 |

