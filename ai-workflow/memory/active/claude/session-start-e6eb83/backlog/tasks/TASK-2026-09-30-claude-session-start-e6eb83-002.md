---
id: TASK-2026-09-30-claude-session-start-e6eb83-002
status: done
created_at: 2026-09-30
source_anchor: generic-task-2026-09-30-claude-session-start-e6eb83-002
source_path: backlog/2026-09-30.md
kind: generic
wbs: M-007/WBS-7.4
---

# TASK-2026-09-30-claude-session-start-e6eb83-002 — worktree·detached HEAD 에서 브랜치 상태 경로를 못 찾는다 — 자동 seed · 로컬 detached HEAD = 기본 브랜치

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-09-30
- Owner: Claude Code
- Host: macOS
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/common/paths.py`
  - `workflow-source/workflow_kit/tools/session_start.py`
  - `workflow-source/workflow_kit/tools/seed_workspace_memory.py`
  - `workflow-source/workflow_kit/common/state/roadmap.py`
  - `workflow-source/tests/check_branch_memory_auto_seed.py`
  - `workflow-source/tests/check_v0_7_26_branch_detection_fix.py`
  - `workflow-source/core/multi_workspace_orchestration.md`
  - `workflow-source/workflow_kit/tools/audit_root_anchors.py`
  - `workflow-source/tests/check_branch_resolver_agreement.py`
  - `workflow-source/tests/check_backlog_update.py`
  - `workflow-source/tests/check_branch_scoped_memory.py`
  - `workflow-source/tests/check_workflow_linter.py`
  - `docs/CODE_INDEX.md`
  - `docs/INSTALLATION_AND_USAGE.md`

- Description: 110차 macOS 실측: (1) Claude Code worktree 브랜치 claude/session-start-e6eb83 에서 wk session-start 가 active/claude/session-start-e6eb83/session_handoff.md 부재로 missing_required_document — 하네스가 스스로 만든 worktree 는 seed(§5A.2)를 안 거친다. 이어진 backlog-update 는 state.json 만 브랜치 경로에 만들어 메모리가 갈렸다. (2) Codex worktree(detached HEAD 6545f13a)에서 active/6545f13/state.json 생성 — sha slug 는 커밋마다 바뀐다. (3) 조사 중 발견: roadmap 선언 수집이 active/*/ 한 단계만 훑어 슬래시 브랜치 task 를 놓친다. 처음 active/main 에 main-013 으로 등록했으나 브랜치 작업이 active/main 을 고치면 check_branch_memory_namespace 위반이라 이 네임스페이스로 옮김.
- Completion criteria: 네임스페이스 없는 worktree 브랜치에서 wk session-start 가 기본 브랜치 기준 자동 seed 후 status=ok (seed task 는 wbs exempt · done)
- Completion criteria: CI 밖 detached HEAD 는 기본 브랜치로 해석, CI 는 F-7 sha 유지
- Completion criteria: roadmap task 수집이 슬래시 브랜치까지 센다
- Completion criteria: check_branch_memory_auto_seed 8 cases + F-7 6 cases, 되주입 red 확인, 게이트 통과
- Completion criteria: 비 git workspace 는 main 으로 해석 (계약 3 변경, 소유자 결정) — kit 체크아웃 브랜치와 무관

## 🛠️ Implementation / Content

- Progress: 구현·검사 완료. 추가로 계약 3 변경(소유자 결정): resolve_branch_for_workspace 비 git → main(source workspace_non_git) — 변경 전 HEAD 에서도 main 아닌 브랜치면 red 이던 check_ensure_entrypoints · check_session_context_budget 해소, get_current_branch 로 비 git fixture 를 만들던 검사 3종 교정, root anchor 원장의 resolve_branch_for_workspace 항목 제거. 전량 299 중 296 통과 — 남은 3건(check_entry_points 30s · check_task_multivalue_fields 23s · check_wiki_trend)은 병렬 부하 60s 타임아웃, 단독 통과.
- Next session starting point: 커밋 → 깨끗한 트리에서 게이트(--branch-context=all) → push/병합 방식 소유자 확인
- Remaining risks: writer(backlog-update)를 session-start 없이 부르면 여전히 브랜치 dir 에 state.json 만 생길 수 있다 — 범위 밖
- Remaining risks: check_ensure_entrypoints · check_session_context_budget 은 변경 전 HEAD 에서도 main 이 아닌 브랜치면 red (비 git 임시 프로젝트가 모듈 저장소 브랜치로 떨어짐) — 이 브랜치의 게이트를 막는다

## ✅ Outcome

- Result: 6118db3d: session-start 자동 seed · CI 밖 detached HEAD=기본 브랜치 · 비 git workspace=main(계약 3 변경) · seed task_status/wbs exempt/§5 작업 후보 · roadmap 슬래시 브랜치 수집. 이 worktree 자체가 자동 seed 로 시작했다.
- Verification: check_branch_memory_auto_seed 8/8 (되주입 3건 각 red) · F-7 6/6 · check_branch_resolver_agreement · check_self_application 8/8 · 게이트 --branch-context=all native 299/299 · slash 299/299 (6118db3d 통과 기록; 첫 시도는 호스트 부하 load 22 로 check_entry_points·check_wiki_trend 60s 타임아웃, 단독 30s·3s 통과)
- Follow-up: 브랜치 네임스페이스가 main 에 합류해도 active/main/session_handoff.md 에는 이 작업이 실리지 않는다 — 다음 세션이 main 기준선만 읽으면 못 본다 (orchestration §5A.4 C. 합류 단계의 reconcile 이 수동)
- Follow-up: check_entry_points 단독 30s(부하 중 측정) — CHECK_TIMEOUT_S 선언 필요 여부를 부하 없는 호스트에서 재측정
- Follow-up: Codex worktree(detached HEAD)가 남긴 active/6545f13/state.json 은 Codex 쪽 미커밋 산출물 — 새 규칙에서는 생기지 않는다. 정리는 소유자·Codex 확인 후
