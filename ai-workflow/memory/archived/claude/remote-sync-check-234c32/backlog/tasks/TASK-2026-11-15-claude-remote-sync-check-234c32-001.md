---
carried_over_to: TASK-2026-11-15-claude-remote-sync-check-234c32-001@main
id: TASK-2026-11-15-claude-remote-sync-check-234c32-001
status: done
created_at: 2026-11-15
source_anchor: generic-task-2026-11-15-claude-remote-sync-check-234c32-001
source_path: backlog/2026-11-15.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-15-claude-remote-sync-check-234c32-001 — MCP 도구 4종 성공 경로 output contract 미등록 수리 (main-002 대응, 발행 차단 결함)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-15
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/common/output_contracts.py`
  - `workflow-source/workflow_kit/common/schemas/read_only.py`
  - `workflow-source/workflow_kit/common/read_only_bundle.py`
  - `workflow-source/tests/check_v0_8_10_read_only_manifest_byte_identical.py`
  - `workflow-source/schemas/`

- Description: summarize_git_history · assess_milestone_progress · rotate_workflow_logs · apply_robust_patch 가 성공 경로에서 Unknown family 로 invalid_tool_output_contract. 1.22.0 발행본 포함 — 다음 발행 전에 닫는다. 정본 task 는 main 브랜치의 TASK-2026-11-04-main-002.
- Completion criteria: 4 도구를 invoke_tool 로 성공 입력 호출하면 rc 0 이고 error_code 가 없다
- Completion criteria: MCP 도구 목록(registry 의 모든 spec 이름)이 PYDANTIC_MODEL_REGISTRY 에 전부 있음을 단언하는 검사가 있고, 등록 하나를 빼면 red 다
- Completion criteria: 새 모델이 실제 출력 필드를 모두 선언한다(키 집합 대조 case) — 모델만 등록되고 출력이 어긋나는 상태를 잡는다

## 🧭 Plan

- Claims: C1 성공 경로의 원인은 family 미등록 — 도구 구현은 정상 출력을 낸다. rotate_workflow_logs 의 오류 응답도 ErrorOutput 계약 밖이라 함께 고쳤다
- Files that change: workflow-source/workflow_kit/common/schemas/read_only.py
- Files that change: workflow-source/workflow_kit/common/output_contracts.py
- Files that change: workflow-source/tests/check_mcp_tool_output_contracts.py
- Order of work: 1) 세 도구 실출력으로 Pydantic 모델 작성, apply_robust_patch 는 기존 ApplyRobustPatchOutput 등록
- Order of work: 2) 레지스트리 등록 → 생성 스키마 · descriptor 재생성
- Order of work: 3) registry↔family 1:1 검사 + 4 도구 성공 호출 case + 되주입
- Plan risks: descriptor 의 outputSchema 가 generic 에서 상세로 바뀐다 — 생성물 바이트 동일 검사 재생성 필요
- Proof: invoke_tool 4건 rc 0 · 새 검사 · --changed · 전량 게이트

## 🛠️ Implementation / Content

- Progress: `2026-11-15 03:55` 기준 summarize_git_history · assess_milestone_progress · rotate_workflow_logs · apply_robust_patch 가 성공 경로에서 Unknown family 로 invalid_tool_output_contract. 1.22.0 발행본 포함 — 다음 발행 전에 닫는다. 정본 task 는 main 브랜치의 TASK-2026-11-04-main-002.
- Next session starting point:
- Remaining risks: summarize_git_history 는 git 저장소가 아닌 경로에도 rc 0 · status ok — 계약 위반은 아니나 오류를 숨긴다 (verifier 관찰, 미수리)
- Remaining risks: apply_robust_patch 는 SEARCH 불일치에 status error 인데 rc 0 — rc 와 status 가 어긋난다 (verifier 관찰, 미수리)

## ✅ Outcome

- Result: 네 family 등록 + 모델 셋 신설 + rotate 오류 경로 계약화 + 생성 스키마 4종 재생성 + 결함을 고정하던 v0_8_10 예외 제거
- Verification: verifier PASS 3/3 (2026-11-15) — invoke_tool 4 도구 rc 0 · 등록 제거 되주입 red · 모델 필드 제거 되주입 red; 새 검사 check_mcp_tool_output_contracts 4/4, 작성자 되주입 10/10 red
- Follow-up: main 브랜치의 TASK-2026-11-04-main-002 는 이 수리로 해소 — main 메모리에서 done 으로 닫는다
