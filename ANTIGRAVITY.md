# ANTIGRAVITY.md

- 문서 목적: Antigravity 가 이 저장소에서 먼저 읽어야 할 workflow 진입 규칙과 기본 작업 원칙을 제공한다.
- 범위: 세션 복원, workflow state docs 참조 순서, 사용자 보고 언어, 기본 실행/검증 명령
- 대상 독자: Antigravity, 저장소 관리자, workflow 설계자
- 상태: draft
- 최종 수정일: 2026-04-30
- 관련 문서: `ai-workflow/memory/state.json`, `ai-workflow/memory/session_handoff.md`, `ai-workflow/memory/work_backlog.md`, `ai-workflow/memory/PROJECT_PROFILE.md`

## 목적

이 저장소에서는 표준 AI 워크플로우를 기준으로 작업한다. 세션 시작, backlog 갱신, 문서 동기화, 세션 종료는 `ai-workflow/` 아래 문서를 우선 기준으로 삼는다.

## 항상 먼저 읽을 문서

- `ai-workflow/memory/state.json`
- `ai-workflow/memory/session_handoff.md`
- `ai-workflow/memory/work_backlog.md`
- `ai-workflow/memory/PROJECT_PROFILE.md`

`ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어다. 프로젝트 코드나 프로젝트 문서를 탐색할 때는 이 경로를 기본 탐색 범위에 넣지 말고, workflow 문서 자체를 갱신하거나 현재 세션 상태를 복원할 때만 예외적으로 참조한다.

## 작업 원칙

- 작업을 시작하기 전에 목적, 범위, 영향 문서를 짧게 정리한다.
- 작업 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 `state.json`, `session_handoff.md`, 최신 backlog 를 갱신한다.

## 언어와 컨텍스트 원칙

- 사용자에게 직접 보이는 작업 보고, 상태 요약, 문서 갱신 문안은 기본적으로 한국어로 작성한다.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 필요할 때 원문 그대로 유지한다.
- 내부 사고 과정과 임시 분류는 모델이 가장 효율적인 방식으로 처리하되, 사용자에게는 필요한 결론과 다음 행동만 짧게 전달한다.
- 장문의 중간 reasoning, 중복 요약, 불필요한 자기 설명을 피한다.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남겨 불필요한 컨텍스트 누적을 줄인다.

## 프로젝트 실행 기본값

- 설치: `pip install -r requirements-dev.txt`
- 로컬 실행: `python3 ai-workflow/scripts/run_demo_workflow.py`
- 빠른 테스트: `python3 ai-workflow/tests/check_docs.py`
- 격리 테스트: `for t in ai-workflow/tests/check_*.py; do python3 "$t" || exit 1; done`
- 실행 확인: `python3 ai-workflow/scripts/bootstrap_workflow_kit.py --help`

## Antigravity 전용 작업 원칙

### 1. Artifacts (작업 증빙) 활용
Antigravity 에이전트는 모든 주요 의사결정과 작업 결과를 Artifacts 로 관리한다.
- **Implementation Plan**: 복잡한 수정 전에는 반드시 계획 문서를 작성하여 의도를 공유한다.
- **Task List**: 작업 단위를 쪼개어 실시간 진행 상황을 기록한다.
- **Walkthrough**: 작업 완료 후 변경 사항과 검증 결과를 요약하여 제출한다.

### 2. 브라우저 통합 및 서브 에이전트
UI 검증이나 외부 환경 조작이 필요한 경우, 직접 도구를 사용하는 대신 전용 **브라우저 서브 에이전트**를 활용하여 스크린샷과 녹화본을 증빙으로 확보한다.

### 3. 워크플로우 Skills 연동
`ai-workflow/skills/` 및 `scripts/` 아래의 도구들은 Antigravity 의 **Specialized Skills** 로 간주한다. 복잡한 상태 갱신이나 백로그 동기화는 직접 파일을 수정하기보다 이 도구들을 호출하여 수행하는 것을 권장한다.

## 문서 작업 기준

- 문서 위키 홈: `README.md`
- 운영 문서 위치: `ai-workflow/memory/`
- backlog 위치: `ai-workflow/memory/backlog/`
- session handoff 위치: `ai-workflow/memory/session_handoff.md`
