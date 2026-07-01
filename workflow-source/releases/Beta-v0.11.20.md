# Beta v0.11.20 — 2차 batch 4 skill stable 승격 + state.json path latent bug fix (2026-07-01)

> Phase 12 의 *운영 안정화 + governance 후속* release 의 후속. v0.11.19 (1차 batch 4 skill stable) 의 follow-up 인 **2차 batch 4 skill stable 승격** + **v0.6.0.1 부터 누적된 state.json path latent bug fix** + **workflow-linter broken_link false-positive fix** + **output_samples tool_version housekeeping**. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (2차 batch 4 skill stable 승격)

v0.11.19 의 follow-up batch blocker 4종 모두 해소 → 누적 stable skill 4 → **8**, beta 7 → **3**, prototype 4 유지.

### Stable 승격 정합 조건 검증 (v0.11.20 정합)

skill_beta_criteria.md §3.1 의 정합 조건 6개 모두 충족 확인:

- [x] **입력 파라미터 CLI 정의** — `parser.add_argument()` argparse 정의
- [x] **출력 JSON 스키마 문서화** — skill spec + `output_sample_contracts.json` + `generated_output_schemas.json` (`project_status_assessment` 신규 family 등록)
- [x] **error_code 분류 최소 3종** — `missing_required_document` / `<skill>_runtime_error` + skill 별 2 종 추가 (총 4종)
- [x] **실행 스크립트 단일 명령** — `scripts/run_<skill>.py` 1 entry
- [x] **SKILL.md 실행 예시** — `예시 실행` 섹션 통일
- [x] **smoke test 통과** — 신규 2 file + 기존 2 file 모두 PASS

### Stable 승격된 4 skill (2차 batch)

| Skill | Smoke test | error_code | Spec | Status |
|---|---|---|---|---|
| `backlog-update` | ✅ PASS (282 line, 4 case) | 4종 (`invalid_task_brief` / `backlog_write_failed` / `missing_required_document` / `backlog_update_runtime_error`) | backlog_update_skill_spec.md | **stable** |
| `merge-doc-reconcile` | ✅ PASS (171 line, 4 case) | 4종 (`merge_conflict_detected` / `doc_index_stale` / `missing_required_document` / `merge_doc_reconcile_runtime_error`) | merge_doc_reconcile_skill_spec.md | **stable** |
| `workflow-linter` | ✅ PASS (178 line, 3 case) | 4종 (`missing_state_json` / `state_json_load_failure` / `matrix_json_load_failure` / `workflow_linter_runtime_error`) + 7 linter rule | workflow_linter/SKILL.md | **stable** |
| `project-status-assessment` | ✅ PASS (137 line, 3 case) | 3종 (`missing_required_document` / `project_assessment_runtime_error` + 신규 Pydantic schema 정합) | project_status_assessment.md | **stable** |

## 핵심 fix

### 1. state.json path latent bug (v0.6.0.1 부터) — `workflow_kit/common/state/cache.py`

**문제**: v0.6.0.1 의 `memory/active/` rename 직후 cache.py 의 `branch_dir = workflow_branch_dir(...) / "active"` 와 `state_path = branch_dir / "state.json"` 가 production 에서 `<memory>/<branch>/active/state.json` (dead path) 에 state.json 을 쓰도록 만들었음. workflow_linter 의 `workflow_memory_dir(...) / "state.json"` 패턴과 비대칭.

**영향**: `refresh_workflow_state_cache` 를 호출하는 모든 skill (`code-index-update`, `merge-doc-reconcile`, `backlog-update`) 의 state.json 이 잘못된 위치에 쓰여졌음. `tests/check_code_index_update_apply.py` 가 silently fail 했던 것이 이 latent bug 의 단서.

**fix**: `/ "active"` suffix 제거 → `memory_dir = workflow_memory_dir(...)`, `state_path = memory_dir / "state.json"`. production `ai-workflow/memory/active/state.json` 와 정합.

**test fixture 정합**: `tests/check_backlog_update.py`, `tests/check_code_index_update_apply.py` 의 `state.json` 기대 path 가 `<tempdir>/<branch>/state.json` → `<tempdir>/state.json` (cache.py default 변경 정합).

### 2. workflow-linter broken_link false-positive — `workflow_kit/common/linter.py`

**문제**: v0.7.22 의 `.resolve()` → `.absolute()` fix (symlink-aware) 가 의도적으로 symlink 따라가지 않음은 좋았지만 `..` segment 정규화도 함께 fallback 되어 `/tmp/x/foo/../../../../README.md` 형태의 literal path 가 `.exists()` 에서 False → false-positive broken link 보고.

**fix**: `.absolute()` 후 `os.path.normpath` 로 정규화한 path 로 `.exists()` 검증. symlink 따라가지 않으면서 `..` 만 풀어서 false-positive 해소.

**test fixture 정합**: `tests/check_workflow_linter.py` 의 `test_linter_pass` 의 link depth `../../../../README.md` (4 dot) → `../../../README.md` (3 dot) 으로 정정.

### 3. project-status-assessment Pydantic schema 정합

기존 `build_runner_success_result` + `extra_fields` dict emission 이 다른 stable skill 의 `BaseOutput` + nested Pydantic dataclass 패턴과 비대칭. 신규 `workflow_kit/common/schemas/assessment.py` (6 nested dataclass + `ProjectStatusAssessmentOutput` Pydantic) 도입으로 정합.

## Follow-up batch (v0.11.21+ 후보)

아직 beta 상태인 **3 skill** 별 blocker:

| Skill | Blocker | 해결 정공법 |
|---|---|---|
| `automated-repro-scaffold` | 프로토타입 + `validation-plan` 연동만 | Pydantic schema + error_code 3종 + smoke test |
| `robust-patcher` | `--apply` 지원 beta, smoke test 부족 | smoke test 추가 + runtime 정합 |
| `git-conflict-resolver` | Alpha 단계, runtime script prototype | spec 보강 + Pydantic schema + error_code |

## 누적 결과

| 항목 | v0.11.19 | **v0.11.20** |
|---|---|---|
| Stable skill | 4 | **8** (+4: backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment) |
| Beta skill | 7 | **3** (-4) |
| Prototype skill | 4 | 4 |
| mypy strict | 0 errors / 107 file | **0 errors / 108 file clean** (+1 신규 schema) |
| Layer 1 (CI) | ✅ | ✅ |
| Layer 2 (release-time) | ✅ | ✅ |
| Cross-verify | ✅ | ✅ |
| Latent bug fix | n/a | **2** (state.json path / broken_link false-positive) |

## 검증

- `workflow-source/tests/check_backlog_update.py`: PASS (4 case)
- `workflow-source/tests/check_merge_doc_reconcile.py`: PASS (4 case) — 신규
- `workflow-source/tests/check_workflow_linter.py`: PASS (3 case)
- `workflow-source/tests/check_project_status_assessment.py`: PASS (3 case) — 신규
- `workflow-source/tests/check_code_index_update_apply.py`: PASS (이전 fail → pass)
- `workflow-source/tests/check_doc_sync_apply.py`: PASS (회귀)
- `workflow-source/tests/check_session_start.py`: PASS (회귀)
- `workflow-source/tests/check_doc_sync.py`: PASS (회귀)
- `workflow-source/tests/check_validation_plan.py`: PASS (회귀)
- `workflow-source/tests/check_code_index_update.py`: PASS (회귀)
- `workflow-source/tests/check_baselines_compliance.py`: 16 tests PASS
- `workflow-source/tests/check_output_samples.py`: 24 JSON files PASS (tool_version housekeeping)
- `workflow-source/tests/check_output_json_schema.py`: PASS (`project_status_assessment` family 등록)
- `workflow-source/tests/check_generated_schema_validation.py`: PASS
- `workflow-source/tests/check_wiki_source_rule.py` (V-R9): PASS
- `mypy --no-incremental --strict workflow-source/workflow_kit/`: **0 errors, 108 file clean** ✅
- GH Actions mypy-strict workflow: cumulative 정합 유지 (Layer 1 ✅)

## File 변경 (총 7 commit, +517/-205)

1. **`workflow-source/workflow_kit/common/state/cache.py`** — `/ "active"` suffix 제거
2. **`workflow-source/workflow_kit/common/linter.py`** — `os.path.normpath` 정규화
3. **`workflow-source/workflow_kit/common/schemas/assessment.py`** (신규, 71 line) — `ProjectStatusAssessmentOutput` Pydantic + 6 nested dataclass
4. **`workflow-source/workflow_kit/common/schemas/__init__.py`** — `assessment` 모듈 export 등록
5. **`workflow-source/workflow_kit/common/output_contracts.py`** — `PYDANTIC_MODEL_REGISTRY` 에 `project_status_assessment` family 등록
6. **`workflow-source/skills/backlog-update/scripts/run_backlog_update.py`** — `invalid_task_brief` / `backlog_write_failed` error_code 추가
7. **`workflow-source/skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py`** — `merge_conflict_detected` / `doc_index_stale` error_code 추가 + `get_current_branch` import
8. **`workflow-source/skills/project-status-assessment/scripts/run_project_status_assessment.py`** — Pydantic schema 정합 + `missing_required_document` error_code
9. **`workflow-source/skills/{backlog-update,merge-doc-reconcile,workflow-linter,project-status-assessment}/SKILL.md`** — status → stable + 예시 실행 섹션 통일
10. **`workflow-source/core/skill_beta_criteria.md`** — §3 표 stable 상태 갱신 + §3.1 stable 정합 검증
11. **`workflow-source/core/workflow_skill_catalog.md`** — §1 / §2 표 stable 상태 갱신
12. **`workflow-source/tests/check_backlog_update.py`** — `state.json` 기대 path 정합 (`<branch>/state.json` → `<memory_dir>/state.json`)
13. **`workflow-source/tests/check_workflow_linter.py`** — broken link test 의 link depth 4 → 3 dot 정정
14. **`workflow-source/tests/check_code_index_update_apply.py`** — `state.json` 기대 path 정합
15. **`workflow-source/tests/check_merge_doc_reconcile.py`** (신규, 171 line) — 4 case smoke test
16. **`workflow-source/tests/check_project_status_assessment.py`** (신규, 137 line) — 3 case smoke test
17. **`workflow-source/examples/output_samples/*.json`** (24 file) — tool_version v0.11.17-beta → v0.11.19-beta 갱신
18. **`workflow-source/schemas/generated_output_schemas.json`** — runtime contracts 와 정합 regenerate
19. **`workflow-source/pyproject.toml`** — version bump `0.11.19` → `0.11.20`
20. **`workflow-source/workflow_kit/__init__.py`** — `__version__` auto-sync (3-tier fallback chain)

## GitHub release

- Tag: `v0.11.20-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌
- PyPI 배포: ❌ (GitHub Releases only)
- Workflow: `pre-check + tag push + gh release` 한 cycle (v0.7.21+ 정공법)

## 다음 release (v0.11.21 candidate)

- **3 beta skill stable 승격** — automated-repro-scaffold / robust-patcher / git-conflict-resolver 의 blocker 해소 후 승격. 또는 누적 housekeeping (sample drift, generated schema, R-A follow-up part 4 deferred 등).
- **또는 v1.0.0 milestone prep** — Phase 12 종료 + SemVer stable guarantee 2-year 진입 평가 (3 beta skill 모두 stable 시 자연스러운 milestone).
- **또는 다른 housekeeping** — beta → stable transition 의 spec / runtime / wiki layer 동기화 정합 verify.

## 메모리 layer (memory → commit → push 흐름 정합)

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.20 (4 skill stable + 2 latent bug fix)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.20 entry
- `ai-workflow/memory/release/v0.11.20/backlog/2026-07-01.md` (per-release detail)