# Workflow Kit Roadmap

- 문서 목적: `standard_ai_workflow` 저장소의 현재 성숙도와 다음 단계 작업을 상위 로드맵 형태로 정리한다.
- 범위: 현재 단계 평가, 단계별 목표, 우선순위 로드맵, 완료 기준, 권장 작업 순서
- 대상 독자: 저장소 관리자, AI workflow 설계자, 구현자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `./project_status_assessment.md`, `./workflow_skill_catalog.md`, `./workflow_mcp_candidate_catalog.md`, `../skills/README.md`, `../mcp/README.md`, `../examples/end_to_end_skill_demo.md`, `../examples/end_to_end_mcp_demo.md`

## 1. 현재 단계

현재 저장소는 아래 4단계 중 3단계 초입에 해당한다.

1. 개념 정리 단계
2. 표준 문서와 템플릿 분리 단계
3. 실행 가능한 프로토타입 도입 단계
4. 다수 프로젝트 실운영 검증 단계

현재 판단 근거:

- 공통 표준, 템플릿, 카탈로그 문서가 정리돼 있다.
- 샘플 프로젝트 문서 세트가 있다.
- 문서 무결성 검사 스크립트가 있다.
- 1차 핵심 skill 4종에 상세 스펙과 실행형 프로토타입이 있다.
- 우선순위 1 MCP 5종에 프로토타입 구조와 실행 스크립트가 있다.
- skill/MCP 모두 end-to-end 데모 문서가 있다.

아직 4단계가 아닌 이유:

- 실제 MCP server packaging 또는 transport 계층이 없다.
- skill 과 MCP 출력 계약이 아직 공용 스키마 문서로 고정되지 않았다.
- 여러 실제 프로젝트에 시범 적용한 결과가 없다.
- 2차 skill/MCP 후보는 아직 스펙/구현이 시작되지 않았다.

## 2. 현재 자산

### 문서와 템플릿

- 공통 코어 표준: [global_workflow_standard.md](./global_workflow_standard.md)
- 프로젝트 상태 진단: [project_status_assessment.md](./project_status_assessment.md)
- 프로젝트/세션 템플릿: [../templates/](../templates/)

### 실행형 skill 프로토타입

- [../skills/session-start/SKILL.md](../skills/session-start/SKILL.md)
- [../skills/backlog-update/SKILL.md](../skills/backlog-update/SKILL.md)
- [../skills/doc-sync/SKILL.md](../skills/doc-sync/SKILL.md)
- [../skills/merge-doc-reconcile/SKILL.md](../skills/merge-doc-reconcile/SKILL.md)

### 실행형 MCP 프로토타입

- [../mcp/latest-backlog/MCP.md](../mcp/latest-backlog/MCP.md)
- [../mcp/check-doc-metadata/MCP.md](../mcp/check-doc-metadata/MCP.md)
- [../mcp/check-doc-links/MCP.md](../mcp/check-doc-links/MCP.md)
- [../mcp/create-backlog-entry/MCP.md](../mcp/create-backlog-entry/MCP.md)
- [../mcp/suggest-impacted-docs/MCP.md](../mcp/suggest-impacted-docs/MCP.md)

### 데모와 검증

- skill 흐름 데모: [../examples/end_to_end_skill_demo.md](../examples/end_to_end_skill_demo.md)
- MCP 흐름 데모: [../examples/end_to_end_mcp_demo.md](../examples/end_to_end_mcp_demo.md)
- 문서 무결성 검사: [../tests/check_docs.py](../tests/check_docs.py)

## 3. 상위 목표

다음 단계의 상위 목표는 아래 세 가지다.

1. 문서와 프로토타입을 공용 계약 중심으로 정리한다.
2. 개별 프로토타입을 연결해 실제 workflow kit 형태를 만든다.
3. 둘 이상의 실제 프로젝트에서 적용 가능한 수준까지 검증한다.

## 4. 우선순위 로드맵

### 우선순위 1: 출력 계약 고정

목표:

- skill 4종과 우선순위 1 MCP 5종의 JSON 출력 스키마를 문서로 고정한다.
- 필수 필드, 선택 필드, 경고 필드, 실패 출력 규칙을 통일한다.

