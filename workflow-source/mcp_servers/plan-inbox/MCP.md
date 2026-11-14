# plan-inbox

- 문서 목적: MCP 도구 `plan_inbox` — 받은편지함의 미반영 계획 응답을 읽기 전용으로 보고
- 범위: 입력 · 출력 · 실행 예시
- 대상 독자: AI 에이전트, MCP 클라이언트
- 상태: implemented
- 최종 수정일: 2026-11-14
- 관련 문서: `../../core/plan_workbench_spec.md` §8.3, `../../core/claim_plan_spec.md`

## 계약

계약의 정본은 `core/plan_workbench_spec.md` §8.3 이다. 받은편지함 건수는 `plan_responses.inbox_census` 하나에서 나온다.

- 입력: `workspace_root`(선택, 기본 서버 cwd) · `task_id`(선택 — 없으면 받은편지함 전체)
- 출력(family `plan_inbox`): `pending`(task 별 건수) · `files`(파일별 `task` · `name` · `responder` · `received_at` · `stage` · `reason`) ·
  `unknown` · `layout_problem`. **주석 본문은 싣지 않는다.** 아무것도 쓰지 않는다.

## 실행 예시

```bash
python3 workflow-source/mcp_servers/plan-inbox/scripts/run_plan_inbox.py --workspace-root . --json
```
