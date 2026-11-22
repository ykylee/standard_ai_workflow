---
merged_from: claude/remote-sync-check-234c32
id: TASK-2026-11-19-claude-remote-sync-check-234c32-002
status: done
created_at: 2026-11-19
source_anchor: generic-task-2026-11-19-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-19.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-11-19-claude-remote-sync-check-234c32-002 — 브랜치 네임스페이스 자동 seed 가 roadmap_state.json 을 재생성하지 않는다 — 생성물 대조 검사 2건 red

## 📝 Description

- Status: done
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

- Files that change: workflow-source/workflow_kit/tools/seed_workspace_memory.py (seed 끝에 generate_roadmap_state — session_start · roadmap.py 는 안 바꿈: seed 가 자동 seed 와 CLI 의 공통 마무리 자리)
- Files that change: workflow-source/tests/check_branch_memory_auto_seed.py (case 19)
- Order of work: seed 의 state.json 생성 뒤 roadmap 재생성 → case 19 (로드맵 fixture 저장소 · 생성물 맞춘 커밋 → 새 브랜치 session-start → 대조) → 되주입 → release/1.x 이식
- Plan risks: roadmap/ 이 없는 저장소(로드맵 미사용)에서 seed 가 실패하면 안 된다 — 부재는 건너뛴다
- Proof: case 19 PASS · 호출 제거 되주입 시 case 19 FAIL (exempt_tasks=[] · 대조 불일치) · 복원 19/19 · --changed 321 PASS FAIL 0 · smoke 8/8

## 🛠️ Implementation / Content

- Progress: `2026-11-22 00:01` done — seed 가 roadmap_state 재생성, 1.x 이식
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: seed 가 state.json 생성 뒤 roadmap_state.json 도 재생성한다 (roadmap 부재 → 건너뜀, 예외 → errors). 자동 seed · seed-workspace-memory CLI 둘 다 덮는다. release/1.x 에도 이식 (release-1.x-009)
- Verification: case 19 PASS · 되주입 FAIL→복원 PASS · --changed 321 PASS FAIL 0 · smoke 8/8 (main · release/1.x) · 전량 게이트는 간소화 기간이라 발행 때
- 기준 3 (전량 게이트 native · slash): 검증 간소화 기간(소유자 2026-11-20)이라 미실행 — 다음 발행 전량 게이트에서 잰다
- Follow-up:
