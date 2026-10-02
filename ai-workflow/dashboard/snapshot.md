# Quality Dashboard Snapshot

- generated_at: `2026-10-02T03:02:12Z`
- tool_version: `1.18.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-10-02`
- maturity_surface_changed_at: `2026-10-02`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-10-02`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 31건)

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

- cumulative_total: `300`
- cumulative_pass: `300`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `300`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.18.0 | 300 | 300 |
| Beta-v1.17.0 | 299 | 299 |
| Beta-v1.16.0 | 298 | 298 |
| Beta-v1.15.0 | 298 | 298 |
| Beta-v1.14.4 | 296 | 296 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-10-02-main-004 — worktree 합류 반영 — 모 브랜치에 병합된 브랜치 메모리를 모 브랜치 메모리에 기록하고 아카이브  `[fresh]`
- [1] TASK-2026-10-02-main-002 — v1.17.0 발행 — worktree 모 브랜치 이어받기 + worktree 자동 seed · meta-watch · 템플릿 검사 수리  `[fresh]`
- [2] TASK-2026-10-02-main-001 — worktree seed 가 모 브랜치 내용을 이어받는다 — 기준선 · 다음 시작 포인트 · 열린 task 복사 + 원류 기록 + 합류 시 되돌려 적기  `[fresh]`
- [3] TASK-2026-09-30-main-014 — macOS Codex v1.16.0 적용·신뢰·재시작·compact 왕복 검증  `[fresh]`
- [4] TASK-2026-09-30-main-013 — meta-watch 좁은 선언이 worktree 중첩 경로를 덮지 못해 게이트가 구조적으로 red 다  `[fresh]`
- [5] TASK-2026-09-30-main-012 — 로드맵 WBS 링크 수집기가 슬래시 포함 브랜치(task 가 2단계 깊이)에 닿지 않는다  `[fresh]`
- [6] TASK-2026-09-30-main-011 — v1.16.0 발행 — Codex compact 중계 hook 탑재 + 출력 수리 (codex-json)  `[fresh]`
- [7] TASK-2026-09-30-main-010 — Codex compact 중계 hook 출력 형식 수리 — [ 머리말이 JSON 으로 오판돼 hook failed · 재주입 0  `[fresh]`
- [8] TASK-2026-09-30-main-009 — Codex 인증 압축 왕복 실측 — PostCompact · SessionStart(compact) 발화와 순서  `[fresh]`
- [9] TASK-2026-09-30-main-008 — Codex 플러그인 hook 적재 — compact 중계 기록·재주입을 Codex 에서  `[fresh]`

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
- telemetry_events_total: `3026`
- telemetry_total_queries: `3026`
- telemetry_hit_count: `1269`
- telemetry_hit_rate: `0.4194`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 532 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2479 |

