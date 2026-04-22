# validation-plan

- 문서 목적: `validation-plan` skill 의 역할, 입력/출력, 실행 예시를 정리한다.
- 범위: 검증 수준 판단, 권장 명령 구조화, 문서화 체크 및 미실행 항목 메모
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../../core/validation_plan_skill_spec.md`, `../../core/workflow_skill_catalog.md`

## 목적

변경된 파일과 프로젝트 프로파일을 기준으로 이번 작업에서 필요한 검증 수준과 권장 검증 항목을 구조화한다.

## 기대 입력

- `project_profile_path`
- `changed_files`
- `change_summary`

선택 입력:

- `session_handoff_path`
- `latest_backlog_path`

## 기대 출력

- 감지된 변경 유형 요약
- 권장 검증 수준
- 실행 권장 명령 목록
- 추가 확인이 필요한 명령 목록
- 문서화 체크 항목
- 증빙 기대값
- 미실행 가능 항목과 기록 위치 힌트
- 경고와 신뢰도 메모

## 권한 경계

- 현재 프로토타입은 읽기 전용이다.
- 프로젝트 프로파일, handoff, backlog 를 읽을 수 있다.
- 테스트나 빌드 명령은 직접 실행하지 않는다.
- 실제 명령 실행과 상태 갱신은 호출한 agent 또는 후속 automation 이 담당한다.

## 구현 메모

- 변경 파일만으로 분류가 어려우면 `change_summary` 를 보조 입력으로 사용한다.
- 프로젝트 프로파일의 `기본 명령` 과 `프로젝트 특화 검증 포인트` 를 우선 해석한다.
- 출력은 보수적으로 생성하고, 확신이 낮은 항목은 `commands_requiring_confirmation` 또는 `confidence_notes` 로 분리한다.
- 프로젝트 특화 환경 제약은 `warnings` 와 `deferred_validation_items` 에 반영한다.
- 문서 전용 변경이어도 프로젝트 프로파일에 빠른 테스트가 정의돼 있으면 기본 회귀 확인 명령을 함께 제안한다.

## 프로토타입 실행

```bash
python3 skills/validation-plan/scripts/run_validation_plan.py \
  --project-profile-path examples/acme_delivery_platform/project_workflow_profile.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --latest-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --changed-file app/jobs/delivery_sync.py \
  --changed-file docs/operations/runbooks/delivery-sync.md \
  --change-summary "delivery sync 재시도 로직과 운영 runbook 동시 수정"
```

## 현재 상태

- 입력/출력 계약과 읽기 전용 프로토타입이 있다.
- 실제 테스트 실행, CI 수집, 증빙 업로드는 아직 없다.
