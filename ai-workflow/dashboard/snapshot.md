# Quality Dashboard Snapshot

- generated_at: `2026-09-30T03:11:37Z`
- tool_version: `1.15.0`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-09-30`
- maturity_surface_changed_at: `2026-09-29`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-09-30`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 28건)

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

- cumulative_total: `298`
- cumulative_pass: `298`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `298`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.15.0 | 298 | 298 |
| Beta-v1.14.4 | 296 | 296 |
| Beta-v1.14.3 | 296 | 296 |
| Beta-v1.14.2 | 296 | 296 |
| Beta-v1.14.1 | 296 | 296 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-09-30-main-006 — compact 중계 구현 — wk compact-checkpoint · hook 3종 · 스킬 compact-relay · 검사  `[fresh]`
- [1] TASK-2026-09-30-main-005 — compact 중계 design — ADR-030 + compact_relay_spec  `[fresh]`
- [2] TASK-2026-09-30-main-004 — compact 중계 requirements — 명령 계약 · checkpoint 형식 · 재주입 예산 · 누락 판정  `[fresh]`
- [3] TASK-2026-09-30-main-003 — compact 중계 concept 검토 — 하네스별 compact 표면 실측과 checkpoint 설계 선택지  `[fresh]`
- [4] TASK-2026-09-30-main-002 — python_floor 하한 해석기 호출을 stdin 으로 — Windows .CMD/.bat shim 에서 -c 다줄 스크립트가 첫 개행에서 잘린다 (main-013…  `[fresh]`
- [5] TASK-2026-09-29-main-018 — str(relative_to) 잔여 사이트 점검 — wk doctor 가 Windows 에서 정본 파일을 extra 로 오판  `[fresh]`
- [6] TASK-2026-09-29-main-017 — roadmap_state.json source_path 호스트 독립(POSIX) 고정  `[fresh]`
- [7] TASK-2026-09-29-main-016 — Codex 세션 내 wk 미인식 — editable 재설치 및 PATH 비교  `[fresh]`
- [8] TASK-2026-09-29-main-015 — Windows 환경 워크플로우 editable 설치 및 emit/doctor 이슈 재현  `[fresh]`
- [9] TASK-2026-09-29-main-014 — v1.14.4 발행 — Windows doctor MCP 탐침 shim 절단 + wiki 스탬프 판정 수리  `[fresh]`

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
- telemetry_events_total: `3000`
- telemetry_total_queries: `3000`
- telemetry_hit_count: `1244`
- telemetry_hit_rate: `0.4147`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 30 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 511 |
| `dispatcher` | 13 |
| `doc-sync` | 2 |
| `session-start` | 2474 |

