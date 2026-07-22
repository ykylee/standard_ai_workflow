# Quality Dashboard Snapshot

- generated_at: `2026-07-22T01:36:25Z`
- tool_version: `v1.0.0-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-07-21`
- maturity_stale: `True`
- harness_supported_count: `11`
- head_commit_date: `2026-07-22`
- last_updated_delta_days: `1`
- silent_failing_cycles_count: `1`

> ⚠️ **maturity_last_updated stale**: refresh hint → `python3 -c "python3 -c "from workflow_kit.common.state.cache import refresh_maturity_last_updated; from pathlib import Path; print(refresh_maturity_last_updated(Path('workflow-source/core/maturity_matrix.json')))""`

## Panel 2 — Maturity Distribution

### skills

| metric | value |
|---|---|
| total | 12 |
| stable | 12 |
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
- names: `codex`, `opencode`, `gemini-cli`, `antigravity`, `minimax-code`, `claude-code`, `aider`, `goose`, `grok-build`, `pi-dev`, `codewhale`

## Panel 3 — Memory Index Utilization

- entries_total: `7`
- entries_by_merge_state: `active`=7
- cue_anchors_unique: `40`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-07-09`

### Top cue anchors

| anchor | count |
|---|---|
| P0 | 2 |
| audit | 1 |
| workflow | 1 |
| 2026-07-09 | 1 |
| candidates | 1 |
| snapshot | 1 |
| P1 | 1 |
| P2 | 1 |
| ADR-005 | 1 |
| memory-index | 1 |

## Panel 4 — Smoke Trend

- cumulative_total: `199`
- cumulative_pass: `188`
- cumulative_pass_rate: `0.9447`
- smoke_files_count: `199`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.0.0 | 188 | 199 |
| Beta-v0.15.19 | 24 | 24 |

## Panel 5 — Recent Release Cycle

- items_total: `11`
- top_n: `10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-07-21-001 — v0.15.21 — **SemVer patch, Phase 13 follow-up 1차 — AC2 telemetry 다양성 + CHANGELOG auto-gen lockdown…
- [1] TASK-2026-07-02-001 — v0.11.21 — **SemVer patch, 3차 batch robust-patcher stable 승격**. v0.11.20 (2차 batch 4 skill stable)…
- [2] TASK-2026-07-09-001 — v0.13.3 — **SemVer patch, Phase 13 AC4+ (self-documenting wiki ↔ memory bidirectional link) close-…
- [3] TASK-2026-07-09-002 — v0.13.2 — **SemVer patch, Phase 13 AC3 (self-recovering) close-out**. drift prevention 의 6 case 가 …
- [4] TASK-2026-07-09-003 — v0.13.1 — **SemVer patch, Phase 13 AC2 (memory_index 활용도) close-out**. v0.13.0 Quality Dashboard 의…
- [5] TASK-2026-07-20-001 — v0.15.16 — **SemVer patch, Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확…
- [6] Phase 10 MCP/JSON-RPC draft
- [7] Phase 6 multi-agent delegation pilot
- [8] workflow 종료 단계 commit/memory 순서 정정 (commit `32185c7`) — 협업 결함 (push 시 memory 갱신 누락 / 추가 commit 유발) 해결. 11 file 변경: `work…
- [9] 워크플로우 구성 점검 + 고도화 후보 10건 도출 (audit-session, no release). 현 상태 v0.11.22-beta 스냅샷 (Phase 12 in_progress, skill stable=9 / …

## Panel 6 — Multi-Agent Concurrent Write Conflict

- north_star: `multi_agent_concurrent_write_conflict_count`
- conflict_count: `0`
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

- phase_15_north_star: `telemetry_hit_rate (1 release ≥ 1 query + hit)`
- entries_total: `7`
- telemetry_events_total: `4`
- telemetry_total_queries: `4`
- telemetry_hit_count: `4`
- telemetry_hit_rate: `1.0000`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 7 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 1 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 1 |

