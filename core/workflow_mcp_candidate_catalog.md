# Workflow MCP Candidate Catalog

- 문서 목적: 표준 워크플로우를 보조할 MCP 후보를 입력/출력과 함께 정리한다.
- 범위: 탐색, 검사, 초안 생성, 영향도 추천 등 반복 작업에 적합한 MCP 후보
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `workflow_skill_catalog.md`, `workflow_agent_topology.md`

## 1. 우선순위 1

| MCP 후보 | 입력 | 출력 | 구현 상태 | 수동 대체 |
| --- | --- | --- | --- | --- |
| `latest_backlog` | 백로그 디렉터리 경로 | 최신 날짜 백로그 경로 | 미구현 | 백로그 디렉터리를 정렬해 최신 파일 확인 |
| `check_doc_metadata` | 문서 디렉터리 | 메타데이터 누락 목록 | 미구현 | Markdown 파일 첫 20줄을 수동/스크립트로 검사 |
| `check_doc_links` | 문서 디렉터리 | 끊어진 링크 목록 | 미구현 | 상대 링크 경로 존재 여부를 수동/스크립트로 검사 |
| `create_backlog_entry` | 날짜, 작업 ID, 작업명 | 백로그 항목 초안 | 미구현 | `daily_backlog_template.md` 를 복사해 수동 작성 |
| `suggest_impacted_docs` | 변경 파일 목록 | 함께 볼 문서 후보 | 미구현 | 변경 파일 기준으로 허브/기준 문서를 수동 추적 |

## 2. 우선순위 2

| MCP 후보 | 입력 | 출력 | 구현 상태 | 수동 대체 |
| --- | --- | --- | --- | --- |
| `create_session_handoff_draft` | 최신 백로그, 완료 작업 요약 | handoff 초안 | 미구현 | handoff 템플릿에 최근 완료/잔여 작업을 수동 요약 |
| `create_environment_record_stub` | 호스트 정보 | 환경 문서 초안 | 미구현 | 환경 기록 템플릿을 수동 작성 |
| `check_quickstart_stale_links` | quickstart 문서 | stale 링크 경고 | 미구현 | quickstart 링크를 기준 문서와 대조 |

## 3. 최소 입력 계약

- 문서 경로 입력은 프로젝트 프로파일에 정의된 문서 구조를 기준으로 해석한다.
- 변경 파일 목록 입력은 상대 경로 목록이면 충분하다.
- 출력은 사람이 바로 검토 가능한 텍스트 또는 구조화 목록이어야 한다.

## 4. 원칙

- 문서를 자동 확정하기보다 초안과 경고를 우선 제공한다.
- 구조화된 출력이 가능해야 한다.
- 프로젝트 특화 규칙은 프로젝트 프로파일을 입력으로 받아야 한다.

## 다음에 읽을 문서

- skill 카탈로그: [./workflow_skill_catalog.md](./workflow_skill_catalog.md)
- agent 토폴로지: [./workflow_agent_topology.md](./workflow_agent_topology.md)