권장 산출물:

- `core/output_schema_guide.md`
- 또는 skill/MCP별 `schemas/` 디렉터리
- 예시 출력 JSON 샘플 모음

완료 기준:

- 현재 존재하는 프로토타입 출력이 모두 문서화된 필드 집합으로 설명 가능하다.
- 같은 성격의 경고/실패 필드가 이름과 의미 면에서 과도하게 흩어지지 않는다.

### 우선순위 2: 통합 실행 흐름

목표:

- `session-start -> backlog-update -> doc-sync -> merge-doc-reconcile` 흐름을 한 번에 실행해볼 수 있는 통합 demo runner 를 만든다.
- MCP 도구도 같은 흐름 안에서 필요한 위치에 재사용 가능하게 연결한다.

권장 산출물:

- `scripts/run_demo_workflow.py` 또는 유사한 통합 실행 스크립트
- skill/MCP 통합 실행 예시 문서
- 단계별 입력/출력 전달 규칙

완료 기준:

- 예시 프로젝트 문서 세트 기준으로 여러 프로토타입을 순서대로 실행할 수 있다.
- 각 단계의 출력이 다음 단계 입력으로 어떻게 이어지는지 문서와 코드에서 설명된다.

### 우선순위 3: 2차 후보 확장

목표:

- 2차 skill/MCP 후보에 대한 스펙 또는 프로토타입을 시작한다.

권장 대상:

- `validation-plan`
- `code-index-update`
- `create_session_handoff_draft`
- `check_quickstart_stale_links`

완료 기준:

- 최소 1개 skill 과 1개 MCP 가 2차 후보 영역에서 스펙 또는 프로토타입 상태로 올라온다.

### 우선순위 4: 실제 적용 검증

목표:

- 성격이 다른 두 번째 샘플 프로젝트를 추가하거나 실제 저장소에 시범 적용한다.

권장 산출물:

- 예시 프로젝트 2호
- 도입 가이드
- 적용 전/후 차이 요약

완료 기준:

- 현재 규칙이 특정 예시 프로젝트에 과도하게 맞춰진 것은 아닌지 검증 가능하다.
- 복사 적용 시 어떤 문서를 어디까지 바꾸면 되는지 명확해진다.

## 5. 2주 권장 순서

### 1주차

- 출력 스키마 가이드 문서 추가
- skill 4종 출력 예시 JSON 정리
- MCP 5종 출력 예시 JSON 정리

### 2주차

- 통합 demo runner 초안 작성
- 예시 프로젝트 기준 통합 실행 확인
- 두 번째 샘플 프로젝트 후보 선정

## 6. 단계별 완료 기준

### 3단계 완료 기준

- skill 4종과 우선순위 1 MCP 5종의 출력 계약이 문서화돼 있다.
- 통합 demo runner 또는 동등한 연결 실행 흐름이 있다.
- 데모 문서만이 아니라 실행 스크립트 수준에서 순차 흐름이 재현된다.

### 4단계 진입 기준

- 두 개 이상 프로젝트에 적용 가능한 예시 또는 시범 적용 결과가 있다.
- 공통 규칙이 과한지 여부를 운영 피드백으로 조정했다.
- MCP/skill 프로토타입 중 일부가 실제 reusable package 또는 server 형태로 승격됐다.

## 7. 현재 권장 다음 작업

현재 시점에서 가장 권장하는 다음 작업은 아래 순서다.

1. 두 번째 샘플 프로젝트 추가
2. 출력 예시 JSON 샘플 추가
3. MCP server 또는 reusable package 승격 범위 정의

이 순서는 현재 저장소가 가진 프로토타입 자산을 범용성과 재사용성 중심으로 확장하는 순서다.

## 다음에 읽을 문서

- 상태 진단: [./project_status_assessment.md](./project_status_assessment.md)
- 출력 스키마 가이드: [./output_schema_guide.md](./output_schema_guide.md)
- skill 허브: [../skills/README.md](../skills/README.md)
- mcp 허브: [../mcp/README.md](../mcp/README.md)
