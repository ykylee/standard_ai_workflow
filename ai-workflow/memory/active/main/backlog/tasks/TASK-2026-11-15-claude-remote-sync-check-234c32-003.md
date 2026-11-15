---
merged_from: claude/remote-sync-check-234c32@7fdf0eb5
id: TASK-2026-11-15-claude-remote-sync-check-234c32-003
status: done
created_at: 2026-11-15
source_anchor: generic-task-2026-11-15-claude-remote-sync-check-234c32-003
source_path: backlog/2026-11-15.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-15-claude-remote-sync-check-234c32-003 — 합류 반영이 완료 task 를 archived/ 로만 보내 main 집계가 근거를 잃는다 — 완료 task 도 모 브랜치로 옮긴다

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-15
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/common/branch_join.py`
  - `workflow-source/tests/check_branch_join_reflect.py`
  - `workflow-source/workflow_kit/tools/archive_branch_memory.py`

- Description: archive-branch-memory 의 합류 반영(branch_join)은 열린 task 만 모 브랜치로 이월하고 완료 task 는 handoff 최근 완료 한 줄만 남긴 채 archived/ 로 보낸다. roadmap 은 active/** 만 읽어, 이 브랜치에서만 진행한 M-022~M-027 · M-029 가 '선언 done ≠ 파생 planned' 7건 · check_roadmap_integrity red. main 의 session-start 가 자동으로 반영하므로 main 의 다음 세션이 바로 맞는다 (2026-11-15 main 워크트리 실측). 소유자 결정: 완료 task 도 모 브랜치로.
- Completion criteria: 합류 반영 뒤 브랜치의 자체 완료 task 파일이 모 브랜치 네임스페이스에 merged_from 원류와 함께 있고 wbs 줄 · status done 이 유지된다 — check_branch_join_reflect 에서 잼
- Completion criteria: 합류 반영 뒤 roadmap 의 task 링크 수집(collect_task_wbs_links)이 그 완료 task 를 센다 — fixture 로 잼, 옮기기를 되돌리면 red
- Completion criteria: 이 저장소 main 체크아웃에서 claude/remote-sync-check-234c32 를 합류 반영한 뒤 roadmap issues [] · check_roadmap_integrity · check_roadmap_wiring green

## 🧭 Plan

- Claims: C1 결함은 합류 반영이 완료 task 를 모 브랜치 집계 밖에 두는 것 하나다
- Decisions: D1 [C1] 완료 task 의 근거를 어디에 두는가? | default: copy-to-parent | options: copy-to-parent = 합류 반영이 완료 task 파일을 모 브랜치 네임스페이스로 옮긴다; roadmap-reads-archived = roadmap 이 archived/ 의 done task 의 wbs 링크도 센다 | state: answered:copy-to-parent
- Files that change: workflow-source/workflow_kit/common/branch_join.py
- Files that change: workflow-source/tests/check_branch_join_reflect.py
- Files that change: workflow-source/workflow_kit/tools/archive_branch_memory.py
- Order of work: 1) plan_join: 완료 task 도 옮김 대상(같은 ID 가 모 브랜치에 있으면 충돌) 2) reflect_join: 이월과 같은 길로 옮김 3) 검사 case 1 확장 + 되주입 4) main 워크트리에서 실제 합류 반영 → roadmap 확인
- Plan risks: 모 브랜치 네임스페이스에 브랜치 ID 의 완료 task 가 쌓인다 — 이월과 같은 형식이라 기존 규칙 안
- Proof: check_branch_join_reflect · 되주입 · main 워크트리 roadmap issues

## 🛠️ Implementation / Content

- Progress: D1 소유자 답(2026-11-15 세션 질의): 완료 task 를 main 으로 (copy-to-parent)
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: branch_join: 자체 task 를 열린 것도 완료한 것도 merged_from 과 함께 모 브랜치로, 같은 ID 충돌은 완료 task 도 차단, seed 사건 task 는 제외. 검사 case 1 확장 + 5b 신설
- Verification: verifier PASS 3/3 (2026-11-15): check_branch_join_reflect 7/7 · 수리 전 코드 되주입 red(완료 task 미이동 · 링크 수집 None · 완료 충돌 미차단 · seed 이동) · main 워크트리 실측 수리 전 issues 7 → 수리 뒤 0, roadmap_integrity 9/9 · wiring 6/6, 옮긴 task 15(done 13 · planned 1 · in_progress 1) wbs 보존
- Follow-up:
