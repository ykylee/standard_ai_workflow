# 워크플로우 허브 표준 규칙 (2.0)

- 문서 목적: 2.0 허브 흐름의 표준 규칙 층 정본 — 허브가 모든 프로젝트 · 모든 지원 하네스의 진입 파일 렌더 영역에 싣는 규칙이다 (hub_spec §5.2, DS6).
- 범위: 세션 시작 확인 · 작업 중 기록 · 세션 끝 순서 · compact 직후 확인 · 쓰기 금지. 1.x 흐름의 정본은 `global_workflow_standard.md` 그대로다.
- 대상 독자: AI agent (진입 파일로 읽는다), workflow 설계자
- 상태: draft (M-034, 2026-11-21)
- 최종 수정일: 2026-11-21
- 관련 문서: `./hub_spec.md`, `../../docs/planning/workflow-hub-requirements-2026-11.md` (요구 R6.4 · R7.3 · R10 · R11), `./global_workflow_standard.md`

> 아래 `hub-standard` 표식 사이가 렌더 영역에 들어가는 본문이다 (`workflow_kit.hub.render`).
> 명령은 허브 MCP 도구 이름이다 — `python -m workflow_kit …` 를 쓰지 않는다 (요구 R7.3).

<!-- hub-standard:begin -->
## 워크플로우 허브 규칙 (표준 · 2.0)

이 저장소의 task · handoff · 이력 · 로드맵 · 공유 지침 · 위키의 정본은 **워크플로우 허브**다. 저장소의 파일은 내보내기다.

### 세션 시작 — 허브와 저장소를 함께 확인한다
1. `hub_session_start` 를 인자 없이 부른다. 허브 쪽 결과(지침 판 · 내 task · 맡은 이 없는 열린 task)와 저장소에서 돌릴 명령 목록이 온다.
2. 그 명령을 **그대로** 돌리고 결과를 `repo_results` 로 실어 `hub_session_start` 를 다시 부른다.
3. 판정을 따른다: `fast_forward_then_start` 면 fast-forward 뒤 시작, `stop_and_ask` 면 **멈추고 사람에게 묻는다**, `[바뀜]` 이면 지침을 먼저 읽는다.
4. 보고에는 확인한 것과 확인하지 못한 것을 나눠 적는다. 허브에 닿지 않으면 "허브 미확인" 이라고 적는다 — 확인한 척하지 않는다.

### 작업 중
- task 를 맡을 때 `hub_task_claim`. 다른 콜사인이 맡고 있으면(409) 그 task 를 하지 않는다.
- 단계마다(계획 → 구현 → 검사 → 커밋 · push) `hub_task_progress` 로 진행 한 줄을 남긴다.
- 커밋하면 `hub_task_link_commit` 으로 task 에 묶는다.
- 쓰기가 409(`version_conflict`)면 지금 값을 다시 읽고 판단한다 — 덮어쓰지 않는다.

### compact 직후
- 첫 행동은 허브 확인과 기록 대조다: 내 task 의 지금 상태 · 진행 기록 · 그 사이 다른 콜사인이 바꾼 것을 확인하고, 압축 전에 적어 둔 다음 걸음에서 잇는다. 끝난 것으로 기록된 일을 다시 하지 않고, 미검증은 미검증으로 보고한다.

### 세션 끝
- 순서: **허브 기록 갱신 → 커밋 → push**. 이 렌더 영역이 바뀌었으면 그 변경도 커밋한다.

### 하지 않는 것
- 이 렌더 영역(`workflow-hub:begin` ~ `end`)을 손으로 고치지 않는다 — 고칠 것은 허브에 지침 제안으로 올린다.
- `.workflow-hub/` 를 커밋하지 않는다. 토큰을 task · handoff · 커밋 · 진입 파일에 적지 않는다.
<!-- hub-standard:end -->
