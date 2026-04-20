# Workflow Kit Roadmap

- 문서 목적: `standard_ai_workflow` 저장소의 현재 성숙도와 다음 단계 작업을 상위 로드맵 형태로 정리한다.
- 범위: 현재 단계 평가, 단계별 목표, 우선순위 로드맵, 완료 기준, 권장 작업 순서
- 대상 독자: 저장소 관리자, AI workflow 설계자, 구현자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-20
- 관련 문서: `./project_status_assessment.md`, `./workflow_skill_catalog.md`, `./workflow_mcp_candidate_catalog.md`, `./output_schema_guide.md`, `./prototype_promotion_scope.md`, `../skills/README.md`, `../mcp/README.md`, `../examples/end_to_end_skill_demo.md`, `../examples/end_to_end_mcp_demo.md`, `../examples/output_samples/README.md`

## 1. 현재 단계

현재 저장소는 아래 4단계 중 3단계 중후반에 해당한다.

1. 개념 정리 단계
2. 표준 문서와 템플릿 분리 단계
3. 실행 가능한 프로토타입 도입 단계
4. 다수 프로젝트 실운영 검증 단계

현재 판단 근거:

- 공통 표준, 템플릿, 카탈로그 문서가 정리돼 있다.
- 샘플 프로젝트 문서 세트가 있다.
- 문서 무결성 검사 스크립트가 있다.
- 1차 핵심 skill 4종과 2차 skill 2종에 상세 스펙과 실행형 프로토타입이 있다.
- 우선순위 1 MCP 5종에 프로토타입 구조와 실행 스크립트가 있다.
- skill/MCP 모두 end-to-end 데모 문서가 있다.
- skill 통합 demo runner 가 실제로 순차 실행된다.
- 출력 스키마 가이드와 대표 JSON 샘플 허브가 있다.
- bootstrap, harness overlay, harness package export 까지 동작한다.
- 기존 프로젝트 bootstrap 이후 후속 온보딩 runner 가 있다.
- 2차 MCP 후보인 `check_quickstart_stale_links` 프로토타입이 있다.
- reusable package / MCP server 승격 범위 문서가 있다.
- `workflow_kit/common` 패키지 루트와 1차 공통 유틸 추출이 시작됐다.

아직 4단계가 아닌 이유:

- 실제 MCP server packaging 또는 transport 계층이 없다.
- skill 과 MCP 출력 계약은 문서화됐지만, 모든 프로토타입 샘플과 실패 규칙까지 완전히 고정되지는 않았다.
- 여러 실제 프로젝트에 시범 적용한 결과가 없다.
- MCP server packaging 은 아직 시작되지 않았다.
- 공통 라이브러리 추출은 `workflow_kit/common` 기준으로 1차 착수 상태다.

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
- [../skills/validation-plan/SKILL.md](../skills/validation-plan/SKILL.md)
- [../skills/code-index-update/SKILL.md](../skills/code-index-update/SKILL.md)

### 실행형 MCP 프로토타입

- [../mcp/latest-backlog/MCP.md](../mcp/latest-backlog/MCP.md)
- [../mcp/check-doc-metadata/MCP.md](../mcp/check-doc-metadata/MCP.md)
- [../mcp/check-doc-links/MCP.md](../mcp/check-doc-links/MCP.md)
- [../mcp/create-backlog-entry/MCP.md](../mcp/create-backlog-entry/MCP.md)
- [../mcp/suggest-impacted-docs/MCP.md](../mcp/suggest-impacted-docs/MCP.md)
- [../mcp/check-quickstart-stale-links/MCP.md](../mcp/check-quickstart-stale-links/MCP.md)

### 데모와 검증

- skill 흐름 데모: [../examples/end_to_end_skill_demo.md](../examples/end_to_end_skill_demo.md)
- MCP 흐름 데모: [../examples/end_to_end_mcp_demo.md](../examples/end_to_end_mcp_demo.md)
- bootstrap 생성물 샘플: [../examples/bootstrap_output_samples.md](../examples/bootstrap_output_samples.md)
- 출력 샘플 허브: [../examples/output_samples/README.md](../examples/output_samples/README.md)
- 문서 무결성 검사: [../tests/check_docs.py](../tests/check_docs.py)
- bootstrap 스모크 검사: [../tests/check_bootstrap.py](../tests/check_bootstrap.py)
- 2차 skill 스모크 검사: [../tests/check_validation_plan.py](../tests/check_validation_plan.py), [../tests/check_code_index_update.py](../tests/check_code_index_update.py)
- 기존 프로젝트 온보딩 스모크 검사: [../tests/check_existing_project_onboarding.py](../tests/check_existing_project_onboarding.py)
- quickstart stale 링크 스모크 검사: [../tests/check_quickstart_stale_links.py](../tests/check_quickstart_stale_links.py)
- 기존 프로젝트 온보딩 runner: [../scripts/run_existing_project_onboarding.py](../scripts/run_existing_project_onboarding.py)

## 3. 상위 목표

다음 단계의 상위 목표는 아래 세 가지다.

1. 문서와 프로토타입을 공용 계약 중심으로 정리한다.
2. 개별 프로토타입을 연결해 실제 workflow kit 형태를 만든다.
3. 둘 이상의 실제 프로젝트에서 적용 가능한 수준까지 검증한다.

## 4. 현재까지 완료된 축

### 완료 또는 사용 가능한 상태

- 공통 코어 문서, 템플릿, 하네스 가이드, 전역 snippet 가이드가 정리돼 있다.
- bootstrap 스크립트가 신규 프로젝트와 기존 프로젝트 도입 모드를 모두 지원한다.
- Codex/OpenCode 오버레이 생성, export, 적용 가이드가 있다.
- skill 6종과 MCP 6종의 실행형 프로토타입이 있다.
- skill 통합 demo runner 와 end-to-end 문서가 있다.
- 출력 스키마 가이드와 skill/MCP 대표 출력 샘플 허브가 있다.
- 사용자 노출 산출물은 한국어, 내부 처리는 간결하게 유지한다는 운영 원칙이 core 문서와 bootstrap 생성물에 반영돼 있다.
- 기존 프로젝트 bootstrap 이후 assessment -> backlog/handoff -> validation/code-index 순으로 이어지는 후속 루틴이 있다.
- 승격 범위 문서가 있어 package/server 화 대상을 분리해서 계획할 수 있다.
- `workflow_kit/common` 패키지에 경로/Markdown/메타데이터 공통 유틸이 추출되기 시작했다.

### 아직 비어 있는 축

- 공통 실패 출력 규칙과 `error_code` 수준 계약
- 읽기 전용 MCP 묶음 server 화
- profile / backlog / handoff / changed-file 분류 계열의 추가 reusable package 추출
- 실제 저장소 시범 적용 결과
- 쓰기 성격 draft MCP 의 permission 경계 정리

## 5. 다음 우선순위 로드맵

### 우선순위 1: 공통 실패 계약과 schema 고정

현재 상태:

- `core/output_schema_guide.md` 는 이미 존재한다.
- skill/MCP 대표 출력 JSON 샘플 허브가 있다.
- `status`, `tool_version`, `warnings` 공통 필드는 1차 정리됐다.
- 다만 `error`, `source_context`, `error_code` 수준의 실패 계약은 아직 더 고정할 여지가 있다.

목표:

- 실패 시 공통 출력 규칙과 `error`/`warnings`/`source_context` 사용 기준을 더 명확히 한다.
- 필요하면 `error_code`, `status`, `tool_version` 같은 필드를 추가로 정의한다.
- 대표 샘플이 이 계약을 따르도록 정렬한다.

권장 산출물:

- `examples/output_samples/*.json`
- `core/output_schema_guide.md` 보강
- 필요 시 `schemas/` 또는 실패 규칙 부록 문서

완료 기준:

- 같은 성격의 경고/실패 필드가 이름과 의미 면에서 과도하게 흩어지지 않는다.
- 샘플과 실제 프로토타입 출력이 같은 실패 계약을 공유한다.
- 실패 케이스 샘플과 예외 종료 스크립트 정리가 따라온다.

### 우선순위 2: 기존 프로젝트 온보딩 자동 루틴 강화

현재 상태:

- bootstrap 의 `existing` 모드는 `repository_assessment.md` 와 초기 문서 세트를 생성한다.
- `run_existing_project_onboarding.py` 가 assessment 결과를 읽고 backlog/handoff/validation/code-index 후속 단계를 이어준다.
- `existing_project_onboarding_contract.md` 로 입력 계약과 단계별 연결 규칙이 문서화됐다.
- 다음 단계는 runner 출력 샘플과 하네스 연결 방식 정리다.

목표:

- 기존 프로젝트 도입 직후에 `repository_assessment.md`, inferred command, backlog/handoff 초안을 읽고
  `validation-plan`, `code-index-update` 같은 후속 프로토타입을 일관된 계약으로 이어준다.
- 신규 프로젝트용 진입과 기존 프로젝트용 진입의 차이를 더 명확히 드러낸다.
- 후속 단계가 어떤 조건에서 생략/경고/추가되는지 명시한다.
- 하네스가 이 결과를 어떻게 소비할지 연결 지점을 짧은 가이드로 정리한다.

권장 산출물:

- 기존 프로젝트 온보딩 runner 또는 bootstrap 후속 스크립트
- 온보딩 흐름 문서
- 단계별 입력/출력 전달 규칙

완료 기준:

- 기존 프로젝트 도입 직후 어떤 프로토타입을 순서대로 실행해야 하는지 자동 또는 반자동으로 재현 가능하다.
- assessment 결과와 후속 skill 출력의 연결이 문서와 코드로 설명된다.
- 온보딩 runner 출력이 샘플/가이드와 어긋나지 않는다.

### 우선순위 3: reusable package 및 MCP server 승격 착수

목표:

- 시작된 `workflow_kit/common` 추출을 profile/backlog/handoff 파서와 changed-file 분류까지 확장하고 읽기 전용 MCP 묶음 server 의 최소 엔트리포인트를 설계한다.

권장 대상:

- profile / backlog / handoff 파서
- metadata / link / quickstart 검사 유틸
- `latest_backlog`, `check_doc_metadata`, `check_doc_links`, `suggest_impacted_docs`, `check_quickstart_stale_links`

완료 기준:

- 기존 스크립트가 공통 라이브러리를 호출하도록 재구성된다.
- 읽기 전용 MCP server 1호 범위가 문서 수준이 아니라 코드 구조 수준으로 시작된다.
- `workflow_kit/` 패키지 루트가 향후 server 내부 구현에서도 재사용 가능한 구조로 정리된다.

### 우선순위 4: 실제 적용 검증

목표:

- 실제 저장소에 시범 적용하거나, 최소 1개의 추가 실제 사례를 문서화한다.

권장 산출물:

- 실제 적용 기록
- 적용 전/후 차이 요약

완료 기준:

- 현재 규칙이 특정 샘플에 과도하게 맞춰진 것은 아닌지 실제 피드백으로 검증 가능하다.
- 복사 적용 시 어떤 문서를 어디까지 바꾸면 되는지 더 명확해진다.

## 6. 권장 2주 순서

### 1주차

- 출력 실패 규칙 정리
- 온보딩 runner 입출력 계약 정리
- 공통 라이브러리 후보 모듈 경계 정리 및 1차 유틸 추출

### 2주차

- 기존 프로젝트 온보딩 흐름 문서 보강
- assessment 와 후속 skill 연결 확인
- profile/backlog 파서 package 추출 또는 읽기 전용 MCP server 엔트리포인트 초안 착수

## 7. 단계별 완료 기준

### 3단계 완료 기준

- skill 6종과 우선순위 1 MCP 5종의 출력 계약이 샘플과 함께 정리돼 있다.
- 통합 demo runner 또는 동등한 연결 실행 흐름이 있다.
- 기존 프로젝트 도입 후속 루틴의 최소 프로토타입이 있다.
- 2차 MCP 후보 1종 이상이 프로토타입 상태다.
- 데모 문서만이 아니라 실행 스크립트 수준에서 순차 흐름이 재현된다.

### 4단계 진입 기준

- 두 개 이상 프로젝트에 적용 가능한 예시 또는 시범 적용 결과가 있다.
- 공통 규칙이 과한지 여부를 운영 피드백으로 조정했다.
- MCP/skill 프로토타입 중 일부가 실제 reusable package 또는 server 형태로 승격됐다.

## 8. 현재 권장 다음 작업

현재 시점에서 가장 권장하는 다음 작업은 아래 순서다.

1. 출력 샘플의 실패/경고 케이스 보강
2. 공통 실패 계약과 schema 정리
3. 기존 프로젝트 온보딩 입출력 계약 보강
4. 실제 저장소 시범 적용 대상 선정
5. 공통 library / 읽기 전용 MCP server 착수

이 순서는 현재 저장소가 가진 자산을 “프로토타입 정렬 -> 온보딩 계약 보강 -> 실사용 검증 -> package/server 승격” 순서로 확장하는 데 초점을 둔다.

## 다음에 읽을 문서

- 상태 진단: [./project_status_assessment.md](./project_status_assessment.md)
- 출력 스키마 가이드: [./output_schema_guide.md](./output_schema_guide.md)
- skill 카탈로그: [./workflow_skill_catalog.md](./workflow_skill_catalog.md)
- 승격 범위 문서: [./prototype_promotion_scope.md](./prototype_promotion_scope.md)
- package 루트: [../workflow_kit/README.md](../workflow_kit/README.md)
- 출력 샘플 허브: [../examples/output_samples/README.md](../examples/output_samples/README.md)
- skill 허브: [../skills/README.md](../skills/README.md)
- mcp 허브: [../mcp/README.md](../mcp/README.md)
