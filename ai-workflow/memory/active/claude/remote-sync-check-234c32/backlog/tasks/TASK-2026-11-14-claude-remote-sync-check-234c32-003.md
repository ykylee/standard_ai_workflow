---
id: TASK-2026-11-14-claude-remote-sync-check-234c32-003
status: done
created_at: 2026-11-14
source_anchor: generic-task-2026-11-14-claude-remote-sync-check-234c32-003
source_path: backlog/2026-11-14.md
kind: generic
wbs: M-029/WBS-29.2
---

# TASK-2026-11-14-claude-remote-sync-check-234c32-003 — M-029 ② MCP plan_inbox · plan_import + 체크인 생성물

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-14
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/core/plan_workbench_spec.md`

- Description: plan_workbench_spec §8.3 — read-only 번들 plan_inbox(task_id 선택, inbox_census + 파일별 판정, 주석 본문 없음), write 번들 plan_import(plan-import 출력 계약 그대로), descriptor · JSON-RPC fixture · 하네스 MCP 예시를 같은 커밋에서 재생성
- Completion criteria: [C1] read-only 번들의 plan_inbox 가 inbox_census 와 파일별 {task, name, responder, received_at, stage, reason} 을 내고 주석 본문을 싣지 않는다 — 검사 case 로 잼
- Completion criteria: [C2] write 번들의 plan_import 가 plan-import 의 출력 계약 family plan_import 그대로이고 기본 dry-run 이다 — WRITE_CAPABLE_TOOL_NAMES · read_only=False 가 같이 바뀐다
- Completion criteria: [C3] 체크인 생성물(descriptor · JSON-RPC fixture · 하네스 MCP 예시)이 도구와 같은 커밋에서 다시 만들어지고 해당 검사가 green 이다

## 🧭 Plan

- Claims: C1 plan_inbox 는 받은편지함을 census 로만 보고한다
- Claims: C2 plan_import 는 CLI 와 같은 계약의 write 도구다
- Claims: C3 생성물이 도구와 함께 바뀐다
- Files that change: workflow-source/workflow_kit/common/plan_mcp.py · common/schemas/plan.py · __init__.py · common/output_contracts.py
- Files that change: workflow-source/workflow_kit/server/read_only_registry.py · read_only_entrypoint.py · read_only_tools.py · read_only_jsonrpc.py
- Files that change: workflow-source/mcp_servers/plan-inbox · plan-import (runner · MCP.md) · schemas/*.json 5종 · examples/mcp_config_examples/minimax-*.json
- Files that change: workflow-source/tests/check_plan_mcp_tools.py · check_plan_claims.py · check_v0_8_10_read_only_manifest_byte_identical.py
- Files that change: workflow-source/core/plan_workbench_spec.md · core/stable_guarantee.md · docs/CODE_INDEX.md · docs/INSTALLATION_AND_USAGE.md
- Order of work: [C1][C2] 등록 · 디스패치 · 출력 계약
- Order of work: [C3] 생성물 재생성 → 되주입 → verifier
- Plan risks: [C2] write 도구를 read-only 로 광고하면 하네스가 자동 승인한다 — readOnlyHint 검사로 확인
- Proof: 검사 case · 되주입 red · verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-14 구현: common/plan_mcp.py(plan_inbox — census · judge, 주석 본문 없음 / plan_import — 서버 인터프리터로 CLI 하위 프로세스) · registry 두 spec(boolean 입력 · requires_any_of · WRITE_CAPABLE) · runner 둘 · MCP.md 둘 · 생성물 5종 재생성 · minimax 예시 · 옛 매니페스트 검사의 도구 수를 registry 파생으로. check_plan_mcp_tools 5/5, 되주입 16/16 red, --changed 301/301 · smoke 8/8
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: plan_inbox(read-only) · plan_import(write, CLI 하위 프로세스 — 출력 계약 동일) · boolean 입력 · missing_discard_reason · invalid_tool_arguments · 생성물 5종 · minimax 예시 · stable_guarantee(beta)
- Verification: verifier 3회 — 1차 C1 FAIL(received_at · reason · task 없음 분기 미측정) · C2 측정 공백(response · apply:1) → 2차 C1 FAIL(오류 규칙 → 0 단계 분기 미측정, M28) → 3차 [C1]~[C3] PASS. check_plan_mcp_tools 5/5, 되주입 작성자 28건 · verifier 30건 red, 생존은 기준 밖 3건(PYTHONPATH 줄 — editable 설치가 가림 · 공백 reason — CLI 가 거절 · object 아닌 JSON 방어 코드). --changed(base c1586fb6) 301/301 · smoke 8/8
- Follow-up:
