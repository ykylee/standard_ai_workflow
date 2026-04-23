# 파일럿 후보 선정 체크리스트

- 문서 목적: 표준 AI 워크플로우를 실제 저장소에 시범 적용할 때 어떤 저장소를 먼저 고를지 일관된 기준으로 판단한다.
- 범위: 후보 선정 기준, 제외 기준, 적용 전후 비교 항목
- 대상 독자: 저장소 관리자, AI workflow 설계자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-22
- 관련 문서: `./pilot_adoption_record_template.md`, `../core/workflow_adoption_entrypoints.md`, `../core/workflow_kit_roadmap.md`

## 1. 우선 선정 기준

- 문서와 코드가 모두 있어 `existing` 모드 검증 가치가 큰 저장소인가
- 첫 세션에서 `session-start`, `validation-plan`, `code-index-update` 묶음을 실제로 적용해볼 가치가 있는 저장소인가
- 기본 실행 명령과 빠른 테스트 명령을 확인할 수 있는 저장소인가
- backlog/handoff 성격 문서를 넣어도 운영 마찰이 과도하지 않은 팀인가
- README 또는 docs 허브가 있어 `code-index-update` 검증 가치가 있는 저장소인가
- 첫 파일럿에서 권한, 보안, 외부 의존이 지나치게 많지 않은 저장소인가
- 변경 빈도가 너무 높지 않아 적용 전후 비교를 남기기 쉬운 저장소인가

## 2. 가급적 뒤로 미룰 후보

- 보안 승인 없이는 기본 실행조차 어려운 저장소
- 단일 README 외에 운영 문서가 거의 없는 저장소
- 현재 대형 마이그레이션 또는 조직 개편 중이라 문서 구조가 급변하는 저장소
- 하네스 선택, 모델 정책, 보고 언어 같은 운영 기준이 아직 합의되지 않은 팀
- CI 또는 테스트 명령이 거의 깨진 상태라 workflow 자체보다 복구 비용이 더 큰 저장소

## 3. 적용 전 확인 항목

- 도입 모드:
  - `new`
  - `existing`
- 사용할 하네스:
  - `codex`
  - `opencode`
- 실제 기본 명령 확보 여부:
  - 설치
  - 실행
  - 빠른 테스트
  - 격리 테스트
  - smoke 확인
- 문서 기준선 위치 확인 여부:
  - README
  - docs 홈
  - 운영/runbook 문서
  - 기존 backlog 또는 작업 추적 문서
- 첫 세션에서 누가 profile 값을 확정할지 담당자 지정 여부

## 4. 적용 후 비교 항목

- bootstrap 초안이 실제 저장소 구조와 얼마나 맞았는가
- onboarding runner 요약이 첫 세션 브리핑으로 충분했는가
- skill 묶음 순서가 실제 세션 진행 순서와 자연스럽게 맞았는가
- 하네스가 `onboarding_summary`, `warnings`, `orchestration_plan` 을 읽기 쉬웠는가
- output sample / 실제 runner 출력 / 문서 계약이 현장에서 어긋나지 않았는가
- backlog/handoff 도입이 실사용 습관으로 이어질 가능성이 있는가
- 문서 위치, 명령, 예외 규칙 중 자동 추정이 특히 자주 틀린 영역은 무엇인가

## 5. 최종 기록 원칙

- 파일럿마다 [./pilot_adoption_record_template.md](./pilot_adoption_record_template.md) 로 적용 기록을 남긴다.
- 최소 2개 저장소에 적용하기 전까지는 공통 규칙을 과하게 일반화하지 않는다.
- 첫 파일럿은 성공 사례보다 마찰 지점 수집 목적에 더 가깝게 본다.
