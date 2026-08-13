# Quality Dashboard Snapshot

- generated_at: `2026-08-13T05:27:52Z`
- tool_version: `v1.2.0-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-08-13`
- maturity_surface_changed_at: `2026-08-13`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-08-13`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 6건)

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

- entries_total: `9`
- entries_by_merge_state: `active`=9
- cue_anchors_unique: `53`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-08-10`

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

- cumulative_total: `252`
- cumulative_pass: `252`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `252`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.2.0 | 252 | 252 |
| Beta-v1.1.8 | 252 | 252 |
| Beta-v1.1.7 | 251 | 251 |
| Beta-v1.1.6 | 251 | 251 |
| Beta-v1.1.5 | 266 | 266 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-13-main-003 — 플러그인 SessionStart hook 조건부 규칙 주입 — 진입점 규칙 블록 감지 시 생략  `[fresh]`
- [1] TASK-2026-08-13-main-002 — bootstrap OpenCode MCP 방언이 현행 opencode 에서 거부됨 — command 배열/enabled/environment 로 갱신  `[fresh]`
- [2] TASK-2026-08-13-main-001 — 원본 저장소에서 bump 를 apply 하는 릴리스 검사를 sandbox 로 이관  `[fresh]`
- [3] TASK-2026-08-12-main-018 — 플러그인 전환 P5 — 실측 게이트 + 채널 전환 판정  `[fresh]`
- [4] TASK-2026-08-12-main-016 — 플러그인 전환 P3 — 멀티 하네스 어댑터 (gemini-cli/goose/opencode)  `[fresh]`
- [5] TASK-2026-08-12-main-020 — 플러그인 payload 에 session-end 스킬 추가 (스킬 3→4종)  `[fresh]`
- [6] TASK-2026-08-12-main-017 — 플러그인 전환 P4 — 릴리스 파이프라인 통합  `[fresh]`
- [7] TASK-2026-08-12-main-015 — 플러그인 전환 P2 — Claude Code 어댑터 + marketplace + 자기 적용  `[fresh]`
- [8] TASK-2026-08-12-main-014 — 플러그인 전환 P1 — 공유 payload 렌더러 (render_agent_plugin)  `[fresh]`
- [9] TASK-2026-08-12-main-013 — 플러그인 배포 전환 계획 수립 + 로드맵 갱신 + WBS  `[fresh]`

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
- entries_total: `9`
- telemetry_events_total: `892`
- telemetry_total_queries: `892`
- telemetry_hit_count: `447`
- telemetry_hit_rate: `0.5011`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 9 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 118 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 772 |

