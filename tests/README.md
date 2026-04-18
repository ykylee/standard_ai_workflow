# Tests

- 문서 목적: 표준 워크플로우 패키지의 링크, 메타데이터, 템플릿 smoke test 또는 향후 구현 테스트를 배치할 위치를 안내한다.
- 범위: 문서 무결성 검사와 향후 skill/MCP/agent 구현 검증
- 대상 독자: 개발자, 운영자, AI agent 설계자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `../split_checklist.md`

## 현재 상태

- 기본 문서 스모크 체크 스크립트 `check_docs.py` 를 제공한다.
- 현재 스크립트는 모든 Markdown 문서의 필수 메타데이터와 상대 링크 무결성을 검사한다.

## 포함된 검사

- 문서 첫 부분에 필수 메타데이터 항목이 있는지 확인
- Markdown 상대 링크가 실제 파일을 가리키는지 확인
- 문서 제목이 `# ` 헤더로 시작하는지 확인

## 실행 방법

- 저장소 루트에서 `python3 tests/check_docs.py`

## 향후 확장 후보

- 템플릿 placeholder 누락 검사
- 예시 문서와 템플릿 구조 차이 비교
- skill/MCP/agent 구현 추가 시 실행 가능한 smoke test 확장
