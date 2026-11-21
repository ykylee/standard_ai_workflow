---
merged_from: claude/workflow-hub-concept@8ef1ee07
id: TASK-2026-11-21-claude-workflow-hub-concept-010
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-010
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-035/WBS-35.2
---

# TASK-2026-11-21-claude-workflow-hub-concept-010 — 허브 로드맵 — 마일스톤 · WBS · WBS 게이트 · 진척 파생

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/hub/`
  - `workflow-source/workflow_kit/tools/backlog_update.py`
  - `workflow-source/workflow_kit/common/state/roadmap.py`

- Description: M-035/WBS-35.2. hub_spec §2.2 판정 손질 표 — 1.x 함수에 데이터 입구(enforce_plan_contract 선택 인자 · judge_wbs · assemble_roadmap · derive_state 콜백)를 내고 허브가 부른다.
- Completion criteria: 허브 DB 의 로드맵으로 1.x 와 같은 judge_wbs · derive_state 결과를 내고, 스키마 오류는 필드 · 제약과 함께 거절된다
- Completion criteria: 1.x 게이트 · 로드맵 검사가 그대로 green

## 🧭 Plan

- Claims: C1 허브 DB 의 로드맵으로 1.x 와 같은 judge_wbs · derive_state 결과를 내고, 스키마 오류는 필드 · 제약과 함께 거절된다
- Claims: C2 1.x 경로의 판정은 바뀌지 않는다 (기존 게이트 · 로드맵 검사 그대로 green)
- Files that change: workflow-source/workflow_kit/hub/
- Files that change: workflow-source/workflow_kit/tools/backlog_update.py
- Files that change: workflow-source/workflow_kit/common/state/roadmap.py
- Order of work: 1.x 입구 손질
- Order of work: 허브 판정 구현
- Order of work: 검사 · 되주입
- Order of work: 커밋 · push
- Plan risks: 1.x 함수 손질이 기존 동작을 바꿀 위험 — 선택 인자 기본값 = 지금 동작, 기존 검사로 확인
- Proof: 1.x 검사 green · check_hub_judge 대조 case · 되주입

## 🛠️ Implementation / Content

- Progress: `2026-11-21 01:08` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: hub/judge.py + 도구 6 (hub_task_close · hub_plan_respond · hub_plan_status · hub_roadmap_get/put/state) + task 생성 · 갱신 판정 훅 + DB 판 3. 허브는 작업 트리가 없어 L5 · 산출물 존재는 미측정으로 싣는다
- Verification: check_hub_judge 7/7 (1.x 와 대조: WBS 게이트 매트릭스 · derive_state · done 게이트 kit error_code · 계획 린트 · 결정 응답 자격 · 걷기 사유) · 허브 어댑터 되주입 6종(draft 무시 · 수신 자격 생략 · 검증 요구 생략 · 린트 생략 · 산출물 미측정 생략 · 걷기 사유 채움) 모두 red · 1.x 손질(enforce_plan_contract 선택 인자 · judge_wbs · assemble_roadmap · index_text_is_draft · derive_state 콜백) 뒤 1.x 검사 check_plan_gate 22/22 · roadmap 6종 green · check_hub_core 10/10 · check_hub_bootstrap 8/8 · mypy strict green · --changed 315/315 · verifier 생략(검증 간소화 기간)
- Follow-up:
