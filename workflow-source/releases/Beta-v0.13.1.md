---
release: v0.13.1
closed_phases: []
promoted_skills: []
added_harnesses: []
deprecated_symbols: []
phase_13_sub_milestones:
  - { name: v0.13.1, scope: "memory_index telemetry sidecar", status: shipped }
---

# Beta v0.13.1 — memory_index telemetry sidecar (Phase 13 AC2 close) (2026-07-09)

> Phase 13 (Operational Intelligence v1.0) 의 sub-milestone 2nd release.
> v0.13.0 Quality Dashboard 의 Panel 3 (memory_index utilization) 가
> `retrieval_hit_rate=0.0` placeholder (`pending_phase_13_ac2_telemetry`) 로
> 출시된 후속. 본 release 는 placeholder → 실측값 전환 + telemetry sidecar
> 인프라 + 3 skill + dispatcher 자동 wiring. AC2 close-out.

## 핵심 (telemetry sidecar 인프라 + 자동 wiring)

### 1. 신규 schema (`workflow_kit/common/schemas/memory_index.py`)

- `MemoryIndexTelemetryEvent`: 1 retrieval call 의 1 row (timestamp / source /
  workspace_root / query_tokens_count / selected_count / cue_hits /
  bm25_hits / expansion_hits / top_k / max_depth / use_bm25_fallback /
  error flag).
- `MemoryIndexTelemetrySummary`: read-time 집계 (total_calls /
  total_hits / hit_rate / by_source / first_event_at / last_event_at /
  events_parsed / events_skipped / source_version).

### 2. 신규 helper (`workflow_kit/common/state/memory_index.py`)

- `TELEMETRY_SUBDIR = "telemetry"` + `TELEMETRY_FILE = "events.jsonl"` constant.
- `telemetry_path(workspace_root)` + `telemetry_dir(workspace_root)`.
- **`append_telemetry_event(workspace_root, event)`** — in-process
  `threading.Lock` + `open("a")` + `flush` 정공법 (consumer_metrics.py 의
  JSONL append 와 동일). OSError 시 silent stderr warn (telemetry 부재
  가 retrieval 본체를 깨지 않음, zero-risk default).
- **`summarize_telemetry(workspace_root)`** — JSONL parse + malformed line
  skip + error-flag skip. hit 정의: `selected_count > 0 and not error`.
- `read_telemetry_events(workspace_root)` — raw list (subcommand
  `--show-events` 용).

### 3. 자동 wiring — 4 source × 4 path = 12 emit point

- **session-start / doc-sync / backlog-update** (`skills/*/scripts/run_*.py`
  의 `_build_memory_index_query_output`): retrieval 성공 시 success-path
  telemetry emit + workspace_root 외부 dir / 예외 path 는 `error=True`
  flag 로 emit (negative example 보존). output schema 변경 ❌ (sidecar 만).
- **dispatcher** (`workflow_kit_cli.py:cmd_memory_index_query`): 같은
  패턴 + try/except 외부에 emit.

### 4. 신규 dispatcher subcommand 36: `cmd_memory_index_telemetry`

- ARGS: `--workspace-root`, `--json` / `--show-events`.
- §6.3 MUST-NOT-delegate 정합 (read-only).

### 5. Dashboard Panel 3 placeholder → 실측값

- `dashboard_data.py:collect_memory_index_utilization` 가 `summarize_telemetry` 호출.
- `retrieval_hit_rate: 0.0` → 실측 (e.g. 1.0 = 1/1 hit).
- `retrieval_hit_rate_source: "memory_index_telemetry_v0_13_1"` (placeholder 교체).
- 신규 field `telemetry.{total_calls, total_hits, by_source, ...}` 표시.

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow-source/tests/check_memory_index_telemetry.py` | 6 case smoke (1 emit / 2-hit-1-miss / by_source / malformed skip / graceful empty / concurrent append 10 line 보존) |
| 신규 | `ai-workflow/memory/release/v0.13.1/backlog/2026-07-09.md` | release note (cycle archive) |
| 신규 | `ai-workflow/memory/active/memory_index/telemetry/.gitkeep` | sibling subdir placeholder |
| extend | `workflow_kit/common/schemas/memory_index.py` | 2 schema 추가 (MemoryIndexTelemetryEvent + MemoryIndexTelemetrySummary) |
| extend | `workflow_kit/common/state/memory_index.py` | telemetry_path / telemetry_dir / append_telemetry_event / summarize_telemetry / read_telemetry_events 5 helper |
| extend | `workflow_kit/common/dashboard_data.py` | `_attach_telemetry_summary` post-hook + `_render_html_panel_3` telemetry field |
| extend | `workflow_kit/workflow_kit_cli.py` | `cmd_memory_index_query` telemetry emit + `cmd_memory_index_telemetry` subcommand 36 신규 등록 |
| extend | `skills/session-start/scripts/run_session_start.py` | `_build_memory_index_query_output` telemetry emit (3 path) |
| extend | `skills/doc-sync/scripts/run_doc_sync.py` | 동일 패턴 |
| extend | `skills/backlog-update/scripts/run_backlog_update.py` | 동일 패턴 |

## housekeeping

- samples 24 file `tool_version` v0.11.20-beta → v0.13.1-beta
- schemas regen (generated_output_schemas + output_sample_contracts)
- dashboard HTML regen (Panel 3 에 telemetry field 표시)
- pyproject.toml 0.13.0 → 0.13.1
- workflow_kit/__init__.py loud fallback v0.13.0-beta → v0.13.1-beta
- README.md header v0.13.0-beta → v0.13.1-beta + Phase 13 v0.13.1 follow-up 1줄
- maturity_matrix.json v0.13.0 + v0.13.1 2줄 추가
- memory_index/README.md layout 다이어그램 + telemetry 설명
- .gitignore events.jsonl runtime-generated 패턴 추가

## 검증 결과

- 신규 smoke **6/6 PASS** (check_memory_index_telemetry)
- memory_index smoke **25/25 PASS** (regression)
- 3 skill smoke (session-start / doc-sync / backlog-update) **3/3 PASS**
- Quality Dashboard smoke **10/10 PASS** (v0.13.0 회귀)
- drift prevention **6/6 PASS** (v0.11.23 회귀)
- output samples + generated schema validation **3/3 PASS**
- mypy strict **0 new error** (8 pre-existing in state/memory_index.py +
  state/builder.py 정공법 유지)
- memory freeze lint **PASS**

**누적 smoke 211+ PASS** (v0.13.0 200+ + 신규 6 + 회귀 5+)

## release URL

- tag: `v0.13.1-beta`
- breaking change: ❌
- PyPI 배포: no