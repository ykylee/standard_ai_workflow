# Workflow Kit Package

- 문서 목적: `workflow_kit/` Python 패키지 루트의 현재 역할과 포함 범위를 설명한다.
- 범위: 현재 포함된 공통 모듈, 초기 사용처, 향후 확장 방향
- 대상 독자: AI workflow 설계자, 구현자, MCP server 정리 담당자
- 상태: draft
- 최종 수정일: 2026-04-20
- 관련 문서: `../core/prototype_promotion_scope.md`, `../core/workflow_kit_roadmap.md`, `../mcp/README.md`

## 1. 목적

`workflow_kit/` 은 문서/스크립트 수준에 흩어져 있던 공통 로직을 reusable package 로 옮기기 위한 초기 루트다. 현재는 모든 프로토타입을 한 번에 옮기지 않고, 중복이 큰 읽기 전용 MCP 유틸부터 단계적으로 정리한다.

## 2. 현재 포함된 모듈

- `common.paths`
- `common.markdown`
- `common.docs`
- `common.text`
- `common.project_docs`
- `common.change_types`

이 모듈들은 아래 책임을 가진다.

- 존재하는 경로 해석
- Markdown 상대 링크 파싱과 깨진 링크 탐지
- 문서 메타데이터 누락 필드 확인
- project profile / handoff / backlog 파싱
- changed-file 분류와 validation change type 추정

## 3. 현재 사용처

현재 아래 MCP 프로토타입이 `workflow_kit.common` 을 사용한다.

- `latest_backlog`
- `check_doc_links`
- `check_doc_metadata`
- `check_quickstart_stale_links`

현재 아래 skill/MCP 프로토타입도 `workflow_kit.common` 을 사용한다.

- `session-start`
- `validation-plan`
- `doc-sync`
- `suggest_impacted_docs`
- `backlog-update`
- `merge-doc-reconcile`
- `code-index-update`

즉, 읽기 전용 MCP 1차 묶음의 공통 기반이 이제 스크립트 내부 복사 로직이 아니라 package 모듈로 이동하기 시작했다.

## 4. 다음 확장 후보

- project profile / handoff / backlog 파서
- changed-file 분류 유틸
- validation-plan 추천 로직
- code-index-update 추천 로직

## 5. 원칙

- 지금 단계에서는 작은 유틸 모듈부터 옮긴다.
- 출력 계약은 기존 프로토타입과 동일하게 유지한다.
- orchestration runner 는 나중에 package 와 MCP server 조합의 상위 레이어로 정리한다.

## 다음에 읽을 문서

- 승격 범위 문서: [../core/prototype_promotion_scope.md](../core/prototype_promotion_scope.md)
- 상위 로드맵: [../core/workflow_kit_roadmap.md](../core/workflow_kit_roadmap.md)
- mcp 허브: [../mcp/README.md](../mcp/README.md)
