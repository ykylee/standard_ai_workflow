# Memory Index (ADR-005 Phase 1)

- 문서 목적: ADR-005 Memora-inspired Memory Index 의 *seed layer* 디렉토리. session-start / doc-sync / backlog-update 의 opt-in retrieval wiring (v0.11.22+ Phase 3b/c/d) 의 실 데이터 보존.
- 범위: `entries/` 디렉토리 + 본 README + 스키마. 1 entry = 1 JSON file.
- 대상 독자: AI agent (memory retrieval), maintainer
- 상태: stable (seed: 2026-07-09)
- 최종 수정일: 2026-07-09
- 관련 문서:
  - [ADR-005](../../../../workflow-source/docs/architecture/ADR-005-memora-inspired-memory-index.md) (architecture spec)
  - [`../../../../workflow-source/workflow_kit/common/schemas/memory_index.py`](../../../../workflow-source/workflow_kit/common/schemas/memory_index.py) (Pydantic schema)
  - [`../../../../workflow-source/workflow_kit/common/state/memory_index.py`](../../../../workflow-source/workflow_kit/common/state/memory_index.py) (helper module)

## 1. 디렉토리 layout

```
memory_index/
├── README.md          # 본 문서
└── entries/
    ├── MEM-YYYY-MM-DD-001.json
    ├── MEM-YYYY-MM-DD-002.json
    └── ...
```

- `entries/*.json` 1 file = 1 MemoryEntry (ADR-005 §2).
- id 형식: `MEM-YYYY-MM-DD-NNN` (NNN = 같은 날짜에서 001~ 단조 증가).
- 신규 entry 생성: helper `save_memory_entry(<workspace_root>, <entry>)` (Pydantic validate + atomic_write_json) 사용 권장.

## 2. Seed entries (2026-07-09)

본 디렉토리는 v0.11.22-beta baseline 의 핵심 concept 을 seed 한다. retrieval cue 다양성 보장을 위해 7개 seed entry 작성.

| id | primary_abstraction (요약) | source |
|---|---|---|
| `MEM-2026-07-09-001` | Workflow audit session (2026-07-09) baseline + 10 candidates | `session_analysis_2026-07-09.md` |
| `MEM-2026-07-09-002` | ADR-005 Memora-inspired Memory Index schema + retrieval 3-tuple | `ADR-005-memora-inspired-memory-index.md` |
| `MEM-2026-07-09-003` | FULL mypy strict 도달 (v0.11.18, 109 file clean) — quality milestone | `maturity_matrix.json` |
| `MEM-2026-07-09-004` | StdIO SDK v0.11.25 정식 stable 승격 (Phase 12 close candidate) | `Beta-v0.11.25.md` |
| `MEM-2026-07-09-005` | Drift prevention automation (v0.11.23, 6 case cross-check smoke) | `check_drift_prevention_v0_11_23.py` |
| `MEM-2026-07-09-006` | CodeWhale 10번째 하네스 overlay (v0.10.4, single SKILL.md) | `maturity_matrix.json` + commit cf0060d |
| `MEM-2026-07-09-007` | Contract v1 P0 enforcement + Mavis engine hook (Phase 12 follow-up) | `orchestrator_subagent_contract_v1.md` |

각 entry 의 `cue_anchors[]` 는 LLM retrieval 시 anchor match 의 진입점. `value_digest` 는 1줄 preview. `source_paths` 는 본문 원본 위치. `mentioned_in` 은 본 entry 를 참조하는 영구 문서/ADR/wiki 경로.

## 3. 운영 규칙

- **생성**: 새 session 또는 새 concept 발견 시 helper 로 entry 1개 생성.
  ```python
  from workflow_kit.common.schemas.memory_index import MemoryEntry, MergeState
  from workflow_kit.common.state.memory_index import save_memory_entry
  from datetime import datetime, timezone
  e = MemoryEntry(id="MEM-2026-07-09-008", ..., created_at=datetime.now(timezone.utc))
  save_memory_entry(Path("/home/yklee/repos/standard_ai_workflow"), e)
  ```
- **merge**: ADR-005 §4 canonical merge. `apply_memory_merge(workspace_root, MemoryMergeRequest(source_ids=[...], apply=False))` 으로 dry-run 후 `--apply`.
- **validate**: `validate_memory_index(workspace_root)` 으로 주기적 검증 (duplicate id / duplicate primary_abstraction / source_paths 중복).
- **retrieval**: `query_memory_index_for_dispatcher(workspace_root, query_tokens=[...])` — session-start / doc-sync / backlog-update 의 opt-in wiring 의 실 호출.

## 4. retrieval wiring (어떤 skill 이 어떻게 쓰는가)

| skill | flag | behavior |
|---|---|---|
| `session-start` (Phase 3b) | `--memory-index-dir` + `--memory-query-tokens` 둘 다 지정 | 진입 시 memory_index 에서 query → hints emit. 부재 시 silent skip (main flow 방해 ❌). |
| `doc-sync` (Phase 3c) | 동일 | doc 갱신 시 memory_index query 후 영향 concept cross-ref. |
| `backlog-update` (Phase 3d) | 동일 | backlog entry 추가 시 memory_index query 후 관련 entry link. |

opt-in 이므로 **flag 미지정 시 silent skip** — main flow 에 영향 없음. wiring 의 목적은 *value-add* 이지 *block* 이 아님.

## 5. P0-3 self-dogfood 노트

2026-07-09 audit (P0-3 후보) 에서 `ai-workflow/memory/active/memory_index/` 부재 확인. 본 commit 으로:

1. 디렉토리 layout 보강 (`entries/` 포함)
2. 본 README 작성 (schema + 운영 규칙 + retrieval wiring 명세)
3. seed entry 7개 작성 (2026-07-09 baseline 의 핵심 concept)
4. helper module 의 동작 검증 (id pattern, schema validation, atomic write)

이후의 wiring 호출은 silent skip → 실 retrieval 으로 전환. P1-3 (drift 사례 분류) 의 seed data 로도 활용 가능.

## 다음에 읽을 문서
- [ADR-005](../../../../workflow-source/docs/architecture/ADR-005-memora-inspired-memory-index.md)
- [schema](../../../../workflow-source/workflow_kit/common/schemas/memory_index.py)
- [helper](../../../../workflow-source/workflow_kit/common/state/memory_index.py)
