---
inherited_from: main@e16ce897
inherited_hash: sha256:f6fdf0bca13af10097e8db0f894c14a6872702ce03d0f890aa4003884f93a44e
merged_from: claude/remote-sync-check-234c32
id: TASK-2026-11-19-claude-remote-sync-check-234c32-002
status: planned
created_at: 2026-11-19
source_anchor: generic-task-2026-11-19-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-19.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-19-claude-remote-sync-check-234c32-002 — 브랜치 네임스페이스 자동 seed 가 roadmap_state.json 을 재생성하지 않는다 — 생성물 대조 검사 2건 red

## 📝 Description

- Status: planned
- Priority: medium
- Request date: 2026-11-19
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: session-start 의 자동 seed(_auto_seed_branch_memory → seed_workspace_memory)가 exempt seed task 를 새로 만들지만 roadmap_state.json 은 갱신하지 않아, 커밋 뒤 전량 게이트에서 check_roadmap_state_generated · check_state_json_generated 가 red 였다(2026-11-19 이 브랜치 재seed 실측 — exempt_tasks 에 TASK-2026-11-19-claude-remote-sync-check-234c32-001 누락). 손으로 refresh-state 를 돌려 seed 커밋에 합쳐 통과시켰다(2787e9e0).
- Completion criteria: seed 직후(추가 명령 없이) roadmap_state.json 이 생성기 출력과 같다 — seed 한 저장소에서 check_roadmap_state_generated 의 대조 case 가 PASS
- Completion criteria: 회귀 검사 case 1개 이상: seed 를 돌린 fixture 저장소에서 roadmap_state.json 의 exempt_tasks 에 seed task 가 있다 — 수리를 되돌리면 red 가 되는지 되주입으로 확인
- Completion criteria: 전량 게이트 --branch-context=all native · slash 전부 green

## 🧭 Plan

- Files that change: workflow-source/workflow_kit/tools/session_start.py
- Files that change: workflow-source/workflow_kit/tools/seed_workspace_memory.py
- Files that change: workflow-source/workflow_kit/common/state/roadmap.py
- Order of work:
- Plan risks: roadmap/ 이 없는 저장소(로드맵 미사용)에서 seed 가 실패하면 안 된다 — 부재는 건너뛴다
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-19 15:00` 등록 — 착수 전
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
