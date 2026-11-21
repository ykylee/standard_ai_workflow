---
merged_from: claude/workflow-hub-concept@8ef1ee07
id: TASK-2026-11-21-claude-workflow-hub-concept-012
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-012
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-21-claude-workflow-hub-concept-012 — 로드맵 현재 마일스톤을 병행 선언 기준으로 — 상시 운영 M-007 이 늘 '현재' 로 보고되던 것

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: current_milestone_id 가 'order 순 첫 in_progress' 라 상시 운영 M-007 이 늘 이긴다. 소유자 결정(2026-11-21): 다른 in_progress 마일스톤의 parallel_allowed 에 오른 것은 배경으로 보고, 나머지 중 order 첫째를 현재로.
- Completion criteria: C1 이 check_roadmap_integrity fixture case(배경 1 · 배경 2단 · 순환 · 단독)로 실측되고 옛 규칙 되주입에서 red
- Completion criteria: C2 스펙 roadmap_milestone_wbs_spec §7.1 과 스키마 description 이 같은 규칙을 말한다

## 🧭 Plan

- Claims: C1 current_milestone_id = in_progress 중 다른 in_progress 의 parallel_allowed 에 없는 것의 order 첫째, 전부 배경이면(순환) order 첫 in_progress
- Claims: C2 규칙 문안이 스펙 · 스키마에 하나로 적혀 있다
- Files that change: workflow-source/workflow_kit/common/state/roadmap.py
- Files that change: workflow-source/workflow_kit/common/schemas/roadmap.py
- Files that change: workflow-source/core/roadmap_milestone_wbs_spec.md
- Files that change: workflow-source/tests/check_roadmap_integrity.py
- Order of work: 규칙 구현 → 스키마 · 스펙 문안 → fixture case · 되주입 → --changed · 스모크
- Plan risks: current_milestone_id 소비자(대시보드 phase · session-start · compact relay) 표시가 바뀐다 — 의도된 변화
- Proof: check_roadmap_integrity 신규 case PASS + 옛 규칙 되주입 red, 이 저장소 roadmap_state current 가 M-028

## 🛠️ Implementation / Content

- Progress: `2026-11-21 01:49` close
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 이 저장소 current_milestone_id M-007 → M-028 (M-036 개시 뒤 M-036)
- Verification: check_roadmap_integrity 10/10 (신규 case 6시나리오), 옛 규칙 되주입 red 2/6 · run_all_checks --changed --changed-base d3d8c9a7 323 PASS 0 FAIL · 스모크 PASS · verifier 생략(검증 간소화 기간)
- Follow-up:
