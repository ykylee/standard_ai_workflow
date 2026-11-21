---
id: TASK-2026-11-21-fix-1x-long-lived-branch-memory-002
status: in_progress
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-fix-1x-long-lived-branch-memory-002
source_path: backlog/2026-11-21.md
kind: generic
wbs: exempt
wbs_exempt_reason: 1.x 결함 수리 줄 (R16.1) — 2.0 로드맵 밖
---

# TASK-2026-11-21-fix-1x-long-lived-branch-memory-002 — 1.x 결함 — 오래 사는 브랜치 메모리가 기본 브랜치 합류 때 반영 · 아카이브된다 (.long-lived 표시)

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 기본 브랜치 체크아웃의 session-start 가 브랜치 tip 이 HEAD 에 병합된 순간 살아 있는 브랜치 네임스페이스를 반영하고 archived/ 로 옮긴다. 브랜치를 계속 쓰면서 자주 main 에 합치는 소비 저장소 (arcturus-port claude-macmini 브랜치 · 2026-11-21 실측: 사본 충돌이 풀리자 125 개 이동 · 89 task 반영) 에서는 다음 병합이 아카이브된 경로와 충돌하거나 기록이 엉뚱한 곳으로 간다. R16.1 ② 저장소 오염 결함 (소유자 2026-11-21 분류). 수리: 브랜치가 자기 네임스페이스에 .long-lived 표시를 두면 git 에 브랜치가 있는 동안 반영 · 아카이브하지 않는다. 브랜치가 사라지면 평소대로.
- Completion criteria: check_branch_join_reflect 12 cases PASS (새 9 · 9b) · 표시 없이 되돌리면 9 가 FAIL · 명세 multi_workspace_orchestration 합류 반영 절에 표시 규칙

## 🧭 Plan

- Files that change: workflow-source/workflow_kit/tools/archive_branch_memory.py (LONG_LIVED_MARKER · 후보 루프)
- Files that change: workflow-source/tests/check_branch_join_reflect.py (case 9 · 9b)
- Files that change: workflow-source/core/multi_workspace_orchestration.md (합류 반영 한계 다음)
- Order of work: 표시 상수 · 후보 루프에서 ref 있고 표시 있으면 skip (병합 판정 앞)
- Order of work: case 9 (표시 → 병합돼도 유지) · 9b (브랜치 삭제 → 아카이브)
- Order of work: 명세 · release/1.x 에 PR · 같은 변경을 main(2.0) 에 (R16.5 1.x → 2.0)
- Plan risks: 표시를 지우지 않고 브랜치만 남겨 두면 영원히 반영되지 않는다 — 브랜치 삭제나 표시 삭제가 끝내는 신호 (명세에 적음)
- Proof: check_branch_join_reflect · 되돌린 판에서 case 9 FAIL

## 🛠️ Implementation / Content

- Progress: `2026-11-21 12:31` 기준 기본 브랜치 체크아웃의 session-start 가 브랜치 tip 이 HEAD 에 병합된 순간 살아 있는 브랜치 네임스페이스를 반영하고 archived/ 로 옮긴다. 브랜치를 계속 쓰면서 자주 main 에 합치는 소비 저장소 (arcturus-port claude-macmini 브랜치 · 2026-11-21 실측: 사본 충돌이 풀리자 125 개 이동 · 89 task 반영) 에서는 다음 병합이 아카이브된 경로와 충돌하거나 기록이 엉뚱한 곳으로 간다. R16.1 ② 저장소 오염 결함 (소유자 2026-11-21 분류). 수리: 브랜치가 자기 네임스페이스에 .long-lived 표시를 두면 git 에 브랜치가 있는 동안 반영 · 아카이브하지 않는다. 브랜치가 사라지면 평소대로.
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
