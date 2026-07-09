# Quality Dashboard Snapshot

- generated_at: `2026-07-09T07:10:09Z`
- tool_version: `v0.13.3-beta`
- workspace_root: `.`

## Panel 1 — Drift Prevention Status

- guard_status: `unknown`
- guard_cases: `6 / 6`
- maturity_last_updated: `2026-07-09`
- harness_supported_count: `10`
- head_commit_date: `2026-07-09`
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
- smoke_files_count: `174`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v0.13.0 | 41 | 41 |
| Beta-v0.11.25 | 40 | 40 |
| Beta-v0.11.24 | 40 | 40 |

## Panel 5 — Recent Release Cycle

- items_total: `62`
- top_n: `10`

### Timeline (preview, first 120 char)

- [0] v0.13.2 (self-recover wiring commit, 2026-07-09): Phase 13 AC3 (self-recovering) close-out — drift prevention 의 6 case 가…
- [1] v0.13.1 (telemetry wiring commit, 2026-07-09): Phase 13 AC2 (memory_index 활용도) close-out — Quality Dashboard Panel 3 의 `…
- [2] 2026-07-09 (audit-follow-up): 2026-07-09 audit-session 의 고도화 후보 10건 일괄 해소 (no release, no version bump). **P0 (즉시 가치, 3건…
- [3] 2026-07-09 (audit-session): 워크플로우 구성 점검 + 고도화 후보 도출 — 현 상태 v0.11.22-beta 스냅샷 (Phase 12 in_progress, skill stable=9 / MCP…
- [4] v0.11.21 (c90b437): 3차 batch robust-patcher stable 승격 — GitHub Release v0.11.21-beta tag push + gh release create exit 0…
- [5] v0.11.20 (af6baaf): 2차 batch 4 skill stable 승격 + 2 latent bug fix — GitHub Release v0.11.20-beta tag push + gh release c…
- [6] v0.11.19 (dfafdc4): 1차 batch 4 skill stable 승격 — GitHub Release v0.11.19-beta tag push + gh release create exit 0 (https…
- [7] v0.11.18 (80470cd): FULL mypy strict 도달 공식 release — GitHub Release v0.11.18-beta tag push + gh release create exit 0 (h…
- [8] v0.11.18-dev (4253eed): mypy strict 잔여 13 error 일괄 격상 — FULL mypy strict 도달 (107 file clean). session 마무리. 12 file 일괄: a…
- [9] v0.11.18-dev (65f0b20): mypy strict read_only_mcp_sdk + doc_sync 묶음 격상 — server + common cross-layer, read_only_mcp_sdk.…

