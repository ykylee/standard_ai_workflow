# Quality Dashboard Snapshot

- generated_at: `2026-07-16T06:10:23Z`
- tool_version: `v0.14.0-beta`
- workspace_root: `/home/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `fail`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-07-09`
- harness_supported_count: `10`
- head_commit_date: `2026-07-16`
- last_updated_delta_days: `7`
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
| stable | 8 |
| beta | 4 |
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

- cumulative_total: `41`
- cumulative_pass: `41`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `175`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v0.13.0 | 41 | 41 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-07-01-003 — v0.11.18 — **🎯 SemVer patch, FULL mypy strict 도달 공식 봉인 (107 file clean)**. 누적 mypy strict 잔여 23 → …
- [1] TASK-2026-07-02-001 — v0.11.21 — **SemVer patch, 3차 batch robust-patcher stable 승격**. v0.11.20 (2차 batch 4 skill stable)…
- [2] TASK-2026-07-09-001 — v0.13.3 — **SemVer patch, Phase 13 AC4+ (self-documenting wiki ↔ memory bidirectional link) close-…
- [3] TASK-2026-07-09-002 — v0.13.2 — **SemVer patch, Phase 13 AC3 (self-recovering) close-out**. drift prevention 의 6 case 가 …
- [4] TASK-2026-07-09-003 — v0.13.1 — **SemVer patch, Phase 13 AC2 (memory_index 활용도) close-out**. v0.13.0 Quality Dashboard 의…
- [5] Phase 10 MCP/JSON-RPC draft
- [6] Phase 6 multi-agent delegation pilot
- [7] workflow 종료 단계 commit/memory 순서 정정 (commit `32185c7`) — 협업 결함 (push 시 memory 갱신 누락 / 추가 commit 유발) 해결. 11 file 변경: `work…
- [8] 워크플로우 구성 점검 + 고도화 후보 10건 도출 (audit-session, no release). 현 상태 v0.11.22-beta 스냅샷 (Phase 12 in_progress, skill stable=9 / …
- [9] 2026-07-09 audit-session 의 고도화 후보 10건 일괄 해소 (audit-follow-up, no release). P0 3건: project_status_assessment.md §2 매트릭스 1…

