---
name: standard-ai-workflow
description: 이 저장소의 표준 AI 워크플로우 진입점. 세션을 시작하거나 이어받을 때, 작업을 backlog 에 등록/갱신할 때, 변경 후 영향 문서를 동기화할 때, 세션을 종료하며 handoff 를 남길 때 사용한다.
---

<!-- standard-ai-workflow-kit: v1.0.0-beta -->

# Standard AI Workflow

- **역할**: 세션 시작 / 백로그 갱신 / 문서 동기화 / 세션 종료를 한 자리에서 안내하는 진입 skill.
- **위치**: `.claude/skills/standard-ai-workflow/SKILL.md`
- **호출**: 모델이 위 `description` 에 해당하는 상황에서 자동 선택. 사용자가 직접 부르려면
  `/workflow-session-start`, `/workflow-backlog-update`, `/workflow-doc-sync` slash command.
- 최종 수정일: 2026-08-05

## 1. 세션 시작 — 항상 먼저 읽는다

1. `ai-workflow/memory/active/<branch>/state.json` — 현재 기준선
2. `ai-workflow/memory/active/<branch>/sessions` — 이전 세션 인계
3. `ai-workflow/memory/active/<branch>/backlog` — 작업 백로그 인덱스
4. `docs/PROJECT_PROFILE.md` — 프로젝트 메타
5. (있으면) `ai-workflow/memory/active/PURPOSE.md` — directional intent

읽은 뒤 한국어로 **1줄 기준선 요약 + 3-5개 다음 작업 후보 + 권장 다음 행동** 만 보고한다.
중간 reasoning, 중복 요약, 자기 설명은 내지 않는다.

`state.json` 이나 `PURPOSE.md` 가 없으면 실패로 처리하지 말고 *graceful skip* 후
scaffold 를 제안한다.

## 2. 백로그 갱신

오늘 작업을 `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md` 와
`./tasks/<TASK-ID>.md` 에 등록한다. 상태값은 `planned` / `in_progress` / `blocked` / `done`
넷만 쓴다. `PURPOSE.md` §3 의 제외 영역과 겹치면 scope creep 경고를 1줄 남긴다.

## 3. 문서 동기화 (advisory)

변경된 파일에서 영향 문서 후보를 뽑고, `ai-workflow/wiki/index.md` anchor 기준으로
갱신 포인트를 *권고* 한다. 자동 반영하지 않는다.

## 작업 원칙

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 새 세션은 항상 현재 상태 요약 문서부터 읽는다.
- 작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.
- 작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.
- 여러 에이전트가 함께 일할 수 있으므로, 작업 시작 전에 원격을 동기화해 다른 에이전트의 진행 상황을 확인하고 겹치지 않는 작업을 선택한다.
- 다른 에이전트의 작업을 지우거나 덮어쓰는 등 되돌릴 수 없는 작업은 단독으로 결정하지 않고 사용자에게 확인한다.
- 공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.

## 세션 종료 순서

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

- 종료 전 갱신 대상: `state.json`, `session_handoff.md`, 최신 backlog

## 언어와 컨텍스트 원칙

- 사용자에게 보이는 보고 / 상태 요약 / 문서 문안은 한국어.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 원문 그대로.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남긴다.
- `ai-workflow/` 는 workflow 메타 레이어다. 프로젝트 코드/문서 탐색 범위에 기본 포함하지 않는다.
