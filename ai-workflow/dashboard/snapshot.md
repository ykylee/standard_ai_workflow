# Quality Dashboard Snapshot

- generated_at: `2026-08-31T15:00:02Z`
- tool_version: `1.8.0`
- workspace_root: `/Users/yklee/repos/standard_ai_workflow`

## Panel 1 — Drift Prevention Status

- guard_status: `pass`
- guard_cases: `7 / 7`
- maturity_last_updated: `2026-08-31`
- maturity_surface_changed_at: `2026-08-31`
- maturity_stale: `False` (source: `maturity_surface_commit`)
- harness_supported_count: `10`
- head_commit_date: `2026-08-31`
- last_updated_delta_days: `0`
- silent_failing_cycles_count: `0` (측정 cycle 12건)

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

- entries_total: `15`
- entries_by_merge_state: `active`=15
- cue_anchors_unique: `101`
- first_entry_date: `2026-07-09`
- last_entry_date: `2026-08-24`

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

- cumulative_total: `276`
- cumulative_pass: `276`
- cumulative_pass_rate: `1.0000`
- smoke_files_count: `276`

### Recent release smoke counts

| version | pass | total |
|---|---|---|
| Beta-v1.8.0 | 276 | 276 |
| Beta-v1.7.0 | 276 | 276 |
| Beta-v1.6.0 | 275 | 275 |
| Beta-v1.5.0 | 274 | 274 |
| Beta-v1.4.0 | 274 | 274 |

## Panel 5 — Recent Release Cycle

- items_total: `10`
- top_n: `10`
- confidence: `fresh=10`

### Timeline (preview, first 120 char)

- [0] TASK-2026-08-31-main-004 — codex marketplace source 가 휘발 경로를 가리켜도 탐침이 침묵한다 — 사본과 경유지는 따로 깨진다  `[fresh]`
- [1] TASK-2026-08-31-main-003 — backlog-update update 가 열거 필드를 교체해 이전 세션 기록을 지운다 — 손실에 경고가 없다  `[fresh]`
- [2] TASK-2026-08-31-main-002 — wk doctor 가 자기 자신의 낡음을 말하지 않는다 — 탐침이 저장소와 갈라진 사본으로 돈다  `[fresh]`
- [3] TASK-2026-08-31-main-001 — 문서의 '현재 버전' 주장이 kit 을 안 따라온다 — 검사가 존재만 보고 통과시킨다  `[fresh]`
- [4] TASK-2026-08-30-main-004 — pi 패키지 매니페스트가 버전 정합 밖에 있다 — plugin/package.json 이 1.2.0 에 고착  `[fresh]`
- [5] TASK-2026-08-30-main-003 — content_drift 가 사본 0 인 채널을 침묵으로 지운다 — '없다' 와 '못 봤다' 가 구별되지 않는다  `[fresh]`
- [6] TASK-2026-08-30-main-002 — doctor 의 grok-build 설치본 탐지가 디렉터리 이름 가정에 기대 실패 — 정본은 registry.json  `[fresh]`
- [7] TASK-2026-08-30-main-001 — 자식 spawn 이 리터럴 python3 — meta-watch PYTHONPATH 주입에서만 드러나는 환경 의존 red 3건  `[fresh]`
- [8] TASK-2026-08-29-main-006 — antigravity 하네스 조사 + 지원 추가  `[fresh]`
- [9] TASK-2026-08-29-main-005 — gemini-cli 하네스 지원 완전 제거  `[fresh]`

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
- entries_total: `15`
- telemetry_events_total: `1306`
- telemetry_total_queries: `1306`
- telemetry_hit_count: `126`
- telemetry_hit_rate: `0.0965`

### Entries by merge_state

| merge_state | count |
|---|---|
| `active` | 15 |

### Telemetry by source

| source | events |
|---|---|
| `backlog-update` | 201 |
| `doc-sync` | 1 |
| `session-start` | 1104 |

