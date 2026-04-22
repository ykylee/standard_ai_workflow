# Read-Only MCP Bundle Draft

- 문서 목적: 읽기 전용 MCP 1차 묶음을 하나의 엔트리포인트로 승격할 때 현재 코드 구조와 포함 범위를 정리한다.
- 범위: 1차 포함 tool, 현재 엔트리포인트 파일, 아직 없는 transport 계층, 다음 확장 포인트
- 대상 독자: AI workflow 설계자, 구현자, MCP server 정리 담당자
- 상태: draft
- 최종 수정일: 2026-04-22
- 관련 문서: `../core/prototype_promotion_scope.md`, `../workflow_kit/README.md`, `./README.md`

## 현재 포함 범위

- `latest_backlog`
- `check_doc_metadata`
- `check_doc_links`
- `suggest_impacted_docs`
- `check_quickstart_stale_links`

이 다섯 개는 모두 읽기 전용이거나 후보/경고 출력 중심이라 1호 MCP bundle 범위로 묶기 쉽다.

## 현재 코드 진입점

- 레지스트리: `workflow_kit/server/read_only_registry.py`
- draft entrypoint: `workflow_kit/server/read_only_entrypoint.py`
- smoke test: `tests/check_read_only_mcp_server.py`

현재 entrypoint 는 아래 두 동작만 제공한다.

1. `--list-tools`
2. `--tool <name> --payload-json '{...}'`

이 단계의 목적은 transport 나 외부 MCP SDK 연동보다, “현재 읽기 전용 tool 들을 하나의 코드 구조 아래서 호출 가능한가”를 먼저 확인하는 것이다.

## 현재 한계

- 아직 정식 MCP transport 계층은 없다.
- tool schema 는 CLI flag 기반 payload 변환 수준이며, 정교한 input schema 검증은 없다.
- 현재는 하위 script 를 subprocess 로 호출하는 draft adapter 형태다.

## 다음 확장 포인트

- tool 별 input schema 문서화 또는 dataclass 기반 schema 추가
- subprocess adapter 대신 `workflow_kit/common` 함수 직접 호출 구조로 교체
- 정식 MCP SDK/transport 계층 연결
- 읽기 전용 bundle 과 초안 생성 bundle 의 permission 경계 분리
