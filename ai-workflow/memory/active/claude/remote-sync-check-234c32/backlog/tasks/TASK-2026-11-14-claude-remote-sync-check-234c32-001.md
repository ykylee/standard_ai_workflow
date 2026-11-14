---
id: TASK-2026-11-14-claude-remote-sync-check-234c32-001
status: done
created_at: 2026-11-14
source_anchor: generic-task-2026-11-14-claude-remote-sync-check-234c32-001
source_path: backlog/2026-11-14.md
kind: generic
wbs: M-029/WBS-29.1
---

# TASK-2026-11-14-claude-remote-sync-check-234c32-001 — M-029 ① 이월 정리 — inbox_census 단일 출처 · plan-import 건수 두 필드 · 받은편지함 우회 검출 · 정리 일곱

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-14
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: ADR-032 결정 16 · 17 · 18 · 24 · 25 를 서버 없이 구현한다. 받은편지함 건수를 plan_responses.inbox_census 하나로 접고 호출자를 전환, plan-import 출력의 pending_responses(지금) · remaining_after(반영 뒤), refresh-state · session-start 의 done 인데 미반영 응답 행, plan-status 의 배치 · 보관 비정상 항목 warnings, 게이트의 배치 warnings(막지 않음), 1 · 2단계 검증이 넘긴 정리 일곱, claim_plan_spec §4 · §10 문면.
- Completion criteria: [C1] plan_responses.inbox_census(branch_dir) 가 task 별 미반영 건수 · 알 수 없는 항목 · 배치 문제를 한 번에 돌려주고, backlog-update 게이트 · session-start · refresh-state · plan-status · plan-import 가 받은편지함 건수 · 알 수 없는 항목을 이것으로만 얻는다(옛 조합 함수를 직접 부르는 호출자 0 — grep 근거); census 를 바꾸는 되주입이 각 소비자의 case 에서 red
- Completion criteria: [C2] plan-import 출력의 pending_responses 는 실행 시점 받은편지함 건수(plan-status 와 같은 값), remaining_after 는 반영 뒤 남을 건수 — dry-run 과 --apply 에서 같고 schema · output contract 에 있다
- Completion criteria: [C3] refresh-state · session-start 가 done 인데 받은편지함에 미반영 응답이 있는 task 를 'done 인데 계획 응답 n건 미반영: <TASK-ID>' 로 싣고(막지 않음), plan-status 가 layout_problem 과 보관의 링크 · 비파일 항목을 warnings 에 싣는다
- Completion criteria: [C4] backlog-update → done 은 배치 문제를 warnings 에만 싣고 그것으로 막지 않으며, 미반영 건수가 있으면 배치와 무관하게 막는다(case 로 잼)
- Completion criteria: [C5] ADR-032 결정 24 의 일곱(_existing_task_lines 예외 경로 case · answered: 빈 값 계수 case · case 15 workspace 분리 · --progress-note 반복 · 배치가 0 단계보다 먼저인 순서 case · EXDEV/LayoutError 되주입이 FAIL 줄로 red · check_plan_import.py 의 type: ignore 제거)이 각각 처리되고 근거가 있다
- Completion criteria: [C6] claim_plan_spec.md §4 · §10 과 plan_workbench_spec §8 이 위 동작을 문면으로 적고, --changed · check_self_application 이 green 이다

## 🧭 Plan

- Claims: C1 받은편지함 건수의 정본이 inbox_census 하나다
- Claims: C2 plan-import 의 두 건수 필드가 plan-status 와 같은 뜻이다
- Claims: C3 게이트를 거치지 않은 done 의 미반영 응답과 배치 비정상이 보고에 드러난다
- Claims: C4 게이트는 배치 문제로 막지 않고 미반영 건수로만 막는다
- Claims: C5 1 · 2단계 검증이 넘긴 정리 일곱이 닫힌다
- Claims: C6 계약 문서가 바뀐 동작을 문면으로 적는다
- Files that change: workflow-source/workflow_kit/common/plan_responses.py · plan_tasks.py
- Files that change: workflow-source/workflow_kit/tools/plan_import.py · plan_status.py · backlog_update.py · session_start.py · refresh_state.py
- Files that change: workflow-source/workflow_kit/common/schemas/plan.py · output_contracts · schemas/*.json
- Files that change: workflow-source/tests/check_plan_import.py · check_plan_gate.py · check_plan_claims.py
- Files that change: workflow-source/core/claim_plan_spec.md · plan_workbench_spec.md (+ ai-workflow/core 사본)
- Order of work: [C1] inbox_census 추가 → 호출자 전환 → 옛 조합 함수 정리
- Order of work: [C2][C3][C4] 출력 필드 · 우회 검출 행 · warnings
- Order of work: [C5] 정리 일곱 — case 와 수정
- Order of work: [C6] 스펙 문면 → 되주입 → verifier
- Plan risks: [C1] 호출자가 census 의 일부만 쓰면 옛 함수를 남겨 두고 다시 조합하게 된다 — 옛 함수는 census 내부로 접고 grep 으로 확인한다
- Plan risks: [C3] refresh-state 의 warnings 는 state.json 생성물에 들어갈 수 있다 — 생성물 바이트가 바뀌는지 확인한다
- Proof: case 추가 · census 되주입 red · grep 근거 · verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-14 구현 완료: inbox_census(옛 조합 함수 셋 접음) · plan-import pending_responses/remaining_after · 우회 검출 받은편지함 행 · plan-status 배치/보관 비파일 warnings · 게이트 배치 warnings(거부 응답 포함 — case 21 이 찾은 결함 수정) · 정리 일곱(case 22 · 6c 순서 · case 15 분리 · 예외→FAIL 줄 · type: ignore 0). 검사: gate 22/22 · import 14/14 · claims 14/14 · --changed 298/298 · smoke 8/8. 되주입 27/27 red (C04 · G04 는 첫 회 green → case 보강; G04 는 CLI rc 가 무관한 읽기에도 가려져 함수 직접 단언)
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result: verifier 2회 — 1차 C1 FAIL(다른 파일시스템 배치 경고 되주입 green) · C6 UNMEASURED → case 6c 소비자 단언 · case 7 건수 단언 · _load_task census 경유로 보강, 2차 [C1]~[C6] PASS (verifier 되주입 24건 red, 작성자 27+5건 red). gate 22/22 · import 14/14 · claims 14/14 · --changed 298/298 · smoke 8/8
- Verification: verifier 2회 — 1차 C1 FAIL(다른 파일시스템 배치 경고 되주입 green) · C6 UNMEASURED → case 6c 소비자 단언 · case 7 건수 단언 · _load_task census 경유로 보강, 2차 [C1]~[C6] PASS (verifier 되주입 24건 red, 작성자 27+5건 red). gate 22/22 · import 14/14 · claims 14/14 · --changed 298/298 · smoke 8/8
- Follow-up:
