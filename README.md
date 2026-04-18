# Standard AI Workflow

- 문서 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 범위: 공통 표준 문서, 프로젝트 프로파일 템플릿, 세션 상태 문서 템플릿, skill/MCP/agent 설계 참고 문서, 분리 체크리스트
- 대상 독자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `./core/global_workflow_standard.md`, `./core/workflow_agent_topology.md`, `./split_checklist.md`
- 상태 진단 문서: `./core/project_status_assessment.md`

## 1. 이 폴더의 역할

이 저장소는 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 워크플로우를 독립 패키지처럼 관리하기 위한 저장소다. 문서와 템플릿만으로도 최소 운영이 가능해야 하며, 이후 `skill`, `MCP`, `agent` 구현이 추가되더라도 같은 구조 안에서 확장할 수 있어야 한다.

핵심 원칙:

- 공통 규칙은 코어 문서로 둔다.
- 저장소별 차이는 프로젝트 프로파일 템플릿에 적는다.
- 세션 상태 문서는 템플릿으로 제공한다.
- skill, MCP, agent 는 설계 카탈로그로 먼저 제공하고, 실제 구현은 프로젝트 상황에 맞게 선택 적용한다.
- 이 저장소만 읽어도 구조를 이해할 수 있게 외부 저장소 의존 링크를 최소화한다.

## 2. 폴더 구성

| 경로 | 역할 |
| --- | --- |
| `core/` | 여러 프로젝트에 공통 적용할 코어 문서 |
| `templates/` | 프로젝트와 세션 상태 문서 템플릿 |
| `skills/` | 향후 공통 skill 구현 위치 |
| `mcp/` | 향후 공통 MCP 구현 위치 |
| `examples/` | 샘플 프로파일과 도입 예시 위치 |
| `tests/` | 링크/템플릿/구현 smoke test 위치 |
| `split_checklist.md` | 별도 프로젝트로 분리할 때 수행할 체크리스트 |

## 3. 현재 구현 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 공통 표준 문서 | 사용 가능 | 바로 복사 가능 |
| 프로젝트/세션 템플릿 | 사용 가능 | 값 채우기 필요 |
| 샘플 도입 예시 | 사용 가능 | `examples/acme_delivery_platform/` 참고 |
| skill 프로토타입 | 사용 가능 | `skills/` 및 end-to-end 데모 참고 |
| skill 카탈로그 | 설계 완료, 프로토타입 포함 | 1차 핵심 skill 실행형 초안 있음 |
| MCP 카탈로그 | 설계 완료, 구현 미포함 | 실제 MCP 서버/도구 없음 |
| agent 토폴로지 | 설계 완료, 구현 미포함 | 역할과 권한 경계 중심 |

## 4. 권장 도입 순서

1. `core/global_workflow_standard.md` 를 기준 문서로 읽는다.
2. 새 저장소에 `project_workflow_profile_template.md` 를 복사해 프로젝트 특화 규칙을 채운다.
3. `templates/` 아래 세션/백로그 템플릿을 해당 저장소 문서 구조에 맞게 배치한다.
4. `core/workflow_skill_catalog.md`, `core/workflow_mcp_candidate_catalog.md`, `core/workflow_agent_topology.md` 를 읽고 도입 범위를 정한다.
5. 첫 도입은 세션 시작, 백로그 갱신, 문서 동기화처럼 영향이 큰 흐름부터 시작한다.

## 5. 다른 프로젝트에 적용할 때 최소 복사 세트

최소 세트:

- `core/global_workflow_standard.md`
- `templates/project_workflow_profile_template.md`
- `templates/session_handoff_template.md`
- `templates/work_backlog_template.md`
- `templates/daily_backlog_template.md`

확장 세트:

- `core/workflow_skill_catalog.md`
- `core/workflow_mcp_candidate_catalog.md`
- `core/workflow_agent_topology.md`

## 6. 별도 프로젝트로 분리할 때 권장 구조

- `README.md`
- `split_checklist.md`
- `core/`
- `templates/`

실제 구현이 시작되면 아래를 추가한다.

- `skills/`
- `mcp/`
- `examples/`
- `tests/`

## 7. 현재 한계

- 이 폴더는 배포용 문서 패키지이며, 실제 skill/MCP 구현 코드를 포함하지는 않는다.
- 프로젝트별 문서 경로와 명령 체계는 `project_workflow_profile_template.md` 를 채운 뒤에야 완성된다.
- 여러 프로젝트에서 시범 적용하기 전에는 공통 규칙이 과도한지 여부를 추가 검증해야 한다.

## 8. 수동 대체 원칙

skill/MCP 구현이 아직 없더라도 아래 문서만으로 수동 운영은 가능해야 한다.

- 세션 시작: `core/global_workflow_standard.md`
- 프로젝트 특화 규칙: `templates/project_workflow_profile_template.md`
- 상태 문서 템플릿: `templates/`

## 다음에 읽을 문서

- 공통 코어 표준: [core/global_workflow_standard.md](./core/global_workflow_standard.md)
- 프로젝트 상태 진단: [core/project_status_assessment.md](./core/project_status_assessment.md)
- 샘플 도입 예시: [examples/README.md](./examples/README.md)
- end-to-end 데모: [examples/end_to_end_skill_demo.md](./examples/end_to_end_skill_demo.md)
- end-to-end MCP 데모: [examples/end_to_end_mcp_demo.md](./examples/end_to_end_mcp_demo.md)
- 프로젝트 프로파일 템플릿: [templates/project_workflow_profile_template.md](./templates/project_workflow_profile_template.md)
- agent 토폴로지: [core/workflow_agent_topology.md](./core/workflow_agent_topology.md)
- 분리 체크리스트: [split_checklist.md](./split_checklist.md)
