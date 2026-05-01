# 작업 백로그 인덱스

- 문서 목적: 날짜별 작업 백로그 문서의 위치와 운영 기준을 관리한다.
- 범위: 일자별 백로그 문서
- 대상 독자: 프로젝트 참여자, 문서 작성자, 개발자, 운영자
- 상태: done
- 최종 수정일: 2026-05-01
- 관련 문서: `./codex/phase6/session_handoff.md`, `../docs/PROJECT_PROFILE.md`

## 운영 원칙

- [x] AI 워크플로우 인프라 격리 (ai-workflow/ 하위 이동)
    - [x] scripts, skills, mcp, tests, templates 등 이동
    - [x] bootstrap_workflow_kit.py 경로 로직 업데이트
    - [x] 모든 Python 엔트리포인트 REPO_ROOT 및 sys.path 업데이트
    - [x] 자동화 스모크 테스트를 통한 정합성 검증
    - [x] 전수 문서 링크 최적화 및 메타데이터 정비 (`check_docs.py` 통과)
    - [x] PR 제출 전 최종 현황 점검 및 `state.json` 동기화
- 세션 시작 시 본 인덱스와 최신 날짜 백로그를 먼저 확인한다.
- 새 작업은 브리핑 후 `backlog/tasks/` 하위 개별 task 파일에 기록하고, 날짜별 백로그에는 해당 task 링크를 추가한다.
- 날짜별 백로그 문서는 Git에서 추적되는 lightweight index이며, 상세 작업 상태의 source of truth는 개별 task 파일이다.
- 세션 종료 전에는 handoff 문서를 갱신한다.
- 검증 결과와 미실행 사유는 날짜별 백로그에 남긴다.
- 사용자에게 직접 보여지는 작업 기록과 상태 요약은 한국어를 기본으로 작성한다.
- 다음 세션에 필요한 핵심 사실만 남기고, 중간 탐색 흔적과 중복 요약은 줄인다.

## 날짜별 백로그 문서

- [2026-05-01 codex/phase6 작업 백로그](./codex/phase6/backlog/2026-05-01.md) (beta 0.4.0 workflow configuration review follow-up plan)
- [2026-04-30 codex/phase6 작업 백로그](./codex/phase6/backlog/2026-04-30.md) (v0.3.2-beta 통합 및 workflow 재배치)
- [2026-04-30 작업 기록](./gemini/phase6/backlog/2026-04-30.md) (main 통합 후 codex/phase6 충돌 해소 포함)
- [2026-04-30 작업 백로그](./gemini/phase6/backlog/2026-04-30.md) (브랜치 격리 및 거버넌스 개편)
