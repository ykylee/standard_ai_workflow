---
id: TASK-2026-11-13-claude-remote-sync-check-234c32-003
status: in_progress
created_at: 2026-11-13
source_anchor: generic-task-2026-11-13-claude-remote-sync-check-234c32-003
source_path: backlog/2026-11-13.md
kind: generic
wbs: M-028/WBS-28.1
---

# TASK-2026-11-13-claude-remote-sync-check-234c32-003 — 주장 트리 계획 구현 1단계 — 라벨 · 파서 · 린트 · 게이트 · --decision-state · plan-status · open_decisions · 정본 §1

## 📝 Description

- Status: in_progress
- Priority: high
- Request date: 2026-11-13
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `workflow-source/core/claim_plan_spec.md`
  - `workflow-source/core/global_workflow_standard.md`
  - `workflow-source/core/backlog_update_skill_spec.md`

- Description: ADR-031 결정 26 의 1단계를 구현한다 (계약은 workflow-source/core/claim_plan_spec.md §1~§5 · §8 · §10 · §11 일부 · §12). task Plan 에 Claims · Decisions 를 싣고 린트하고, 열린 결정이 남으면 done 을 거부하고, 대화의 답을 --decision-state 로 기록하고, plan-status 로 주장별 묶음을 낸다. 응답 파일 · 받은편지함 · plan-import 는 2단계(WBS-28.2)
- Completion criteria: [C1] 두 라벨이 없는 기존 task 파일 전수에서 알려진 라벨의 읽은 값과 생성기의 state.json 이 구현 전과 같다 (check_plan_claims 의 호환 case)
- Completion criteria: [C2] 린트 L1~L10 이 스펙 §3 대로 판정한다 — 오류 규칙은 backlog-update --apply 가 파일을 쓰지 않고(rc 1 · plan_lint_error), 경고 규칙은 쓰고 warnings 에 규칙 번호를 싣는다; 각 규칙의 판정을 한 군데씩 되돌리면 그 case 가 red 다
- Completion criteria: [C3] 열린 결정이 남은 task 의 → done 이 거부되고(파일 무변경 · rc 1 · open_decisions) → in_progress 는 경고하며 통과하고, --decision-state D=answered:<v> 뒤에는 통과한다; 손으로 고친 kept 칸은 계산값(proposed)으로 판정된다; 오류 규칙을 어긴 task 의 → done 은 거부된다
- Completion criteria: [C4] 결정 상태 계산(스펙 §8)이 상태 기계 전수 탐색에서 끝 상태 1종 · 멱등 · done 판정 순서 무관 · 다툼에 든 입장이 채택된 채 닫히는 경로 0 이고, 되주입(부분 채택 · 칸을 입력으로 읽기)이 red 다 (check_plan_decision_state)
- Completion criteria: [C5] plan-status 가 주장 × 인용 기준 × 계산한 결정 상태를 json · md 로 내고 아무것도 쓰지 않는다; state.json 의 open_decisions 는 열린 결정이 있을 때만 나오고 없으면 기존과 바이트가 같다; done 인데 열린 결정이 있는 task 를 refresh-state · session-start 가 warning 으로 싣는다
- Completion criteria: 정본 §1 개정이 스냅샷 · 배포 사본 · 진입점에 반영되고 가장 큰 진입 파일이 8,192 바이트 이하다; 전량 게이트 --branch-context=all 이 green 이고 mypy 오류가 0 이다

## 🧭 Plan

