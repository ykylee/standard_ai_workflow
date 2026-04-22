# Read-Only MCP Bundle Draft

- 문서 목적: 읽기 전용 MCP 1차 묶음을 하나의 엔트리포인트로 승격할 때 현재 코드 구조와 포함 범위를 정리한다.
- 범위: 1차 포함 tool, 현재 엔트리포인트 파일, 아직 없는 transport 계층, 다음 확장 포인트
- 대상 독자: AI workflow 설계자, 구현자, MCP server 정리 담당자
- 상태: draft
- 최종 수정일: 2026-04-23
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
- 공통 callable layer: `workflow_kit/common/read_only_bundle.py`
- direct-call adapter: `workflow_kit/server/read_only_tools.py`
- smoke test: `tests/check_read_only_mcp_server.py`

현재 entrypoint 는 아래 두 동작만 제공한다.

1. `--list-tools`
2. `--tool <name> --payload-json '{...}'`

이 단계의 목적은 transport 나 외부 MCP SDK 연동보다, “현재 읽기 전용 tool 들을 하나의 코드 구조 아래서 직접 호출하고, 같은 output contract 로 검증 가능한가”를 먼저 확인하는 것이다.

## 현재 payload schema 규칙

- manifest 는 각 tool 에 대해 `input_schema.fields`, `requires_any_of`, `payload_example` 를 함께 노출한다.
- manifest 는 각 tool 에 대해 `output_schema.success_required_keys`, `output_schema.error_required_keys` 를 함께 노출한다.
- manifest 는 각 tool 에 대해 `output_schema.field_shapes` 로 주요 필드의 list/object nested shape 도 함께 노출한다.
- entrypoint 는 payload JSON 이 object 인지 확인한 뒤, unknown field, 필수 field 누락, repeated field 의 list 여부를 검증한다.
- schema 검증을 통과한 payload 는 subprocess 대신 `workflow_kit/server/read_only_tools.py` 의 direct-call 함수로 바로 전달된다.
- direct-call 결과는 `workflow_kit/common/output_contracts.py` 의 공통 출력 계약으로 한 번 더 검증되며, read-only 5종은 주요 list/object nested shape 까지 확인한다.
- direct-call 경로에서는 누락된 입력 경로를 `missing_tool_input_path` 구조화 error 로 반환한다.
- `latest_backlog` 는 `backlog_dir_path` 또는 `work_backlog_index_path` 중 하나가 있어야 한다.
- `check_doc_metadata`, `check_doc_links` 는 `doc_dir_path` 가 필수다.
- `suggest_impacted_docs` 는 `changed_files` list 가 필수다.
- `check_quickstart_stale_links` 는 `quickstart_paths` list 가 필수다.

## 현재 한계

- 아직 정식 MCP transport 계층은 없다.
- 입력 field type 은 현재 `path` 와 `string` 수준의 얕은 계약이며, 경로 존재성 검증만 수행한다.
- 출력 계약은 주요 nested list/object shape 까지 고정됐지만, 모든 nested 타입과 enum 제약을 완전 고정한 것은 아니다.
- 정식 MCP SDK 에 맞는 tool descriptor/transport 계층은 아직 연결되지 않았다.

## 관련 검증 경로

- `tests/check_read_only_mcp_server.py` 는 manifest 의 `bundle_phase`, `input_schema`, `output_schema.field_shapes`, payload validation 경로를 함께 확인한다.
- `tests/check_output_samples.py` 는 read-only 5종 sample 이 공통 output contract 와 정적 계약 파일에 맞는지 확인한다.
- `tests/check_output_json_schema.py` 와 `tests/check_generated_schema_validation.py` 는 runtime contract 에서 생성한 JSON Schema draft 가 sample payload 를 실제로 받아들이는지 확인한다.

## 다음 확장 포인트

- tool 별 input schema 문서화 또는 dataclass 기반 schema 추가
- output payload 의 nested field 타입과 enum 제약 추가
- generated JSON Schema draft 를 manifest 또는 외부 소비 지점과 어떻게 연결할지 정리
- 정식 MCP SDK/transport 계층 연결
- 읽기 전용 bundle 과 초안 생성 bundle 의 permission 경계 분리
