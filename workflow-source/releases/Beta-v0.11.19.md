# Beta v0.11.19 — 1차 batch 4 skill stable 승격 (2026-07-01)

> Phase 12 의 *운영 안정화 + governance 후속* release. v0.11.18 (FULL mypy strict 공식 봉인) 의 후속으로, roadmap §8 Phase 12 in-progress 의 "**11 beta skill stable 승격 1차 batch**" deliverable. v0.5.10-beta 부터 beta 상태로 운영된 **4 skill** (session-start / doc-sync / validation-plan / code-index-update) 의 **stable** 채널 승격 + spec layer 동기화. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1차 batch 4 skill stable 승격)

### Stable 승격 정합 조건 (v0.11.19 확정, 6 항목)

skill_beta_criteria.md 의 정합 조건 6개 모두 충족 확인:

- [x] **입력 파라미터 CLI 정의** — `parser.add_argument()` argparse 정의
- [x] **출력 JSON 스키마 문서화** — skill spec + `output_sample_contracts.json` + `generated_output_schemas.json`
- [x] **error_code 분류 최소 3종** — `missing_required_document` / `missing_change_input` / `<skill>_runtime_error`
- [x] **실행 스크립트 단일 명령** — `scripts/run_<skill>.py` 1 entry
- [x] **SKILL.md 실행 예시** — `예시 실행` 또는 `실행 예시` 섹션
- [x] **smoke test 통과** — `tests/check_<skill>.py` PASS

### Stable 승격된 4 skill

| Skill | Smoke test | error_code | Spec | Cycle 통합 | Status |
|---|---|---|---|---|---|
| `session-start` | ✅ PASS (92 line) | 3종 | session_start_skill_spec.md (348 line) | stage_completion + purpose_context + R-A trigger | **stable** |
| `doc-sync` | ✅ PASS (116 line) | 3종 | doc_sync_skill_spec.md (289 line) | stage_completion + purpose_context | **stable** |
| `validation-plan` | ✅ PASS (148 line) | 3종 | validation_plan_skill_spec.md (161 line) | stage_completion + automated_repro_scaffold 연동 | **stable** |
| `code-index-update` | ✅ PASS (144 line) | 3종 | code_index_update_skill_spec.md (138 line) | stage_completion | **stable** |

### File 변경 (8 file, +19/-4)

1. **`skills/session-start/SKILL.md`** — `- 상태: beta` → `- 상태: stable (v0.11.19 stable 승격)`
2. **`skills/doc-sync/SKILL.md`** — 동
3. **`skills/validation-plan/SKILL.md`** — 동
4. **`skills/code-index-update/SKILL.md`** — 동
5. **`core/skill_beta_criteria.md`** — 표 갱신 (4 skill ✅ stable + 4 skill ⏸ blocker) + §3.1 Stable 승격 정합 조건 추가
6. **`core/workflow_skill_catalog.md`** — §1 + §2 표 갱신 (4 skill ✅ Stable + 4 skill ⏸ blocker)
7. **`workflow-source/pyproject.toml`** — version bump `0.11.18` → `0.11.19`
8. **`workflow-source/workflow_kit/__init__.py`** — `__version__` auto-sync (3-tier fallback chain)

## Follow-up batch (v0.11.20+ 후보)

아직 beta 상태인 **4 skill** 별 blocker 해결 후 stable 승격:

| Skill | Blocker | 해결 정공법 |
|---|---|---|
| `backlog-update` | smoke FAIL (state.json 부재) + error_code 2 (3종 미달) | smoke test 의 temp dir fixture 정합 + error_code 추가 (`invalid_task_brief` / `backlog_write_failed`) |
| `merge-doc-reconcile` | error_code 2 (3종 미달) | error_code 추가 (`merge_conflict_detected` / `doc_index_stale`) |
| `workflow-linter` | smoke FAIL (warning) | `task_status_mismatch` 등 7 linter rule 의 정합 verify + 회귀 fix |
| `project-status-assessment` | smoke FAIL + error_code 1 | script 의 output schema 정합 + error_code 추가 |

## 누적 결과

| 항목 | v0.11.18 | **v0.11.19** |
|---|---|---|
| Stable skill | 0 (all beta) | **4** (session-start / doc-sync / validation-plan / code-index-update) |
| Beta skill | 11 | **7** |
| Prototype skill | 4 | 4 |
| Stable 채널 후속 | n/a | **7** (v0.11.20+ 후속 batch) |

## 검증

- `workflow-source/tests/check_session_start.py`: PASS
- `workflow-source/tests/check_doc_sync.py`: PASS
- `workflow-source/tests/check_validation_plan.py`: PASS
- `workflow-source/tests/check_code_index_update.py`: PASS
- `workflow-source/tests/check_baselines_compliance.py`: 16 tests PASS
- `workflow-source/tests/check_output_samples.py`: 24 JSON files PASS
- `workflow-source/tests/check_output_json_schema.py`: PASS
- `workflow-source/tests/check_wiki_source_rule.py` (V-R9): PASS
- `workflow-source/tests/check_generated_schema_validation.py`: PASS
- `mypy --no-incremental --strict workflow-source/workflow_kit/`: **0 errors, 107 file clean** ✅
- GH Actions mypy-strict workflow: cumulative 정합 유지 (Layer 1 ✅)

## GitHub release

- Tag: `v0.11.19-beta`
- Pre-release: yes
- Notes: 본 파일
- Breaking change: ❌
- PyPI 배포: ❌ (GitHub Releases only)
- Workflow: `pre-check + tag push + gh release` 한 cycle (v0.7.21+ 정공법)

## 다음 release (v0.11.20 candidate)

- **2차 batch 4 skill stable 승격** — backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment 의 blocker 해결 후 승격. memory §6 "1 follow-up = 1 deliverable × N release 분할" 정합 — 4 skill blocker 해결 후 1 release (또는 2 release 분할).
- **또는 v1.0.0 milestone prep** — Phase 12 종료 + SemVer stable guarantee 2-year 진입 평가.
- **또는 다른 housekeeping** — beta → stable transition 의 spec / runtime / wiki layer 동기화 정합 verify.

## 메모리 layer (memory → commit → push 흐름 정합)

- `ai-workflow/memory/active/work_backlog.md` index entry: v0.11.19 (4 skill stable)
- `ai-workflow/memory/active/state.json` recent_done_items: v0.11.19 entry
- `ai-workflow/memory/release/v0.11.19/backlog/2026-07-01.md` (per-release detail)