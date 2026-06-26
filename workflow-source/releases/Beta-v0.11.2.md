# Beta v0.11.2 — Cycle 4 deferred 통합 (graph_insights schema + 3 skill context load) (2026-06-26)

> **SemVer patch** (v0.11.1 → v0.11.2) — v0.11.1 release note 의 commit message 에 명시한 deferred TASK (TASK-V1111-003, TASK-V1111-004) 흡수. v0.11.1 의 cycle 4 가 standalone dispatch 중심이었다면, v0.11.2 는 **3 output schema extension + 3 skill context load 통합** 으로 cycle 4 의 start → end-of-2-step-cycle 완결성 회복. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (2 deferred TASK 통합 + 1 spec layer extension + 5 acceptance test)

### 1. `GraphInsightsOutput` schema 3종 정의 (TASK-V1111-003 deferred)

**v0.11.0 cycle 3 (`*PurposeCoTTrace`) 와 동일 nested Pydantic model 패턴 흡수**:

| Schema | File | Field |
|---|---|---|
| `SessionStartOutput` | `workflow_kit/common/schemas/session.py` | `graph_insights: GraphInsightsOutput \| None = None` |
| `BacklogUpdateOutput` | `workflow_kit/common/schemas/backlog.py` | `graph_insights: GraphInsightsOutput \| None = None` |
| `DocSyncOutput` | dict 기반 (cycle 3 정합) | `result["graph_insights"] = {...}` |

**`GraphInsightsOutput` nested Pydantic model** (session + backlog 공통 정의):
```python
class GraphInsightsOutput(BaseModel):
    """v0.11.2 cycle 4 deferred 통합: graph insights output."""

    coverage_pct: float = 0.0
    covered_count: int = 0
    uncovered_count: int = 0
    covered_goals: list[str] = Field(default_factory=list)
    uncovered_goals: list[str] = Field(default_factory=list)
    surprising_count: int = 0
    scope_creep_warnings: list[str] = Field(default_factory=list)
    gaps_count: int = 0
    health_score: int = 0
    health_tier: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
```

**`schemas/__init__.py` export 갱신**:
- `SessionGraphInsightsOutput` (alias for `GraphInsightsOutput` in session.py)
- `BacklogGraphInsightsOutput` (alias for `GraphInsightsOutput` in backlog.py)
- `SessionStartPurposeCoTTrace` / `BacklogUpdatePurposeCoTTrace` 추가 (cycle 3 정합)

### 2. 3 skill context load 통합 (TASK-V1111-004 deferred)

**session-start** (`workflow-source/skills/session-start/scripts/run_session_start.py`):
- cycle 3 `run_two_step_cot_ingest` 호출 직후 `run_graph_insights` 호출
- `GraphInsightsOutput` 자동 populate + `warnings.extend(graph_result.overall_warnings)`
- output binding: `SessionStartOutput(..., graph_insights=graph_insights)`

**backlog-update** (`workflow-source/skills/backlog-update/scripts/run_backlog_update.py`):
- 동일 패턴 + `BacklogUpdateOutput.graph_insights` field

**doc-sync** (`workflow-source/skills/doc-sync/scripts/run_doc_sync.py`):
- dict 기반: `result["graph_insights"] = {...}` (cycle 3 dict 패턴 정합)

### 3. Spec layer 갱신 (1 spec)

