---
name: session-start
description: 표준 AI 워크플로우 세션 시작 — state.json + session_handoff.md + backlog 로 현재 기준선을 복원하고 다음 작업 후보를 보고한다.
---

# session-start

## 역할

`ai-workflow/memory/active/<branch>/` 의 현재 baseline 을 복원하고, 다음 작업
후보를 보고한다.

## 절차

1. `state.json` — 현재 기준선 (`latest_backlog_path`, 진행/차단/최근 완료 목록)
2. `session_handoff.md` — 이전 세션의 인계 사항
3. `backlog/<YYYY-MM-DD>.md` — 현재 작업 목록
4. `docs/PROJECT_PROFILE.md` — 프로젝트 메타
5. (있으면) `ai-workflow/memory/active/PURPOSE.md` — directional intent

읽은 뒤 한국어로 **1줄 기준선 요약 + 3~5개 다음 작업 후보 + 권장 다음 행동** 만
보고한다. 중간 reasoning, 중복 요약, 자기 설명은 내지 않는다.

`state.json` 이나 `PURPOSE.md` 가 없으면 실패로 처리하지 말고 *graceful skip* 후
scaffold 를 제안한다.

## 실행

```bash
wk session-start --help
```

`wk` 가 없으면 조용히 넘어가지 않는다 — 설치 안내를 보고하고
멈춘다 (`INSTALLATION_AND_USAGE.md` §3).

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
