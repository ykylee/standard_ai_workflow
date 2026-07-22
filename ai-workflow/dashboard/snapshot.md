# Quality Dashboard Snapshot

- generated_at: `2026-07-22T14:28:05Z`
- tool_version: `v1.0.0-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-07-22`
- maturity_surface_changed_at: `2026-07-22`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `11`
- head_commit_date: `2026-07-22`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `미측정` (원장 `ai-workflow/memory/release/drift_ledger.jsonl` 에 cycle 0건)

## Panel 2 — Maturity Distribution

### skills

| metric | value |
|---|---|
| total | 14 |
| stable | 13 |
| beta | 1 |
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

- cumulative_total: `207`
- cumulative_pass: `207`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `208`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.0.0 | 207 | 207 |
| Beta-v0.15.19 | 24 | 24 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-07-09-003 — v0.13.1 — **SemVer patch, Phase 13 AC2 (memory_index 활용도) close-out**. v0.13.0 Quality Dashboard 의…
- [1] TASK-2026-07-20-001 — v0.15.16 — **SemVer patch, Grok Build (xAI CLI TUI) 11번째 harness + cross-check discipline anchor 확…
- [2] TASK-2026-07-21-001 — v0.15.21 — **SemVer patch, Phase 13 follow-up 1차 (AC2 telemetry 다양성 + CHANGELOG auto-gen lockdown)…
- [3] TASK-2026-07-22-001 — v1.0.0-beta — **major, v1.0.0 진입 릴리스 발행**. entry gate 6/6 PASS + 전량 smoke 199/199 PASS 로 tag `v1.0…
- [4] TASK-2026-07-22-002 — **v1.0.0 발행 후 보강 — "지표가 무엇을 재고 있는가" 3층 점검** (노트 §2.15~§2.20). 릴리스 후 발견/보강 6건: (1) §2.15 auto-bump …
- [5] Phase 10 MCP/JSON-RPC draft
- [6] Phase 6 multi-agent delegation pilot
- [7] workflow 종료 단계 commit/memory 순서 정정 (commit `32185c7`) — 협업 결함 (push 시 memory 갱신 누락 / 추가 commit 유발) 해결. 11 file 변경: `work…
- [8] 워크플로우 구성 점검 + 고도화 후보 10건 도출 (audit-session, no release). 현 상태 v0.11.22-beta 스냅샷 (Phase 12 in_progress, skill stable=9 / …
- [9] 2026-07-09 audit-session 의 고도화 후보 10건 일괄 해소 (audit-follow-up, no release). P0 3건: project_status_assessment.md §2 매트릭스 1…

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

- phase_15_north_star: `telemetry_hit_rate (1 release ≥ 1 query + hit)`
- entries_total: `7`
- telemetry_events_total: `6`
- telemetry_total_queries: `6`
- telemetry_hit_count: `6`
- telemetry_hit_rate: `1.0000`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 7 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 3 |
| `dispatcher` | 1 |
| `doc-sync` | 1 |
| `session-start` | 1 |

