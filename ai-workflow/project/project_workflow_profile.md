# Project Workflow Profile

- 문서 목적: 공통 표준 워크플로우를 `Standard AI Workflow` 저장소에 적용할 때 필요한 프로젝트 특화 규칙을 정리한다.
- 범위: 저장소 목적, 문서 구조, 기본 명령, 환경 기록 위치, 프로젝트 특화 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: final (Phase 6 진입)
- 최종 수정일: 2026-04-29
- 관련 문서: `../core/global_workflow_standard.md`, `./session_handoff.md`, `./work_backlog.md`, `../core/maturity_matrix.json`

## 1. 프로젝트 개요

- 프로젝트명:
- `Standard AI Workflow`
- 프로젝트 목적:
- 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다. 현재 **Phase 6 (편집 정밀화 및 지능형 읽기 도구 최적화)** 단계에 있으며, `robust-patcher`와 `smart-context-reader`를 통한 생산성 극대화를 목표로 한다.
- 주요 이해관계자:
- YK Lee (Developer), AI Agent 설계자

## 2. 문서 구조

- 문서 위키 홈:
- `README.md`
- 운영 문서 위치:
- `ai-workflow/project/` (또는 `ai-workflow/project/` 를 직접 참조)
- 백로그 위치:
- `ai-workflow/project/backlog/tasks/` (개별 태스크 저장)
- `ai-workflow/project/backlog/` (취합된 날짜별 백로그 - Auto-generated)
- 세션 인계 문서 위치:
- `ai-workflow/project/session_handoff.md`
- 환경 기록 위치:
- `ai-workflow/project/repository_assessment.md`

## 3. 기본 명령

- 설치:
- `python3 -m pip install -r requirements-dev.txt`
- 로컬 실행:
- `python3 scripts/run_demo_workflow.py`
- 빠른 테스트:
- `python3 tests/check_docs.py`
- 격리 테스트:
- `for t in tests/check_*.py; do python3 "$t" || exit 1; done`
- UI/API 실행 확인:
- `python3 scripts/bootstrap_workflow_kit.py --help`

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- `tests/check_*.py` 스모크 테스트 통과 확인. `bootstrap_workflow_kit.py` 의 경우 `--dry-run` 결과의 JSON 스키마 정합성 확인.
- 문서 변경 시:
- `python3 tests/check_docs.py` 를 실행하여 상대 링크와 메타데이터 무결성 확인.
- UI 변경 시:
- N/A (CLI/문서 중심 프로젝트)
- 배포/운영 변경 시:
- `scripts/export_harness_package.py` 를 실행하여 배포용 번들 생성 및 `PACKAGE_CONTENTS.md` 포함 여부 확인.

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙 (Conflict Management):
- **백로그 (Event Sourcing)**: `backlog/tasks/` 하위의 개별 태스크 파일을 Git으로 관리하여 병합 충돌을 방지한다. 날짜별 취합 문서(`backlog/YYYY-MM-DD.md`)는 로컬에서 자동 생성되므로 Git에서 제외(ignore)하거나 충돌 시 무시하고 재생성한다.
- **상태 문서 (`state.json`, `session_handoff.md`)**: 이 문서들은 현재 세션의 context를 담고 있는 파생(Generated) 문서이거나 캐시이므로, Git 병합 충돌 시 `merge-doc-reconcile --apply` 명령을 사용하여 양쪽 브랜치의 변경 사항을 AI가 자동 취합하여 재생성하도록 권장한다.
- **Backlog Index (`work_backlog.md`)**: 날짜별 문서 링크 추가 시 충돌이 나면 `merge=union` 속성을 활용하거나 수동으로 중복 없이 병합한다.
- 승인 규칙:
- `core/` 아래의 표준 문서는 워크플로우 전반에 영향을 주므로 변경 시 반드시 설계 의도와 하위 호환성을 검토한다.
- 환경 제약:
- Python 3.10 이상 필요 (MCP SDK 의존성).
- 기타:
- 이 저장소는 워크플로우 키트 자체의 개발 저장소이므로, `ai-workflow/` 디렉터리가 개발 대상이자 동시에 운영 도구로 사용되는 "self-dogfooding" 구조임을 유의한다.

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../../core/global_workflow_standard.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
