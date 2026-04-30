# Standard AI Workflow Skill

- 문서 목적: 세션 시작, backlog 갱신, handoff 정리를 위한 빠른 진입점을 제공한다.
- 범위: 세션 상태 복원, 작업 planejamento, 문서 동기화
- 대상 독자: OpenCode agent
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `../../AGENTS.md`, `../../ai-workflow/memory/state.json`, `../../ai-workflow/memory/session_handoff.md`, `../../ai-workflow/memory/work_backlog.md`

## 시작할 때

1. 먼저 아래 문서를 순서대로 읽는다.
   - `AGENTS.md`
   - `ai-workflow/memory/state.json`
   - `ai-workflow/memory/session_handoff.md`
   - `ai-workflow/memory/work_backlog.md`

2. 세션 시작 skill 이라면:
   - state.json 의 현재 프로젝트 상태를 확인한다.
   - session_handoff.md 에 남겨진 다음 작업을 확인한다.
   - work_backlog.md 에 현재 진행 중인 작업을 확인한다.

## 작업 원칙

- 작업을 시작하기 전에 목적, 범위, 영향 문서를 짧게 정리한다.
- 작업 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 `state.json`, `session_handoff.md`, 최신 backlog 를 갱신한다.

## 언어 원칙

- Writing visible summaries and document updates in Korean by default.
- Code, commands, filepaths, config keys maintain original when needed.
- Keep internal processing compact—deliver only essential conclusions and next actions to user.
- Leave only essential facts in handoff/backlog to minimize context.

## 검증 명령어

- 설치: `python3 -m pip install -r requirements-dev.txt`
- 테스트: `python3 tests/check_docs.py`
- 로컬 실행: `python3 scripts/run_demo_workflow.py --example-project acme_delivery_platform`

## 상태 동기화

- 세션 시작 직후: state.json, session_handoff.md, work_backlog.md 를 읽고 현재 상태를 복원한다.
- 작업 중: 검증 직후 Todos를 갱신한다.
- 세션 종료 직전: state.json, session_handoff.md, 최신 backlog 를 갱신하고 종료한다.