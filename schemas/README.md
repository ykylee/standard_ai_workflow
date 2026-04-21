# Schemas

- 문서 목적: 출력 샘플과 smoke test 가 공유하는 정적 계약 파일의 위치와 역할을 설명한다.
- 범위: 현재 포함된 schema 초안, 사용 방식, 한계
- 대상 독자: AI workflow 설계자, 구현자, 테스트 작성자
- 상태: draft
- 최종 수정일: 2026-04-22
- 관련 문서: `../core/output_schema_guide.md`, `../tests/README.md`, `../workflow_kit/README.md`

## 1. 목적

이 디렉터리는 현재 저장소의 실행형 프로토타입 출력 계약을 정적 파일 형태로도 유지하기 위한 초안 위치다.

현재 단계에서는 완전한 JSON Schema 생태계나 외부 validator 의존성을 바로 도입하기보다, 아래 목표를 우선한다.

- output sample 과 smoke test 가 같은 계약 파일을 공유
- contract 변경이 문서와 코드 사이에서 쉽게 보이도록 유지
- 이후 JSON Schema 또는 MCP/server 응답 계약으로 승격하기 쉬운 중간 산출물 확보

## 2. 현재 포함된 schema 초안

- [output_sample_contracts.json](./output_sample_contracts.json)

이 파일은 아래 정보를 담는다.

- 공통 필수 필드
- sample family 별 success/error 필수 필드
- `tool_version` 단일 출처가 `workflow_kit.__version__` 임을 가리키는 메타데이터

## 3. 현재 사용 방식

- `tests/check_output_samples.py` 가 이 파일을 읽어 대표 JSON 샘플의 핵심 필드 계약을 검증한다.
- `workflow_kit/common/output_contracts.py` 는 같은 계약을 Python 코드에서 재사용하기 위한 런타임 표현이다.
- 두 표현이 어긋나면 smoke test 가 실패하도록 유지하는 것이 권장된다.

## 4. 현재 한계

- 아직 완전한 JSON Schema draft 문서나 외부 validator 연동까지는 포함하지 않는다.
- 타입 수준 검증은 제한적이며, 현재는 필수 키와 family 별 핵심 필드 중심이다.
- nested payload 전체 구조를 완전 검증하지는 않는다.

## 5. 다음 확장 후보

- family 별 허용 상태값과 nested object 필드 제약 추가
- runner/skill/MCP 공통 에러 코드 분류 체계 문서화
- JSON Schema draft 형식으로의 승격

## 다음에 읽을 문서

- 출력 스키마 가이드: [../core/output_schema_guide.md](../core/output_schema_guide.md)
- 테스트 가이드: [../tests/README.md](../tests/README.md)
- package 루트: [../workflow_kit/README.md](../workflow_kit/README.md)
