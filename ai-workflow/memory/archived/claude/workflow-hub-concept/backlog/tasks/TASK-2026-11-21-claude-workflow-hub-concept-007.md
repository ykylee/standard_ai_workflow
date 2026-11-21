---
carried_over_to: TASK-2026-11-21-claude-workflow-hub-concept-007@main
id: TASK-2026-11-21-claude-workflow-hub-concept-007
status: done
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-claude-workflow-hub-concept-007
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-034/WBS-34.2
---

# TASK-2026-11-21-claude-workflow-hub-concept-007 — 허브 지침 렌더링 — 표준 규칙(2.0판) · 프로젝트 지침 · 하네스 4종 · 판 · 로컬 수정 감지

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/workflow_kit/hub/`
  - `workflow-source/core/hub_workflow_standard.md`
  - `workflow-source/tests/check_hub_bootstrap.py`

- Description: M-034/WBS-34.2. hub_spec §5 · §6.1 · §6.2 · §6.5 구현.
- Completion criteria: 렌더 영역이 판 · 해시 머리를 갖고, 로컬에서 고친 영역은 덮어쓰지 않으며, 4종 모두 8KiB 예산 안이다
- Completion criteria: check_hub_bootstrap 해당 case green · 되주입 red

## 🧭 Plan

- Claims: C1 렌더 영역이 판 · 해시 머리를 갖고, 로컬에서 고친 영역은 덮어쓰지 않으며, 4종 모두 8KiB 예산 안이다
- Claims: C2 check_hub_bootstrap 이 실제 git 저장소 · 실제 허브 프로세스로 재고 되주입에 red 다
- Files that change: workflow-source/workflow_kit/hub/
- Files that change: workflow-source/tests/check_hub_bootstrap.py
- Order of work: 구현
- Order of work: 검사 · 되주입
- Order of work: --changed + 스모크
- Order of work: 커밋 · push
- Plan risks: 원격 MCP 가 저장소를 못 보므로 판정 입력(훑기 · 명령 결과)을 에이전트가 정직하게 보낸다는 가정 — 결과 없음은 미확인으로
- Proof: check_hub_bootstrap case PASS · 되주입 red

## 🛠️ Implementation / Content

- Progress: `2026-11-21 00:51` 커밋 · push
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: hub/ setup · render · session · guide_page · _standard_snapshot + core/hub_workflow_standard.md + DB 판 2 + 도구 4 (hub_setup_plan · hub_setup_confirm · hub_session_start · hub_guide_render) + hub admin guide set
- Verification: check_hub_bootstrap 8/8 (실제 허브 프로세스 · 실제 git 저장소 · bare origin 으로 뒤처짐/갈라짐/미커밋 재현) · 되주입 6종(.gitignore 관문 · 부정 패턴 판정 · 로컬 수정 감지 · 해시 대조 · 갈라짐 판정 · 정본만 고친 스냅샷) 모두 red — 첫째는 예외로 죽어 case 판정으로 남도록 고침 · fixture 가 git 의미(부모 디렉터리가 무시되면 파일 ! 는 효과 없음)와 달라 디렉터리 부정 · 파일 부정 · 추적 중 세 경우로 고침 · 새 DB 에서 쓸모없는 이관 사본 만들던 것 고침 · check_hub_core 10/10 · mypy strict 5건 수정 · --changed 319/319 · 하네스 등록 명령(codex · agy)은 실행하지 않음(§16.3 실측 몫) · verifier 생략(검증 간소화 기간)
- Follow-up:
