---
id: TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003
status: done
created_at: 2026-10-02
source_anchor: generic-task-2026-10-02-claude-remote-sync-status-1ce0a3-003
source_path: backlog/2026-10-02.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003 — 게이트의 check_roadmap_wiring 이 worktree 에서 실제 저장소의 현재 브랜치 메모리를 합류 반영·아카이브한다

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-10-02
- Owner:
- Host: macOS
- Host IP:
- Affected documents:
  - `workflow-source/tests/check_roadmap_wiring.py`
  - `ai-workflow/memory/archived/feat/`
  - `workflow-source/workflow_kit/tools/archive_branch_memory.py`
  - `workflow-source/tests/check_branch_join_reflect.py`

- Description: 저장소 관찰 session-start 가 CODEX_WORKFLOW_BRANCH=main 강제로 돌아 HEAD 의 현재 브랜치를 '병합된 브랜치' 로 보고 archive-branch-memory --apply 를 실행
- Completion criteria: worktree 에서 check_roadmap_wiring 단독 실행 뒤 ai-workflow/memory git status 무변화
- Completion criteria: 옛 동작(main 강제) 되주입 시 같은 검사가 red
- Completion criteria: check_branch_join_reflect case 6: worktree 에서 CODEX_WORKFLOW_BRANCH=main 강제 session-start 가 자기 브랜치를 반영·아카이브하지 않는다 (수정 전 red)

## 🛠️ Implementation / Content

- Progress: `2026-10-02 22:21` 기준 저장소 관찰 session-start 가 CODEX_WORKFLOW_BRANCH=main 강제로 돌아 HEAD 의 현재 브랜치를 '병합된 브랜치' 로 보고 archive-branch-memory --apply 를 실행
- Next session starting point:
- Remaining risks: main 체크아웃(실제 checkout = main)에서는 여전히 병합만 되고 미반영인 브랜치가 있으면 저장소 관찰 검사가 합류 반영을 쓴다 — 의도된 동작과 같은 경로라 게이트 전에 main 의 session-start 를 먼저 돌려 반영을 커밋할 것 (check_roadmap_wiring 의 전후 무변화 단언이 red 로 알린다)

## ✅ Outcome

- Result: _repo_branch(): 실제 checkout 브랜치(네임스페이스 있을 때) 를 강제, 없으면(detached · slash) main. test_repo_session_start_reports_roadmap 에 관찰 전후 ai-workflow/memory porcelain 동일 단언 추가
- Result: 같은 게이트가 잡은 아카이브 결함 수리: f3de0dba 의 철회된 M-022 링크 비링크화 · state.json 의 active/main 경로를 자기 아카이브 경로로 · 열린 task 5건에 carried_over_to(main-001 · main-012 · remote-sync-status-002)
- Result: 근본 수리(kit): archive_branch_memory 가 git symbolic-ref 로 실제 checkout 브랜치를 읽어 keep 에 넣고, 합류 반영은 checkout 이 기본 브랜치(또는 detached)일 때만. 두 번째 범인 check_state_reconcile case 7(같은 main 강제 패턴)도 이 수리로 무변화
- Verification: check_branch_join_reflect 6/6 (case 6 수정 전 red) · check_state_reconcile 7 · check_roadmap_wiring 6/6 · archive_history 17 · namespace 12 · auto_seed 13 · self_location 8/8 · convention 5/5 — 모두 실행 뒤 ai-workflow git status 무변화
- Follow-up:
