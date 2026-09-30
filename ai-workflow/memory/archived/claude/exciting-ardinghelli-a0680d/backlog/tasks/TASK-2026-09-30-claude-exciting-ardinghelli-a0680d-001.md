---
id: TASK-2026-09-30-claude-exciting-ardinghelli-a0680d-001
status: done
created_at: 2026-09-30
source_anchor: generic-task-2026-09-30-claude-exciting-ardinghelli-a0680d-001
source_path: backlog/2026-09-30.md
kind: generic
wbs: exempt
wbs_exempt_reason: 게이트 간헐 red 를 내는 단일 검사 격리 수정 (로드맵 밖 유지보수)
---

# TASK-2026-09-30-claude-exciting-ardinghelli-a0680d-001 — release-notes-template 검사가 실 releases/ 에 쓰지 않게 격리

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-09-30
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/tests/check_v0_7_24_release_notes_template.py`
  - `workflow-source/workflow_kit/tools/release_pipeline_changelog.py`

- Description: check_v0_7_24_release_notes_template 의 simple template 검사가 workflow-source/releases/ 에 Beta-v9.9.9-test*.md 를 썼다 지워 게이트 repo-touch 탐지기가 간헐 red. _resolve_notes_file 에 releases_dir 주입 + 검사를 tmp 로 옮기고 저장소 무오염 단언 추가
- Completion criteria: 검사가 tmp releases 디렉터리만 쓰고, 저장소 releases/ 에 쓰면 실패하는 주입 단언이 있다
- Completion criteria: run_all_checks --changed 와 게이트 통과

## 🛠️ Implementation / Content

- Progress: _resolve_notes_file 에 releases_dir 주입 인자 · 검사는 임시 디렉터리 + 저장소 releases/ 전후 스냅샷 단언
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: 검사가 저장소 releases/ 에 쓰지 않는다. 변이 2종(주입 무시 · 저장소 쓰기)을 새 단언이 모두 잡음을 실측. 형제 검사(changelog_gen · lib · deploy_doctor · wrapper_args)는 dry-run/임시 프로젝트만 써 같은 패턴 없음
- Verification: run_all_checks --changed 272/272 · check_self_application 8/8 · 변이 A/B 검출
- Follow-up:
