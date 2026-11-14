# plan-import

- 문서 목적: MCP 도구 `plan_import` — 받은편지함의 계획 응답을 task 에 반영 (기본 dry-run, write 번들)
- 범위: 입력 · 출력 · 실행 예시
- 대상 독자: AI 에이전트, MCP 클라이언트
- 상태: implemented
- 최종 수정일: 2026-11-14
- 관련 문서: `../../core/plan_workbench_spec.md` §8.3, `../../core/claim_plan_spec.md`

## 계약

계약의 정본은 `core/plan_workbench_spec.md` §8.3 이다. 받은편지함 건수는 `plan_responses.inbox_census` 하나에서 나온다.

- 입력: `workspace_root`(선택) · `task_id` 또는 `discard` + `reason` · `response`(선택) · `apply`(boolean, 기본 false)
- 출력: CLI `python -m workflow_kit plan-import` 의 출력 계약 family `plan_import` 그대로 — 같은 인터프리터의 하위 프로세스로 부른다.
- write 번들이다 (`readOnlyHint: false`). write 번들을 받지 않는 하네스(Codex)는 CLI `plan-import` 를 쓴다.

## 실행 예시

```bash
python3 workflow-source/mcp_servers/plan-import/scripts/run_plan_import.py --workspace-root . --task-id <TASK-ID> --json
```
