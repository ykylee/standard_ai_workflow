---
carried_over_to: TASK-2026-11-20-claude-workflow-hub-concept-007@main
id: TASK-2026-11-20-claude-workflow-hub-concept-007
status: done
created_at: 2026-11-20
source_anchor: generic-task-2026-11-20-claude-workflow-hub-concept-007
source_path: backlog/2026-11-20.md
kind: generic
wbs: exempt
wbs_exempt_reason: 1.x 결함 수리 — 로드맵 밖
---

# TASK-2026-11-20-claude-workflow-hub-concept-007 — 런타임 오류가 예외 이름만 내고 원인을 감춘다 — exception_message · pydantic 필드 오류를 오류 결과에 싣는다

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-20
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/common/errors.py`

- Description: backlog-update 가 WBS 제목 200자 초과를 ValidationError 이름만으로 보고했다. catch-all 5곳(backlog_update 2 · session_start · doc_sync · writing_bundle)이 source_context 에 exception_type 만 싣는다.
- Completion criteria: 5곳 catch-all 오류 결과에 exception_message 가 있다
- Completion criteria: pydantic ValidationError 는 exception_errors 에 loc · msg 가 있고 error 문안에 첫 원인이 보인다
- Completion criteria: 검사가 헬퍼 되돌림 · 한 곳 누락 되주입에 red

## 🧭 Plan

- Claims: C1 catch-all 런타임 오류 결과에 예외 메시지가 실린다
- Claims: C2 pydantic ValidationError 는 필드 위치 · 메시지가 실린다
- Files that change: workflow-source/workflow_kit/common/errors.py
- Files that change: workflow-source/workflow_kit/tools/backlog_update.py
- Files that change: workflow-source/workflow_kit/tools/session_start.py
- Files that change: workflow-source/workflow_kit/tools/doc_sync.py
- Files that change: workflow-source/workflow_kit/common/writing_bundle.py
- Order of work: 공용 헬퍼 exception_context 추가
- Order of work: 5곳 적용
- Order of work: 검사 추가 · 되주입
- Order of work: --changed + 스모크 · 커밋 · push
- Plan risks: 오류 결과 계약(contracts/errors.py) 이 source_context 추가 키를 거절할 수 있다
- Proof: 200자 초과 제목 재현에서 오류 결과에 필드 loc 와 msg 가 보인다 · 신규 검사 green · 헬퍼 되돌리면 red

## 🛠️ Implementation / Content

- Progress: `2026-11-20 22:41` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: common/errors.py exception_context · describe_exception 신설, catch-all 6곳(backlog_update 3 · session_start · doc_sync · writing_bundle) 적용, 오류 계약 3 family 에 exception_message · exception_errors 선언, 스모크 수 333→334
- Verification: check_exception_context 8/8 · 되주입 4종(메시지 드롭 · 필드 오류 드롭 · doc_sync 이름만 복귀 · 계약 키 드롭) 전부 red · 200자 WBS 제목 실재현: 수리 전 exception_type 만 → 수리 후 'ValidationError(WbsNode) — title: String should have at most 200 characters' · --changed 310/312 (나머지 2 = load 17 중 timeout, 단독 green) · smoke 8/8 · verifier 생략(검증 간소화 기간)
- Follow-up:
