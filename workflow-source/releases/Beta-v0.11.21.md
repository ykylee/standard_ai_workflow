# Beta v0.11.21 — 3차 batch robust-patcher stable 승격 (2026-07-01)

> Phase 12 의 *운영 안정화 + governance 후속* release 의 후속. v0.11.20 (2차 batch 4 skill stable) 의 follow-up 인 **robust-patcher 1 skill stable 승격**. v0.11.20 note 가 제시한 "3 beta skill 중 가장 성숙한 것부터 1 release 분할" 정공법의 첫 part. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (3차 batch robust-patcher stable 승격)

### Stable 승격 정합 조건 검증 (v0.11.21 정합)

skill_beta_criteria.md §3.1 의 정합 조건 6개 모두 충족 확인:

- [x] **입력 파라미터 CLI 정의** — `parser.add_argument()` argparse 정의 (`--file` / `--patch-file` / `--dry-run`)
- [x] **출력 JSON 스키마 문서화** — 신규 `RobustPatcherOutput` Pydantic schema + `output_sample_contracts.json` + `generated_output_schemas.json` (`robust_patcher` family 등록)
- [x] **error_code 분류 4종** — `missing_required_document` / `malformed_patch_block` / `fuzzy_match_failed` / `robust_patcher_runtime_error`
- [x] **실행 스크립트 단일 명령** — `scripts/run_robust_patcher.py` 1 entry (이전 비표준 `patch_engine.py` 폐기)
- [x] **SKILL.md 실행 예시** — `예시 실행` 섹션 통일
- [x] **smoke test 통과** — `tests/check_robust_patcher.py` 5 case PASS

### Stable 승격된 1 skill (3차 batch)

| Skill | Smoke test | error_code | Spec | Status |
|---|---|---|---|---|
| `robust-patcher` | ✅ PASS (148 line, 5 case) | 4종 (`missing_required_document` / `malformed_patch_block` / `fuzzy_match_failed` / `robust_patcher_runtime_error`) | phase6_precision_editing_plan.md | **stable** |

## 핵심 fix / 신규

### 1. 신규 `RobustPatcherOutput` Pydantic schema

기존 `patch_engine.py` 의 dict emission (status / tool_version / message / file_path / warnings 의 5개 field 만) 이 다른 stable skill 의 `BaseOutput` + nested dataclass 패턴과 비대칭.

**신규 schema** (`workflow_kit/common/schemas/patcher.py`, 35 line):
- `RobustPatcherOutput` (BaseOutput 상속)
- nested dataclass 2종: `AppliedPatchBlock` (block_index / matched / fuzzy_score / preview), `RobustPatcherSourceContext` (file / patch_file)
- `workflow_kit/common/schemas/__init__.py` export + `__all__` 등록
- `workflow_kit/common/output_contracts.py` 의 `PYDANTIC_MODEL_REGISTRY` 에 `robust_patcher` family 등록 (`validate_output_payload(family="robust_patcher")` 정합)

### 2. `apply_robust_patch_detailed` helper 신규

기존 `apply_robust_patch(file_path, patch_content, *, dry_run=False) → tuple[bool, str]` 가 2-tuple 로 minimal info 만 반환. v0.11.21 stable 정합을 위해 per-block detail 추적:

- **신규**: `apply_robust_patch_detailed(file_path, patch_content, *, dry_run=False) → tuple[bool, str, list[dict]]`
- detail 의 각 entry: `block_index` (0-based) / `matched` / `fuzzy_score` (`difflib.SequenceMatcher.ratio()` round 3자리) / `preview` (첫 80 char)
- **backwards-compatible**: `apply_robust_patch` 는 wrapper 로 남아 기존 caller (`patch_engine.py` 외 다른 곳이 있다면) 가 영향 ❌
- **atomic semantics**: 한 block 도 fuzzy fail 하면 즉시 rollback (원본 보존) — caller 가 partial apply 결과를 받지 않음

### 3. script 표준화 (`patch_engine.py` → `run_robust_patcher.py`)

이전 `scripts/patch_engine.py` (84 line) 가 표준 `scripts/run_<skill>.py` 진입점 패턴과 비대칭. **v0.11.21 부터 `run_robust_patcher.py` 로 표준화** + `patch_engine.py` 폐기 (trash).

`run_robust_patcher.py` 의 핵심 변경:
- **error_code 정합** (4종): `missing_required_document` (path 부재 사전 차단) / `malformed_patch_block` (valid SEARCH/REPLACE block 자체 부재) / `fuzzy_match_failed` (fuzzy 0.8 threshold fail 또는 post-patch SyntaxError) / `robust_patcher_runtime_error` (catch-all)
- **stage_completion 통합**: stage_name=`robust-patcher`, next_stage=`validation-plan` (catalog §3 wiring 정합)
- **Pydantic emission**: `RobustPatcherOutput(**).model_dump()` + `merge_into_result` 로 stage_completion 통합
- **dry-run 지원**: `--dry-run` flag 추가, file 변경 ❌

### 4. smoke test 신규 (`tests/check_robust_patcher.py`, 148 line, 5 case)

- **Case 1: exact-match 성공** — exact SEARCH/REPLACE block, `apply_robust_patch` 의 `difflib.ratio() == 1.0` 정합, syntax_validated=True, stage_completion.next_stage='validation-plan' 검증, file 실제 변경 verify
- **Case 2: dry-run preview** — `--dry-run` mode, file 변경 ❌ verify
- **Case 3: fuzzy_match_failed (atomic rollback)** — 존재하지 않는 SEARCH block, exit 1 + `fuzzy_match_failed` error_code, file 변경 ❌ verify
- **Case 4: malformed_patch_block** — SEARCH/REPLACE marker 없는 patch file, exit 1 + `malformed_patch_block` error_code
- **Case 5: missing_required_document** — patch file 미존재, exit 1 + `missing_required_document` error_code

영향: 4 skill 모두 6 조건 stable 정합 검증.

### 5. housekeeping — output_samples tool_version drift (v0.11.20 → v0.11.21 발견)

v0.11.20 release 시 housekeeping 후 v0.11.21 작업 중 24 sample file 의 `tool_version` v0.11.19-beta → **v0.11.20-beta** 갱신. runtime `workflow_kit.__version__` = `v0.11.20-beta` 와 정합.

**lesson (cross-project)**: 매 release 마다 output_samples 의 tool_version housekeeping 1 cycle 필수. post-step 자동화 미구현 — 수동 갱신 또는 sample regenerate script 보강 검토.

## Follow-up batch (v0.11.22+ 후보)

아직 beta / alpha 상태인 **2 skill**:

| Skill | Status | 해결 정공법 |
|---|---|---|
| `automated-repro-scaffold` | prototype (no scripts/ subdir, non-standard error_code) | Pydantic schema 정합 + error_code 3종 + scripts/ 구조 통일 + smoke test |
| `git-conflict-resolver` | Alpha (spec.md 없음, runtime script prototype, no smoke test) | spec.md 신규 + Pydantic schema 정합 + error_code 3종 + smoke test |

후속 v0.11.22+ 시 **각각 별도 release** (v0.11.21 와 같은 1 skill = 1 release 패턴) 또는 1 release 묶음 (session capacity 허용 시).

## 누적 결과

| 항목 | v0.11.20 | **v0.11.21** |
|---|---|---|
| Stable skill | 8 | **9** (+1: robust-patcher) |
| Beta skill | 3 | **2** (-1) |
| Prototype skill | 4 | 4 (alpha 1 + beta 1 + prototype 2) |
| mypy strict | 0 errors / 108 file | **0 errors / 109 file clean** (+1 신규 schema) |
| Layer 1 (CI) | ✅ | ✅ |
| Layer 2 (release-time) | ✅ | ✅ |
| Cross-verify | ✅ | ✅ |

## 검증

- `workflow-source/tests/check_robust_patcher.py`: PASS (5 case) — 신규
- `workflow-source/tests/check_backlog_update.py`: PASS (회귀)
- `workflow-source/tests/check_merge_doc_reconcile.py`: PASS (회귀)
- `workflow-source/tests/check_workflow_linter.py`: PASS (회귀)
- `workflow-source/tests/check_project_status_assessment.py`: PASS (회귀)
- `workflow-source/tests/check_session_start.py`: PASS (회귀)
- `workflow-source/tests/check_doc_sync.py`: PASS (회귀)
- `workflow-source/tests/check_validation_plan.py`: PASS (회귀)
- `workflow-source/tests/check_code_index_update.py`: PASS (회귀)
- `workflow-source/tests/check_baselines_compliance.py`: 16 tests PASS
- `workflow-source/tests/check_output_samples.py`: 24 JSON files PASS (tool_version housekeeping)
- `workflow-source/tests/check_output_json_schema.py`: PASS (`robust_patcher` family 등록)
- `workflow-source/tests/check_generated_schema_validation.py`: PASS
- `workflow-source/tests/check_wiki_source_rule.py` (V-R9): PASS
- `mypy --no-incremental --strict workflow-source/workflow_kit/`: **0 errors, 109 file clean** ✅
- GH Actions mypy-strict workflow: push 시 자동 실행

## File 변경 (총 8 commit, +504/-107)

1. **`workflow-source/workflow_kit/common/schemas/patcher.py`** (신규, 35 line) — `RobustPatcherOutput` Pydantic + nested dataclass 2종
2. **`workflow-source/workflow_kit/common/schemas/__init__.py`** — `patcher` 모듈 export 등록
3. **`workflow-source/workflow_kit/common/output_contracts.py`** — `PYDANTIC_MODEL_REGISTRY` 에 `robust_patcher` family 등록
4. **`workflow-source/workflow_kit/common/patching.py`** — `apply_robust_patch_detailed` helper 신규 (per-block detail) + 기존 `apply_robust_patch` wrapper
5. **`workflow-source/skills/robust_patcher/scripts/run_robust_patcher.py`** (신규, 180 line) — 표준 진입점 + 4종 error_code + stage_completion 통합
6. **`workflow-source/skills/robust_patcher/scripts/patch_engine.py`** (trash) — 비표준 진입점 폐기
7. **`workflow-source/skills/robust_patcher/SKILL.md`** — status → stable + 예시 실행 섹션 + 출력 계약 / error_code 분류 표
8. **`workflow-source/core/skill_beta_criteria.md`** — §3 표 stable 상태 갱신 + §3.1 3차 batch 정합 검증
9. **`workflow-source/core/workflow_skill_catalog.md`** — §2 표 robust-patcher stable + §5 runtime script ✅ 갱신
10. **`workflow-source/tests/check_robust_patcher.py`** (신규, 148 line) — 5 case smoke test
11. **`workflow-source/examples/output_samples/*.json`** (24 file) — tool_version v0.11.19-beta → v0.11.20-beta housekeeping
12. **`workflow-source/schemas/generated_output_schemas.json`** — runtime contracts 와 정합 regenerate (`robust_patcher` family 등록)
13. **`workflow-source/pyproject.toml`** — version bump `0.11.20` → `0.11.21`
14. **`workflow-source/workflow_kit/__init__.py`** — `__version__` auto-sync (3-tier fallback chain)

## GitHub release

- Tag: `v0.11.21-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌ (`patch_engine.py` 폐기는 동일 skill 의 다른 진입점 간 변경 — migration 가이드 release note 본문 참조)
- PyPI 배포: ❌ (GitHub Releases only)
- Workflow: `pre-check + tag push + gh release` 한 cycle (v0.7.21+ 정공법)

## Migration note (`patch_engine.py` → `run_robust_patcher.py`)

이전 release 에서 `patch_engine.py` 로 호출하던 caller 는 다음 변경 필요:
```diff
- python3 skills/robust_patcher/scripts/patch_engine.py --file X --patch-file Y
+ python3 skills/robust_patcher/scripts/run_robust_patcher.py --file X --patch-file Y
```
동일한 CLI flag (`--file`, `--patch-file`) 지원. 신규 `--dry-run` flag 추가. **breaking change 아님** (skill 내부 진입점 변경, 동일 skill 의 다른 path).

## 다음 release (v0.11.22 candidate)

- **automated-repro-scaffold stable 승격** — v0.11.21 와 같은 1 skill = 1 release 패턴. Pydantic schema 정합 + error_code 3종 + scripts/ 구조 통일 + smoke test 신규.
- **또는 git-conflict-resolver stable 승격** — spec.md 신규 + Pydantic schema 정합 + error_code 3종 + smoke test.
- **또는 누적 housekeeping** — sample drift 자동화, R-A follow-up part 4 deferred 해소 등.

## 메모리 layer (memory → commit → push 흐름 정합)

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.21 (1 skill stable + per-block detail)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.21 entry
- `ai-workflow/memory/release/v0.11.21/backlog/2026-07-01.md` (per-release detail)