| Spec | Section | 변경 |
|---|---|---|
| `core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 4 deferred entry | v0.11.2 cycle 4 deferred 통합 entry 추가 (3 output schema + 3 skill 통합) |
| `core/llm_wiki_concept_purpose_spec.md` | §5 acceptance criterion | cycle 4 check item `[ ]` → `[x]` |
| `core/llm_wiki_concept_purpose_spec.md` | §10 R-A follow-up cycle table | cycle 4 의 v0.11.1 + v0.11.2 통합 ✅ |

## 운영 누적 (v0.11.1 → v0.11.2)

| | v0.11.1 | **v0.11.2** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **`GraphInsightsOutput` schema** | ❌ | **✅ (session + backlog + doc_sync dict)** |
| **`SessionStartOutput.graph_insights` field** | ❌ | **✅** |
| **`BacklogUpdateOutput.graph_insights` field** | ❌ | **✅** |
| **`DocSyncOutput["graph_insights"]` dict** | ❌ | **✅** |
| **3 skill context load 통합** | ❌ | **✅ (session-start + backlog-update + doc-sync)** |
| **cumulative acceptance** | 77/77 | **82/82** (v0.11.2 5 신규) |
| **spec §9 acceptance** | 12/12 | **12/12** (변동 ❌) |
| **breaking change** | none | **none** (schema 추가만, v0.11.1 호환) |
| **Bundle 비율 (1차 출처)** | ~95% | **~95%** (변동 ❌, 정형화 패턴 흡수만) |

## Test 결과

- 신규 (5 PASS, v0.11.2):
  - `test_session_start_graph_insights_v0_11_2` — SessionStartOutput.graph_insights 자동 populate (정상 100%/PURPOSE 부재/state 부재/둘 다 부재 4 case)
  - `test_backlog_update_graph_insights_v0_11_2` — BacklogUpdateOutput.graph_insights 자동 populate (4 case 동일)
  - `test_doc_sync_graph_insights_v0_11_2` — DocSyncOutput["graph_insights"] dict 자동 populate (4 case)
  - `test_graph_insights_schema_consistency_v0_11_2` — Session ↔ Backlog 동일 data round-trip (real repo state)
  - `test_graph_insights_skills_no_state_mutation_v0_11_2` — read-only helper verify (state.json + PURPOSE.md mtime/size preserved)
- v0.11.1 회귀: **8/8 PASS** ✅
- v0.11.0 회귀: **6/6 PASS** ✅
- v0.10.3 회귀: **7/7 PASS** ✅
- v0.10.2 회귀: **9/9 PASS** ✅
- v0.10.1 회귀: **6/6 PASS** ✅
- v0.10.0 회귀: **6/6 PASS** ✅
- v0.9.6 회귀: **6/6 PASS** ✅
- v0.9.5 회귀: **6/6 PASS** ✅
- v0.9.4 회귀: **3/3 PASS** ✅
- v0.9.2 회귀: **8/8 PASS** ✅
- v0.9.3 회귀: **4/4 PASS** ✅
- v0.9.1 회귀: **4/4 PASS** ✅
- v0.9.0 회귀: **6/6 PASS** ✅
- 누적 acceptance: **82/82 PASS**
- 누적 smoke: **162/162 + 82 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7 + v0.11.0 6 + v0.11.1 8 + v0.11.2 5)

## 변경 파일 (7 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/schemas/session.py` | `GraphInsightsOutput` nested model + `SessionStartOutput.graph_insights` field |
| M | `workflow-source/workflow_kit/common/schemas/backlog.py` | `GraphInsightsOutput` nested model + `BacklogUpdateOutput.graph_insights` field |
| M | `workflow-source/workflow_kit/common/schemas/__init__.py` | SessionGraphInsightsOutput / BacklogGraphInsightsOutput / PurposeCoTTrace export |
| M | `workflow-source/skills/session-start/scripts/run_session_start.py` | `run_graph_insights` 호출 + `graph_insights=graph_insights` binding |
| M | `workflow-source/skills/backlog-update/scripts/run_backlog_update.py` | 동일 패턴 |
| M | `workflow-source/skills/doc-sync/scripts/run_doc_sync.py` | dict 기반 graph_insights 추가 |
| M | `workflow-source/core/llm_wiki_concept_purpose_spec.md` | §4.3 cycle 4 deferred entry + §5 acceptance `[x]` |
| M | `workflow-source/pyproject.toml` | version 0.11.1 → 0.11.2 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.1-beta"` → `"v0.11.2-beta"` |
| M | `ai-workflow/memory/active/state.json` | in_progress + latest_backlog_path 갱신 |
| A | `workflow-source/tests/check_graph_insights_skill_integration_v0_11_2.py` | 신규 (5 acceptance test, ≈ 600 line) |
| A | `workflow-source/releases/Beta-v0.11.2.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.2/backlog/2026-06-26.md` | v0.11.2 plan |

## 다음 (v0.11.3+ / v1.0.0)

1. **v0.11.3 follow-up** — mypy strict cumulative 격상 (19 → 20-21 file). 1 release = 1-2 file 단계적 격상.
2. **v1.0.0 milestone** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상). spec §9 acceptance 12/12 도달 유지.
