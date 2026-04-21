# Tests

- 문서 목적: 표준 워크플로우 패키지의 링크, 메타데이터, 템플릿 smoke test 또는 향후 구현 테스트를 배치할 위치를 안내한다.
- 범위: 문서 무결성 검사와 향후 skill/MCP/agent 구현 검증
- 대상 독자: 개발자, 운영자, AI agent 설계자
- 상태: draft
- 최종 수정일: 2026-04-22
- 관련 문서: `../split_checklist.md`

## 현재 상태

- 기본 문서 스모크 체크 스크립트 `check_docs.py` 를 제공한다.
- bootstrap 스캐폴딩 결과를 확인하는 `check_bootstrap.py` 를 제공한다.
- 하네스 스텁 생성기를 확인하는 `check_scaffold_harness.py` 를 제공한다.
- 하네스 패키지 export 를 확인하는 `check_export_harness_package.py` 를 제공한다.
- 기존 프로젝트 bootstrap 후속 온보딩 흐름을 확인하는 `check_existing_project_onboarding.py` 를 제공한다.
- demo runner 성공/실패 경로를 확인하는 `check_demo_workflow.py` 를 제공한다.
- quickstart/README stale 링크 점검 MCP 를 확인하는 `check_quickstart_stale_links.py` 를 제공한다.
- 현재 스크립트는 문서 무결성과 기본 생성 흐름이 깨지지 않았는지 빠르게 검사한다.

## 포함된 검사

- 문서 첫 부분에 필수 메타데이터 항목이 있는지 확인
- Markdown 상대 링크가 실제 파일을 가리키는지 확인
- 문서 제목이 `# ` 헤더로 시작하는지 확인
- bootstrap 스크립트가 신규/기존 프로젝트 모드에서 핵심 문서, 하네스 오버레이, core 복사본을 생성하는지 확인
- bootstrap manifest 에 하네스별 global snippet 후보 정보가 포함되는지 확인
- 하네스 스캐폴드 스크립트가 새 하네스 starter 문서를 생성하는지 확인
- 하네스 export 스크립트가 dist 산출물, manifest, zip 파일을 생성하는지 확인
- export manifest 에 global snippet 파일 정보가 포함되는지 확인
- `validation-plan` 프로토타입이 예시 프로젝트에서 기대한 분류와 검증 수준을 출력하는지 확인
- `code-index-update` 프로토타입이 예시 프로젝트에서 색인 문서 후보와 stale 경고를 출력하는지 확인
- `examples/output_samples/` 아래 JSON 샘플이 README 링크와 일치하고 유효한 JSON 인지 확인
- demo runner 가 상위 `orchestration_plan`, `workflow_summary`, `source_context` 를 유지하는지 확인
- demo runner 가 하위 step 실패를 top-level `workflow_step_failed` 로 감싸는지 확인
- 대표 JSON 샘플이 공통 필드뿐 아니라 skill/runner 계약의 핵심 필드도 유지하는지 확인
- `schemas/output_sample_contracts.json` 과 Python 런타임 계약 맵이 서로 어긋나지 않는지 확인
- 기존 프로젝트 bootstrap 산출물을 입력으로 받아 onboarding runner 가 session-start, validation-plan, code-index-update 를 연결하는지 확인
- onboarding runner 가 누락 입력 문서 시 top-level 구조화 error JSON 을 반환하는지 확인
- quickstart/README 문서를 입력으로 받아 stale 링크 경고와 핵심 진입 문서 누락을 감지하는지 확인

## 실행 방법

- 저장소 루트에서 `for t in tests/check_*.py; do python3 "$t" || exit 1; done`
- 저장소 루트에서 `python3 tests/check_docs.py`
- 저장소 루트에서 `python3 tests/check_bootstrap.py`
- 저장소 루트에서 `python3 tests/check_scaffold_harness.py`
- 저장소 루트에서 `python3 tests/check_export_harness_package.py`
- 저장소 루트에서 `python3 tests/check_validation_plan.py`
- 저장소 루트에서 `python3 tests/check_code_index_update.py`
- 저장소 루트에서 `python3 tests/check_output_samples.py`
- 저장소 루트에서 `python3 tests/check_demo_workflow.py`
- 저장소 루트에서 `python3 tests/check_existing_project_onboarding.py`
- 저장소 루트에서 `python3 tests/check_quickstart_stale_links.py`

## 향후 확장 후보

- 템플릿 placeholder 누락 검사
- 예시 문서와 템플릿 구조 차이 비교
- skill/MCP/agent 구현 추가 시 실행 가능한 smoke test 확장
