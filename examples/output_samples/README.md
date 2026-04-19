# Output Samples

- 문서 목적: 실행형 skill 프로토타입의 대표 JSON 출력 예시를 한곳에서 참조할 수 있게 정리한다.
- 범위: 현재 추가된 skill 출력 샘플 파일과 사용 용도
- 대상 독자: AI workflow 설계자, skill 구현자, 테스트 작성자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-19
- 관련 문서: `../../core/output_schema_guide.md`, `../end_to_end_skill_demo.md`

## 현재 포함된 샘플

- [validation_plan.acme_delivery_platform.json](./validation_plan.acme_delivery_platform.json)
- [code_index_update.research_eval_hub.json](./code_index_update.research_eval_hub.json)

## 사용 목적

- 출력 스키마 문서에서 실제 필드 구성을 예시로 참조할 때 사용한다.
- 테스트 작성 시 기대 필드 구조를 빠르게 확인할 때 사용한다.
- 이후 공통 schema 파일 또는 MCP server 응답 규격으로 승격할 때 초안 샘플로 재사용한다.

## 주의 사항

- 이 디렉터리의 JSON 파일은 대표 예시이며, 모든 프로젝트에서 값이 동일하다는 뜻은 아니다.
- 경고 문구나 후보 경로는 프로젝트 프로파일과 변경 파일 입력에 따라 달라질 수 있다.

## 다음에 읽을 문서

- 출력 스키마 가이드: [../../core/output_schema_guide.md](../../core/output_schema_guide.md)
- end-to-end skill demo: [../end_to_end_skill_demo.md](../end_to_end_skill_demo.md)