- Files that change: workflow-source/workflow_kit/common/plan_claims.py
- Files that change: workflow-source/workflow_kit/common/project_docs.py
- Files that change: workflow-source/workflow_kit/common/workflow_writes.py
- Files that change: workflow-source/workflow_kit/tools/backlog_update.py
- Files that change: workflow-source/workflow_kit/tools/plan_status.py
- Files that change: workflow-source/workflow_kit/common/tool_dispatch.py · pyproject.toml (명령 등록)
- Files that change: workflow-source/workflow_kit/common/output_contracts.py · schemas (plan_status family · BacklogUpdateOutput)
- Files that change: workflow-source/workflow_kit/common/state/builder.py · tools/refresh_state.py · tools/session_start.py (open_decisions · 우회 검출)
- Files that change: workflow-source/core/global_workflow_standard.md + 스냅샷 · ai-workflow/core 사본 · CLAUDE.md · AGENTS.md · plugin (정본 §1 전파)
- Files that change: workflow-source/tests/check_plan_claims.py · check_plan_decision_state.py · check_plan_gate.py (신규) + 기존 검사 갱신
- Files that change: ai-workflow/memory/active/** (task · backlog · handoff · state.json · roadmap)
- Files that change: workflow-source/workflow_kit/common/plan_tasks.py (신규 — task 파일을 읽는 얇은 I/O 층, ADR-031 Implementation Notes)
- Files that change: workflow-source/workflow_kit/common/schemas/plan.py · workflow-source/schemas/*.json (재생성)
- Files that change: workflow-source/core/claim_plan_spec.md (상태 줄) · ai-workflow/wiki/decisions/adr-031-claim-plan.md (Implementation Notes)
- Files that change: workflow-source/workflow_kit/plugin_payload.py · plugin/** (backlog-update 스킬 본문) · docs/CODE_INDEX.md · docs/INSTALLATION_AND_USAGE.md (검사 수 312)
- Files that change: workflow-source/scripts/harvest_entry_sections.py · workflow_kit/common/_entry_known_sections.py (진입점 템플릿 변경 → 재채취)
- Files that change: workflow-source/core/backlog_update_skill_spec.md + ai-workflow/core 사본 (§13 포인터) · .claude/agents/verifier.md (plan-status 한 줄)
- Order of work: [C2][C4] plan_claims.py (파서 · 린트 · 지문 · 상태 계산, 순수 함수) → check_plan_claims · check_plan_decision_state
- Order of work: [C1][C2][C3] 라벨 · PLAN_FIELD_KEYS · _ensure_plan_section · backlog-update 인자 · 린트 · 게이트 · 칸 고쳐 쓰기 → check_plan_gate
- Order of work: [C5] plan-status · 출력 계약 · open_decisions · 우회 검출 warning
- Order of work: 정본 §1 개정과 전파 → 진입점 크기 → mypy → --changed → verifier → 전량 게이트
- Plan risks: [C1] 라벨 표에 key 를 더하면 그 표를 도는 기존 코드(본문 조립 · registry 검사)가 새 key 를 빈 줄로 내거나 red 가 될 수 있다 — 기존 task 파일과 새 task 렌더가 바이트로 안 바뀌는지 먼저 잰다
- Plan risks: [C3] 게이트를 쓰기 블록 뒤에 두면 거부인데 파일이 바뀐다 — WBS 게이트와 같은 자리(쓰기 앞)에 둔다
- Plan risks: 정본을 고치면 생성물 여럿(스냅샷 · 사본 · 진입점 · 플러그인 · 예제)이 함께 움직인다 — 검사가 알려 주는 대로 재생성하고 손으로 고치지 않는다
- Plan risks: 2단계 전이라 응답 파일이 없다 — 상태 계산은 응답 목록을 인자로 받고 1단계는 빈 목록을 넘긴다 (받은편지함 게이트는 2단계)
- Proof: 신규 검사 셋의 case 와 되주입, 기존 검사 --changed, mypy, 전량 게이트, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-13 verifier 1차: [C2] FAIL(린트 되주입 8건 green) + 스펙과 다른 동작 9건 → 코드 수리(명시 사유 · answered 옮겨 적기 · 겹친 사유 · 경고 되풀이 없음 · --check 우회 · verifier 한 줄) + 검사 보강(11 + 6 + 18 case). 되주입 56건 전부 red, mypy 0. 재검증 대기
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
