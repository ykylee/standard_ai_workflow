---
id: TASK-2026-11-21-claude-workflow-hub-concept-011
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-011
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-035/WBS-35.1
---

# TASK-2026-11-21-claude-workflow-hub-concept-011 — 허브 콜사인별 기억 — handoff · 세션 끝 · compact 체크포인트 · state.json v1 · 보관

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/hub/`
  - `workflow-source/core/hub_spec.md`

- Description: M-035/WBS-35.1. hub_spec §3.3 (handoff · memory_note · checkpoint) · §6.3 · §6.4 · 요구 R4.5 · R6 · R11. state.json v1 은 허브 데이터를 임시 디렉터리에 1.x 배치로 펼쳐 1.x build_workflow_state_payload 로 만든다 (리팩터 대신, 1.x 코드 무변경).
- Completion criteria: C1 · C2 · C3 가 check_hub_memory 로 실측된다
- Completion criteria: 되주입에 red

## 🧭 Plan

- Claims: C1 handoff 는 콜사인 하나에 하나 · 최근 완료는 TASK- 로 시작 · 10건 넘으면 지우지 않고 옮긴다 · 다른 콜사인은 읽기만
- Claims: C2 hub_state 가 같은 데이터의 1.x 배치에서 1.x 생성기가 낸 state.json 과 같은 칸 값을 낸다
- Claims: C3 compact 직후 확인이 그 사이 다른 콜사인의 변경과 요약에서 빠진 식별자를 알리고, 요약이 없으면 대조 불가로 보고한다
- Files that change: workflow-source/workflow_kit/hub/
- Files that change: workflow-source/tests/check_hub_memory.py
- Order of work: 구현
- Order of work: 검사 · 되주입
- Order of work: --changed + 스모크
- Order of work: 커밋 · push
- Plan risks: 펼침 어댑터가 1.x 배치 형식을 잘못 흉내 내면 생성기가 조용히 빈 값을 낸다 — 같은 데이터의 1.x 원본 배치 결과와 대조한다
- Proof: check_hub_memory case PASS · 1.x 대조 · 되주입 red

## 🛠️ Implementation / Content

- Progress: `2026-11-21 01:20` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: hub/memory.py (handoff · session_end · checkpoint · compact_resume · state) + 도구 6 + DB 판 4 · 세션 시작이 내 handoff 를 돌려줌 · 상태 생성은 1.x 배치 펼침 어댑터 (hub_spec §2.2 갱신)
- Verification: check_hub_memory 5/5 — state.json v1 은 이 검사가 손으로 쓴 1.x 배치의 생성기 출력과 대조 · 되주입 5종(넘침 옮김 제거 · handoff version 대조 제거 · 펼침에서 handoff 누락 · 그 사이 변경 놓침 · 빠진 식별자 대조 제거) 모두 red · 검사가 잡은 실제 결함: compact '그 사이 변경' 을 초 단위 시각으로 비교해 같은 초의 변경을 놓침 → 이벤트 순번으로 고침 · 단일 출처 검사 2건(task ID 정규식 · handoff 경로 조립) → 정본 import · check_hub_bootstrap 의 handoff 미확인 기대를 구현 상태로 갱신 · --changed 317/317 · verifier 생략(검증 간소화 기간)
- Follow-up:
