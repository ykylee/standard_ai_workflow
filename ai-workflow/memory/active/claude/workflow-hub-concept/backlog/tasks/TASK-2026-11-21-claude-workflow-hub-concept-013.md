---
id: TASK-2026-11-21-claude-workflow-hub-concept-013
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-013
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-21-claude-workflow-hub-concept-013 — handoff §5 서두의 회차 줄이 예산 밖에서 쌓인다 — 누적형으로 세고 이관

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: context_budget.split_s5_blocks 가 첫 ### 앞 서두를 통째로 현재형으로 쳐서, session-end · 합류 · seed 가 서두에 쌓는 '- (N차 …)' 줄이 예산에도 rollover 에도 안 잡힌다. 이 브랜치 §5 21KB 중 대부분이 그것(이어받은 main 29줄).
- Completion criteria: C1 · C2 · C3 가 fixture case 로 실측되고 서두를 통째 현재형으로 되돌린 되주입에서 red, 기존 rollover · budget 검사 green
- Completion criteria: C4 이 브랜치 handoff §5 누적형이 8,192B 이하로 이관됐다 (삭제 0)
- Completion criteria: C5 session_context_budget_spec §2 가 서두 회차 줄 규칙을 말한다

## 🧭 Plan

- Claims: C1 §5 서두의 '- (' 로 시작하는 회차 줄은 누적형 블록(한 줄 = 한 블록)으로 세고, 그 밖 서두 줄은 현재형 그대로
- Claims: C2 seed 의 이어받음 머리줄('아래 N줄은')은 뒤 N줄과 한 블록 — 일부만 옮겨 'N줄' 이 거짓이 되지 않는다
- Claims: C3 rollover 가 서두 회차 줄을 아래부터 sessions/handoff-notes_<날짜>.md 로 바이트 그대로 옮기고 포인터 하나, 노트 절 수 = 포인터 건수
- Claims: C4 이 브랜치 §5 누적형 ≤ 8,192B
- Claims: C5 spec §2 문안
- Files that change: workflow-source/workflow_kit/common/context_budget.py
- Files that change: workflow-source/workflow_kit/tools/rollover_handoff_notes.py
- Files that change: workflow-source/core/session_context_budget_spec.md
- Order of work: 분류 수리 → rewrite 재조립 → spec → fixture · 되주입 → 이 브랜치 --apply → --changed · 스모크
- Plan risks: 현재형으로 쓰던 서두 줄이 '- (' 로 시작하면 이관된다 — 현재 지시는 ### ▶ 지금 할 일 절에 두는 것이 계약
- Proof: rollover dry-run 이 이 브랜치에서 누적형 >8KB 를 보고하고 --apply 뒤 ≤8KB, 옮긴 줄이 노트 파일에 그대로

## 🛠️ Implementation / Content

- Progress: `2026-11-21 01:49` close
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 이 브랜치 §5 누적형 29,068B → 6,092B, handoff 38.5KB → 16KB, 옮긴 줄 누락 0 (sessions/handoff-notes_2026-11-21.md). 함께 고친 것: 포인터가 서두 #### 소절 안에 들어감 · 건수 0 대상 링크(죽은 링크)
- Verification: check_session_context_budget 12/12 (case 12 신규), 되주입 5종 red(서두 통째 현재형 · 묶음 무시 · rewrite 미제거 · 포인터 위치 · 죽은 링크) · --changed 323 PASS · 스모크 PASS · verifier 생략(검증 간소화 기간)
- Follow-up:
