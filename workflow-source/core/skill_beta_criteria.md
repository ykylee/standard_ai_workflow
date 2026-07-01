# Skill Beta Criteria

- 문서 목적: skill 프로토타입을 beta 수준으로 올릴 때 필요한 기준을 정의한다.
- 범위: beta-level 정의, 각 skill별 현재 수준,upgrade checklist
- 대상 독자: 개발자, 운영자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `./prototype_promotion_scope.md`, `../skills/README.md`

## 1. Beta-Level 정의

| 기준 | prototype | beta |
|------|-----------|------|
| 입력 계약 | 부분 정의 | 완전 정의 + CLI arg |
| 출력 계약 | JSON (일부) | 완전 JSON + error_code |
| 실행 방식 | 수동 단계 필요 | CLI 한 번에 실행 |
| 에러 처리 | 기본 | structured error + warnings |
| 문서 | SKILL.md (개요) | SKILL.md + 실행 예시 |
| 테스트 | 수동 | smoke test 통과 |

## 2. BetaUpgrade Checklist

- [ ] 입력 파라미터 CLI 로 정의
- [ ] 출력 JSON 스키마 문서화
- [ ] error_code 분류 최소 3종
- [ ] 실행 스크립트 단일 명령
- [ ] SKILL.md 실행 예시 추가
- [ ] smoke test 통과

## 3. 현재 Skill 수준

| skill | prototype | beta | stable | Gap |
|------|-----------|------|--------|-----|
| session-start | ✅ 실행 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| backlog-update | ✅ 실행 | ✅ beta | ✅ **stable (v0.11.20)** | completed |
| doc-sync | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| merge-doc-reconcile | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.20)** | completed |
| validation-plan | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| code-index-update | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| workflow-linter | ✅ 실행 | ✅ beta | ✅ **stable (v0.11.20)** | completed |
| project-status-assessment | ✅ 실행 | ✅ beta | ✅ **stable (v0.11.20)** | completed |
| robust-patcher | ✅ 실행 | ✅ beta | ✅ **stable (v0.11.21)** | completed |

### 3.1 Stable 승격 정합 조건 (v0.11.19 확정, v0.11.20 정합 검증)

- [x] 입력 파라미터 CLI 로 정의 (argparse `add_argument`)
- [x] 출력 JSON 스키마 문서화 (skill spec + output_sample_contracts.json)
- [x] error_code 분류 최소 3종 (`missing_required_document` / `missing_change_input` / `<skill>_runtime_error`)
- [x] 실행 스크립트 단일 명령 (`scripts/run_<skill>.py`)
- [x] SKILL.md 실행 예시 (`예시 실행` / `실행 예시` 섹션)
- [x] smoke test 통과 (`tests/check_<skill>.py` PASS)

**1차 stable 승격 batch (v0.11.19)**: session-start / doc-sync / validation-plan / code-index-update (4 skill).

**2차 stable 승격 batch (v0.11.20)**: backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment (4 skill). 각 skill 별 blocker 해소:
- backlog-update: temp dir fixture 정합 (`tests/check_backlog_update.py` 의 `state.json` 기대 path 가 `<branch>/state.json` → `<memory_dir>/state.json` 으로 v0.6.0.1 부터의 cache.py latent bug 와 정합) + `invalid_task_brief` / `backlog_write_failed` 2 error_code 추가.
- merge-doc-reconcile: `merge_conflict_detected` (`--merge-result-summary` 의 `CONFLICT` 마커 사전 차단) / `doc_index_stale` (work_backlog index 가 최신 backlog 미참조 시 사전 차단) 2 error_code 추가 + 신규 smoke test (`tests/check_merge_doc_reconcile.py`).
- workflow-linter: `os.path.normpath` 로 broken link check 의 `..` segment 정규화 (이전 v0.7.22 의 `.absolute()` 가 `..` 풀지 않아 false-positive 보고) + smoke test fixture 의 link depth 정합 (4 → 3 dot).
- project-status-assessment: 신규 `ProjectStatusAssessmentOutput` Pydantic schema (legacy `build_runner_success_result` dict emission → 다른 stable skill 의 `BaseOutput` 패턴과 정합) + `missing_required_document` error_code 추가 + 신규 smoke test (`tests/check_project_status_assessment.py`).

**3차 stable 승격 batch (v0.11.21)**: robust-patcher (1 skill). 후속 batch (v0.11.22+): automated-repro-scaffold / git-conflict-resolver (각각 별도 release).
- robust-patcher: 기존 `patch_engine.py` 스크립트 명 + 표준 `run_robust_patcher.py` 로 표준화 (scripts/ 진입점 일관성) + 신규 `RobustPatcherOutput` Pydantic schema (legacy dict emission → `BaseOutput` 패턴 정합) + `missing_required_document` / `malformed_patch_block` / `fuzzy_match_failed` / `robust_patcher_runtime_error` 4종 error_code 추가 + `apply_robust_patch_detailed` helper (per-block matched / fuzzy_score / preview detail) + `tests/check_robust_patcher.py` 5 case smoke test (exact-match / dry-run / fuzzy-fail atomic rollback / malformed / missing patch file).

## 4. BetaUpgrade 계획

- session-start: smoke test 추가 → beta완료
- backlog-update: smoke test 추가 → beta완료
- doc-sync: 쓰기 기능 확장 → beta완료
- merge-doc-reconcile: 쓰기 기능 확장 → beta완료
- validation-plan: 테스트 스캐폴딩 생성 → beta완료
- code-index-update: 인덱스 갱신 쓰기 기능 추가 → beta완료