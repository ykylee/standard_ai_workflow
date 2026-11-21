---
id: TASK-2026-11-21-claude-workflow-hub-concept-005
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-005
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-033/WBS-33.4
---

# TASK-2026-11-21-claude-workflow-hub-concept-005 — 허브 코어 — 원격 MCP 골격 · 부트스트랩 묶음 · 인증 경계

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/hub/`
  - `workflow-source/tests/check_hub_core.py`

- Description: M-033/WBS-33.4. hub_spec.md 의 해당 절을 workflow_kit/hub/ 로 구현. 게이트(done · 계획 린트)는 M-035.
- Completion criteria: 토큰 없는 MCP 연결은 부트스트랩 묶음만 보이고 토큰 연결은 전체, MCP 와 HTTP 가 같은 함수 결과를 낸다
- Completion criteria: check_hub_core 해당 case 가 green 이고 되주입에 red

## 🧭 Plan

- Claims: C1 토큰 없는 MCP 연결은 부트스트랩 묶음만 보이고 토큰 연결은 전체, MCP 와 HTTP 가 같은 함수 결과를 낸다
- Claims: C2 검사 check_hub_core 가 실제 프로세스 · 실제 포트로 재고 되주입에 red 다
- Files that change: workflow-source/workflow_kit/hub/
- Files that change: workflow-source/tests/check_hub_core.py
- Files that change: workflow-source/pyproject.toml
- Order of work: 구현
- Order of work: 검사 작성 · 되주입
- Order of work: --changed + 스모크
- Order of work: 커밋 · push
- Plan risks: 새 mcp 사용 표면이 기존 SDK 호환 검사의 표면 목록과 어긋날 수 있다
- Proof: check_hub_core case 별 PASS · 되주입 red

## 🛠️ Implementation / Content

- Progress: `2026-11-21 00:33` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: workflow_kit/hub/ (errors · gitkey · db · store · tools · app) + tools/hub.py (serve · backup · admin) + workflow_kit[hub] extra
- Verification: check_hub_core 10/10 (실제 프로세스 · 실제 포트 · MCP SDK 클라이언트) · 되주입 6종(목록 경계 · version 대조 · 토큰 검사 · 갱신 이력 · 대소문자 규칙 · 이관 원자성) 해당 case red, 복원 10/10 · --changed 첫 실행 red 6 → 스모크 수 335 · 스탬프 · optional_deps hub 등록 · SDK 필드 getattr · WATCHES 넓힘 · check_state_json_generated case 5 를 현재 브랜치 생성물로(main 고정이 네임스페이스 규칙과 충돌, 되주입 확인) + active/main/state.json 을 origin/main 판으로 되돌림 · sdk_matrix 1.27.0/1.29.0/2.1.1 은 check_mcp_tool_output_contracts case 5 만 red — 매트릭스 tmp 가 저장소 안이라 생기는 기존 결함(TMPDIR 을 저장소 안으로 준 직접 실행에서 재현, 밖이면 6/6) · verifier 생략(검증 간소화 기간)
- Follow-up: 1.x 결함: sdk_matrix 의 --tmp-dir 가 저장소 안(.venv-sdk-matrix/_tmp)이라 check_mcp_tool_output_contracts case 5 가 매트릭스에서만 red
