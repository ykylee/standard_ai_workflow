# Quality Dashboard Snapshot

- generated_at: `2026-07-17T14:41:42Z`
- tool_version: `v0.15.0-beta`
- workspace_root: `.`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-07-17`
- maturity_stale: `False`
- harness_supported_count: `10`
- head_commit_date: `2026-07-17`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0`

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
| total | 12 |
| done | 11 |
| in_progress | 1 |
| planned | 0 |

### harnesses

- supported: `10`
- names: `codex`, `opencode`, `gemini-cli`, `antigravity`, `minimax-code`, `claude-code`, `aider`, `goose`, `pi-dev`, `codewhale`

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

- cumulative_total: `260`
- cumulative_pass: `260`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `187`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v0.15.0 | 260 | 260 |
| Beta-v0.14.7 | 260 | 260 |
| Beta-v0.14.6 | 260 | 260 |
| Beta-v0.14.5 | 260 | 260 |
| Beta-v0.14.3 | 260 | 260 |

## Panel 5 — Recent Release Cycle

- items_total: `20`
- top_n: `10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-07-17-009 — v0.15.9 — **SemVer patch, Harness verification smoke — 10 harness cross-check discipline anchor**.…
- [1] TASK-2026-07-17-008 — v0.15.8 — **SemVer patch, Panel 1+2 maturity_distribution cross-validation smoke — v1.0.0 진입 평가의 c…
- [2] TASK-2026-07-17-007 — v0.15.7 — **SemVer patch, Panel 3 memory_index cross-validation smoke — Phase 13 AC2 retrieval cro…
- [3] TASK-2026-07-17-006 — v0.15.6 — **SemVer patch, Panel 6/8 telemetry cross-validation smoke — Phase 15 cross-check discip…
- [4] TASK-2026-07-17-005 — v0.15.5 — **SemVer patch, Panel 4 cross-validation smoke — v0.15.x follow-up 의 cross-check discipl…
- [5] TASK-2026-07-17-004 — v0.15.4 — **SemVer patch, ADR-007 close-out — 3rd deprecation cycle accepted no-op**. ADR-007 plac…
- [6] TASK-2026-07-17-003 — v0.15.3 — **SemVer patch, v0.14.6 out-of-scope 2 해소 — release_error 시에만 maturity refresh**. maturi…
- [7] TASK-2026-07-17-002 — v0.15.2 — **SemVer patch, v0.14.6 out-of-scope 1 해소 — legacy_memory strict opt-out 정렬**. maturity_…
- [8] TASK-2026-07-17-001 — v0.15.1 — **SemVer patch, dashboard 정합 + Panel 4 SMOKE_COUNT_PATTERN 확장**. v0.15.0 ⚠️ BREAKING pus…
- [9] TASK-2026-07-16-001 — v0.15.0 — **⚠️ SemVer minor, BREAKING — 2nd deprecation cycle 종결 (work_backlog.md.bak drop) + push…

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
- telemetry_events_total: `1`
- telemetry_total_queries: `1`
- telemetry_hit_count: `1`
- telemetry_hit_rate: `1.0000`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 7 |

### Telemetry by source

| source | events |
|---|---|
| `dispatcher` | 1 |

