---
id: TASK-2026-11-13-claude-remote-sync-check-234c32-004
status: in_progress
created_at: 2026-11-13
source_anchor: generic-task-2026-11-13-claude-remote-sync-check-234c32-004
source_path: backlog/2026-11-13.md
kind: generic
wbs: M-028/WBS-28.2
---

# TASK-2026-11-13-claude-remote-sync-check-234c32-004 — 주장 트리 계획 구현 2단계 — 응답 파일 · 받은편지함 · plan-import · 받은편지함 게이트 · 이어받기 · 정본 §11.1

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-13
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: ADR-031 결정 26 의 2단계를 구현한다 (계약은 workflow-source/core/claim_plan_spec.md §6 · §7 · §8.1~§8.3 · §8.6 · §9 · §10 의 받은편지함 · §11). 응답 파일을 읽어 자격을 판정하고, plan-import 로 받은편지함의 응답을 보관으로 옮겨 결정 상태를 다시 계산하고, 미반영 응답이 있으면 done 을 거부하고, 이어받기가 보관 응답을 옮긴다. MCP 도구 · 워크벤치는 범위 밖 (ADR-032).
- Completion criteria: [C1] 스펙 §8.1 의 0~6 단계마다 어긋난 응답은 옮겨지지 않고 받은편지함에 남으며 파일별 결과에 단계 번호가 나온다; 0 단계에서는 plan-import 의 --apply · --discard 가 rc 1 · plan_lint_error · 무변경이고 task 를 고친 뒤 같은 호출이 통한다; 보관에 있는 응답도 자격을 잃으면(지문 변경 · 손 편집) 계산에 들지 않는다 (check_plan_import 의 자격 표)
- Completion criteria: [C2] plan-import --apply 가 자격 있는 응답을 보관으로 옮기고 상태 칸을 다시 적고 Progress 에 한 줄을 남기며, dry-run 은 같은 판정을 내고 아무것도 쓰지 않는다; --discard 는 .rejected.md 로 옮기고 다시 계산한다; 같은 응답 집합을 일괄 · 하나씩 · 어느 순서로 반영해도 끝 상태 칸이 같고 다시 불러도 바뀌지 않는다
- Completion criteria: [C2] 번호는 접미사를 통틀어 유일하고 이동은 있는 파일을 덮지 않는다; 잠금을 못 쥔 plan-import 는 import_busy (rc 0 · 무변경)다; 쓰는 쪽 × 옮기는 쪽 둘의 경합에서 중복 0 · 유실 0 이고, 잠금 무력화 · 배타 이동 제거 되주입이 red 다; inbox/.gitignore 가 매번 복구된다
- Completion criteria: [C3] 결정이 있는 task 의 받은편지함 건수가 1 이상이면 → done 이 거부되고(pending_plan_responses · 무변경 · rc 1) 겹친 사유의 error_code 는 plan_lint_error > pending_plan_responses > open_decisions 순이며 결정이 없는 task 는 영향이 없다; backlog-update · session-start 가 미반영 건수를, 지문을 바꾸는 쓰기가 옛 계획 응답을 warnings 에 싣는다; plan-status 가 받은편지함 건수 · 파일별 자격 · 알 수 없는 파일을 낸다; 게이트 · plan-status · 우회 검출이 보관 응답으로 계산한 상태(kept · changed · unopened · disputed)로 판정한다
- Completion criteria: [C4] seed 가 이어받는 task 의 보관 응답(<TASK-ID>-<숫자>.md)을 새 브랜치로 복사하고 받은편지함 · .rejected.md 는 옮기지 않는다; 합류 반영이 task 를 이월 · 되돌려 적을 때도 보관 응답이 함께 간다
- Completion criteria: [C5] 응답 파일이 없는 저장소에서 1단계 검사 셋이 그대로 통과하고 추적된 task 파일 전수의 게이트 판정 · state.json 이 구현 전과 같다
- Completion criteria: [C1] 되주입: common/plan_responses.py · tools/plan_import.py 와 이 task 가 backlog_update.py · plan_tasks.py · plan_status.py · 이어받기 코드에 더한 판정 분기(조건 · 비교 · 상수)를 한 군데씩 되돌린 것 중, 스펙 §6~§9 · §11 이 정한 관측값(자격 단계 · 옮김 여부 · 보관 이름 · 상태 칸 · error_code · rc · warnings 의 유무)을 바꾸는 것은 red 다 — 메시지 문구 · 스펙이 정하지 않은 세부 · 동치는 범위 밖
- Completion criteria: 정본 §11.1 에 plan-import 줄이 들어가 스냅샷 · 배포 사본 · 진입점에 반영되고 가장 큰 진입 파일이 8,192 바이트 이하다; 스킬 plan-import 와 출력 계약 family plan_import 가 등록된다; mypy 오류 0 · 전량 게이트 --branch-context=all green

## 🧭 Plan

- Claims: C1 응답은 자격 0~6 단계를 전부 통과해야만 결정 상태에 든다
- Claims: C2 반영은 순서 · 방식과 무관하게 같은 상태에 이르고 응답을 잃거나 겹쳐 놓지 않는다
- Claims: C3 미반영 응답이 남은 task 는 닫히지 않고 그 사실이 보고에 드러난다
- Claims: C4 이어받은 task 는 상태의 근거인 보관 응답과 함께 온다
- Claims: C5 응답이 없는 저장소는 1단계와 같게 동작한다
- Decisions: D1 [C4] 합류의 되돌려 적기가 브랜치에서 거둔 응답을 원본 쪽 보관에서도 거두는가? | default: carry | options: carry = 내용이 같은 원본 쪽 보관 응답을 .rejected.md 로 옮긴다; keep = 옮기지 않고 원본 쪽 보관을 그대로 둔다 | state: answered:carry
- Files that change: workflow-source/workflow_kit/common/plan_responses.py (신규 — 응답 파서 · 자격 · 받은편지함 · 보관 · 잠금 · 배타 이동)
- Files that change: workflow-source/workflow_kit/tools/plan_import.py (신규) · common/tool_dispatch.py · pyproject.toml (명령 등록)
- Files that change: workflow-source/workflow_kit/common/plan_tasks.py · tools/plan_status.py · tools/backlog_update.py · tools/session_start.py (보관 응답으로 계산 · 받은편지함 게이트 · 경고)
- Files that change: workflow-source/workflow_kit/common/schemas/plan.py · output_contracts.py · workflow-source/schemas/*.json (plan_import family · plan_status 확장, 재생성)
- Files that change: workflow-source/workflow_kit/tools/seed_workspace_memory.py · common/branch_join.py · common/branch_inheritance.py (보관 응답 이어받기)
- Files that change: workflow-source/core/global_workflow_standard.md + 스냅샷 · ai-workflow/core 사본 · CLAUDE.md · AGENTS.md · plugin/** · harvest_entry_sections.py · _entry_known_sections.py (정본 §11.1 전파)
- Files that change: workflow-source/workflow_kit/plugin_payload.py · plugin/** (스킬 plan-import) · docs/CODE_INDEX.md · docs/INSTALLATION_AND_USAGE.md (명령 · 검사 수)
- Files that change: workflow-source/tests/check_plan_import.py (신규) · check_plan_gate.py · check_plan_claims.py · check_plan_decision_state.py (받은편지함 행 · 파서 단일성 · 파일 수준 순서 무관)
- Files that change: workflow-source/core/claim_plan_spec.md · ai-workflow/wiki/decisions/adr-031-claim-plan.md (Implementation Notes) · ai-workflow/memory/active/** (task · handoff · state · roadmap)
- Order of work: [C1] plan_responses.py — 응답 파서 · 자격 0~6 · 디렉터리 · 번호 · 배타 이동 · 잠금 → plan_tasks.archived_responses 를 채운다
- Order of work: [C2] plan-import (dry-run · --apply · --response · --discard) · 출력 계약 → check_plan_import (자격 표 · 순서 무관 · 경합)
- Order of work: [C3] backlog-update 게이트 · 경고 · session-start · plan-status → check_plan_gate 의 받은편지함 행
- Order of work: [C4] seed · 합류의 보관 응답 복사 → check_plan_import 의 이어받기 case
- Order of work: [C5] 정본 §11.1 · 스킬 · 문서 → 되주입 → mypy → --changed → verifier → 전량 게이트
- Plan risks: [C2] 쓰기끼리 · 이동끼리 따로 잰 경합은 쓰기 × 이동을 못 본다 (requirements 실측) — 쓰는 쪽 여럿 × 옮기는 쪽 둘을 한 case 에서 잰다
- Plan risks: [C1] 자격을 backlog-update 의 초안 계획(쓰기 뒤의 지문)으로 봐야 한다 — 쓰기 전 지문으로 보면 지문을 바꾸는 쓰기가 옛 응답을 채택한 채 닫는다
- Plan risks: [C5] 게이트가 받은편지함 디렉터리를 만들면 응답이 없는 저장소의 트리가 바뀐다 — 읽는 길은 디렉터리를 만들지 않는다
- Plan risks: 정본을 고치면 생성물 여럿이 함께 움직이고 진입점 절 해시는 커밋 뒤에야 재채취된다 (1단계와 같은 두 커밋 순서)
- Proof: check_plan_import 신규 + 1단계 검사 셋 확장, 판정 분기 되주입, mypy, --changed, verifier, 전량 게이트

## 🛠️ Implementation / Content

- Progress: 2026-11-13 verifier 4차: FAIL 2 — 받은편지함이 다른 파일시스템으로 가는 링크면 --apply 가 EXDEV 로 죽음(dry-run 은 이동 예고) / 받은편지함 쪽 비파일 항목 case 없음(되주입 4건 green). 수리: 배치 판정(같은 디렉터리 · 다른 fs → plan_responses_layout, dry-run 도) · EXDEV 를 오류로 · 링크 · 비파일 항목은 응답이 아니고 알 수 없는 것으로 보고 + case 6c. 되주입 13건 중 12 red · 1 동치. verifier 5차 대기
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
