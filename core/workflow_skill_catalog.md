# Workflow Skill Catalog

- 문서 목적: 표준 워크플로우를 skill 로 분리할 때 우선순위와 책임을 정리한다.
- 범위: skill 후보, 역할, 입력 문서, 기대 출력, 도입 우선순위
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `workflow_agent_topology.md`, `workflow_mcp_candidate_catalog.md`, `../templates/project_workflow_profile_template.md`

## 1. 1차 도입 skill

| skill | 역할 | 주요 입력 | 기대 출력 | 구현 상태 | 수동 대체 |
| --- | --- | --- | --- | --- | --- |
| `session-start` | 세션 시작 기준선 복원 | handoff, 백로그, 프로젝트 프로파일 | 현재 상태 요약, 다음 문서 경로 | 미구현 | `global_workflow_standard.md` 의 세션 시작 순서를 수동 수행 |
| `backlog-update` | 작업 등록/갱신 | 오늘 날짜 백로그, 작업 브리핑 | 신규 작업 항목 초안, 상태 갱신 문안 | 미구현 | 백로그 템플릿을 복사해 수동 갱신 |
| `doc-sync` | 문서 영향도와 허브 갱신 판단 | 변경 파일, 기준 문서, 허브 문서 | 영향 문서 후보, 허브 갱신 체크 | 미구현 | 변경 파일을 기준으로 관련 허브 문서를 수동 확인 |
| `merge-doc-reconcile` | 병합 후 문서 정합성 복구 | 병합 결과, handoff, 인덱스 문서 | 병합 후 재확정 포인트 | 미구현 | 병합 후 handoff, 허브, 색인 문서를 수동 재정리 |

## 2. 2차 도입 skill

| skill | 역할 | 주요 입력 | 기대 출력 | 구현 상태 | 수동 대체 |
| --- | --- | --- | --- | --- | --- |
| `validation-plan` | 변경 유형별 검증 수준 판단 | 변경 요약, 프로젝트 프로파일 | 검증 계획, 미실행 사유 | 미구현 | 프로젝트 프로파일과 공통 표준을 읽고 수동 판단 |
| `code-index-update` | 색인 문서 갱신 판단 | 변경 파일, 기존 색인 문서 | 갱신 필요 색인 후보 | 미구현 | 변경 경로를 기준으로 색인 문서를 수동 검토 |

## 3. 최소 입력 계약

- `session-start`: 현재 프로젝트의 handoff 문서, 백로그 인덱스, 프로젝트 프로파일 경로
- `backlog-update`: 오늘 날짜 백로그 경로 또는 생성 대상 날짜, 작업명, 작업 브리핑
- `doc-sync`: 변경 파일 목록, 기준 문서 후보, 허브 문서 후보
- `merge-doc-reconcile`: 병합 후 상태 문서와 허브 문서 경로

## 4. 상세 스펙 진행 상태

- `session-start`: 상세 입력/출력 계약 초안 있음
- 참고 문서: [./session_start_skill_spec.md](./session_start_skill_spec.md)
- `backlog-update`: 상세 입력/출력 계약 초안 있음
- 참고 문서: [./backlog_update_skill_spec.md](./backlog_update_skill_spec.md)
- `doc-sync`: 상세 입력/출력 계약 초안 있음
- 참고 문서: [./doc_sync_skill_spec.md](./doc_sync_skill_spec.md)
- `merge-doc-reconcile`: 상세 입력/출력 계약 초안 있음
- 참고 문서: [./merge_doc_reconcile_skill_spec.md](./merge_doc_reconcile_skill_spec.md)

## 5. 설계 원칙

- skill 은 정책 원문이 아니라 절차와 판단 순서를 담당한다.
- skill 은 가능하면 프로젝트 프로파일을 읽고 분기해야 한다.
- tool 이 없어도 최소 수동 절차는 남아 있어야 한다.

## 다음에 읽을 문서

- `session-start` 상세 스펙: [./session_start_skill_spec.md](./session_start_skill_spec.md)
- `backlog-update` 상세 스펙: [./backlog_update_skill_spec.md](./backlog_update_skill_spec.md)
- `doc-sync` 상세 스펙: [./doc_sync_skill_spec.md](./doc_sync_skill_spec.md)
- `merge-doc-reconcile` 상세 스펙: [./merge_doc_reconcile_skill_spec.md](./merge_doc_reconcile_skill_spec.md)
- MCP 후보 카탈로그: [./workflow_mcp_candidate_catalog.md](./workflow_mcp_candidate_catalog.md)
- agent 토폴로지: [./workflow_agent_topology.md](./workflow_agent_topology.md)
