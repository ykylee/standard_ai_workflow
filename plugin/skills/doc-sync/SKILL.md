---
name: doc-sync
description: 표준 AI 워크플로우 문서 동기화 — 변경된 파일에서 영향 문서 후보를 뽑고 wiki index 기준 갱신 포인트를 advisory 로 제안한다.
---

# doc-sync

## 역할

변경된 파일에서 영향 문서 후보를 뽑고, 갱신 포인트를 **advisory 로** 제안한다.
자동 반영하지 않는다.

## 절차

1. 현재 변경된 파일 목록에서 영향 문서 후보를 식별한다.
2. `ai-workflow/wiki/index.md` 의 anchor 카탈로그와 대조한다.
3. 후보별로 경로 + 1줄 요약 + confidence (high / medium / low) 를 보고한다.
4. 새 concept / decision / pattern 페이지가 필요한지 판단해 제안한다.

## 실행

```bash
wk doc-sync --help
```

## 메모리 갱신 경로

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 세션 시작 baseline 복원: `wk session-start`
- task 등록 / 갱신: `wk backlog-update`
- 영향 문서 동기화 (advisory): `wk doc-sync`
- 세션 종료 시 state.json 재생성: `wk refresh-state`

- handoff 의 `in_progress` / `blocked` 목록이 비면 **빈 bullet `-`** 로 둔다. 산문을 쓰면 작업 항목으로 파싱된다.
- handoff 의 최근 완료 목록 항목은 `TASK-` 로 시작하고, 10건을 넘지 않는다.
- backlog task 의 `status` 는 `planned` / `in_progress` / `blocked` / `done` 중 하나다.
- `state.json` 은 **생성물**이다 — 손으로 고치지 않는다. SSOT 는 `backlog/tasks/` 와 `session_handoff.md` 이고, 세션 종료 시 `wk refresh-state` 로 재생성한다.
- `session_handoff.md` 와 backlog 는 **state.json 생성기의 입력**이다 — 형식을 벗어나 쓰면 state.json 이 조용히 오염된다.
