# MCP

- 문서 목적: 표준 워크플로우에서 공통으로 재사용할 MCP 구현을 배치할 위치와 역할을 안내한다.
- 범위: 향후 추가할 MCP 서버 또는 도구 구현의 목적과 초기 도입 후보
- 대상 독자: AI agent 설계자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `../core/workflow_mcp_candidate_catalog.md`

## 현재 상태

- 아직 실제 MCP 구현 코드는 없다.
- 현재는 `core/workflow_mcp_candidate_catalog.md` 의 카탈로그를 기준으로 어떤 MCP 를 먼저 구현할지 정하는 단계다.

## 1차 구현 후보

- `latest_backlog`
- `check_doc_metadata`
- `check_doc_links`
- `create_backlog_entry`
