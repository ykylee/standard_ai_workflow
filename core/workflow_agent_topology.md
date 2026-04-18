# Workflow Agent Topology

- 문서 목적: 배포형 표준 워크플로우에서 사용할 agent 역할과 권한 경계를 요약한다.
- 범위: 추천 agent 목록, 책임, 입력/출력, 상태 문서 수정 원칙
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `workflow_skill_catalog.md`, `workflow_mcp_candidate_catalog.md`, `../templates/project_workflow_profile_template.md`

## 1. 1차 필수 agent

| agent | 역할 | 입력 | 출력 |
| --- | --- | --- | --- |
| `session-orchestrator` | 세션 시작 기준선 복원 | handoff, 백로그, 프로젝트 프로파일 | 현재 상태 요약, 다음 행동 |
| `backlog-steward` | 작업 등록/갱신 보조 | 오늘 날짜 백로그, 작업 브리핑 | 작업 항목 초안, 상태 갱신 초안 |
| `doc-sync-guardian` | 문서 동기화 점검 | 변경 파일, 기준 문서, 허브 문서 | 영향 문서 후보, stale 경고 |

## 2. 2차 확장 agent

| agent | 역할 | 입력 | 출력 |
| --- | --- | --- | --- |
| `validation-coordinator` | 검증 수준 결정 | 변경 요약, 프로젝트 프로파일 | 검증 계획, 결과 요약 |
| `merge-reconciler` | 병합 후 정합성 복구 | 병합 결과, handoff, 허브 문서 | 재확정 포인트 |
| `workflow-governor` | 공통/특화 규칙 경계 관리 | 표준 문서, 프로젝트 프로파일 | 체계 변경 제안 |

## 3. 권한 매트릭스

| agent | 읽기 가능 | 수정 가능 | 수정 금지 또는 주의 |
| --- | --- | --- | --- |
| `session-orchestrator` | handoff, 백로그, 프로젝트 프로파일 | 기본적으로 없음 | 상태 문서를 직접 완료 처리하지 않음 |
| `backlog-steward` | 오늘 날짜 백로그, handoff, 프로젝트 프로파일 | 날짜별 백로그 초안, 상태 갱신 초안 | 검증 없이 `done` 확정 금지 |
| `doc-sync-guardian` | 기준 문서, 허브 문서, 변경 파일 목록 | 허브 갱신 제안 문안 | 상태 문서를 직접 사실 확정 용도로 수정하지 않음 |
| `validation-coordinator` | 프로젝트 프로파일, 검증 문서, 결과 요약 | 검증 계획/요약 초안 | 테스트 결과를 확인하지 않고 성공 표기 금지 |
| `merge-reconciler` | 병합 후 handoff, 백로그, 허브 문서 | 병합 후 재확정 초안 | 병합 전 상태를 기계적으로 합치지 않음 |
| `workflow-governor` | 표준 문서, 프로젝트 프로파일, skill/MCP 카탈로그 | 체계 변경 제안 문안 | 특정 프로젝트 상태 문서를 직접 운영하지 않음 |

## 4. 상태 문서 수정 원칙

- 존재하지 않는 백로그 파일을 사실처럼 쓰지 않는다.
- 검증하지 않은 작업을 `done` 으로 바꾸지 않는다.
- 외부 리뷰 코멘트보다 저장소 실제 상태를 먼저 확인한다.
- 상태 문서는 가능한 한 보수적으로 수정한다.

## 다음에 읽을 문서

- 프로젝트 프로파일 템플릿: [../templates/project_workflow_profile_template.md](../templates/project_workflow_profile_template.md)
- skill 카탈로그: [./workflow_skill_catalog.md](./workflow_skill_catalog.md)
