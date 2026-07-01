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
| backlog-update | ✅ 실행 | ✅ beta | ⏸ blocker (smoke FAIL + error_code 2) | follow-up batch |
| doc-sync | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| merge-doc-reconcile | ✅ 읽기 | ✅ beta | ⏸ blocker (error_code 2) | follow-up batch |
| validation-plan | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| code-index-update | ✅ 읽기 | ✅ beta | ✅ **stable (v0.11.19)** | completed |
| workflow-linter | ✅ 실행 | ✅ beta | ⏸ blocker (smoke FAIL warning) | follow-up batch |
| project-status-assessment | ✅ 실행 | ✅ beta | ⏸ blocker (smoke FAIL + error_code 1) | follow-up batch |

### 3.1 Stable 승격 정합 조건 (v0.11.19 확정)

- [x] 입력 파라미터 CLI 로 정의 (argparse `add_argument`)
- [x] 출력 JSON 스키마 문서화 (skill spec + output_sample_contracts.json)
- [x] error_code 분류 최소 3종 (`missing_required_document` / `missing_change_input` / `<skill>_runtime_error`)
- [x] 실행 스크립트 단일 명령 (`scripts/run_<skill>.py`)
- [x] SKILL.md 실행 예시 (`예시 실행` / `실행 예시` 섹션)
- [x] smoke test 통과 (`tests/check_<skill>.py` PASS)

**1차 stable 승격 batch (v0.11.19)**: session-start / doc-sync / validation-plan / code-index-update (4 skill).

**Follow-up batch (v0.11.20+ 후보)**: backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment (4 skill). 각 skill 별 blocker 해결 후 stable 승격.

## 4. BetaUpgrade 계획

- session-start: smoke test 추가 → beta완료
- backlog-update: smoke test 추가 → beta완료
- doc-sync: 쓰기 기능 확장 → beta완료
- merge-doc-reconcile: 쓰기 기능 확장 → beta완료
- validation-plan: 테스트 스캐폴딩 생성 → beta완료
- code-index-update: 인덱스 갱신 쓰기 기능 추가 → beta완료