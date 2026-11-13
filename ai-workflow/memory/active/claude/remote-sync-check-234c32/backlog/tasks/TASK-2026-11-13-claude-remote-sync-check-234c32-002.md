---
id: TASK-2026-11-13-claude-remote-sync-check-234c32-002
status: done
created_at: 2026-11-13
source_anchor: generic-task-2026-11-13-claude-remote-sync-check-234c32-002
source_path: backlog/2026-11-13.md
kind: generic
wbs: M-026/WBS-26.1
---

# TASK-2026-11-13-claude-remote-sync-check-234c32-002 — 주장 트리 계획 design — ADR-031 + core 스펙 (필드 · 린트 · 게이트 · 응답 형식 · plan-import · 받은편지함 계약)

## 📝 Description

- Status: done
- Priority: high
- Request date: 2026-11-13
- Owner:
- Host:
- Host IP:
- Affected documents:
  - `ai-workflow/wiki/decisions/adr-031-claim-plan.md`
  - `workflow-source/core/claim_plan_spec.md`
  - `ai-workflow/wiki/index.md`

- Description: requirements(claim-plan-requirements-2026-11.md R0~R13, 워크벤치 requirements 가 고친 R8.1 · R5.1 포함)를 받아 ADR-031 과 core 스펙을 낸다. ADR 은 모듈 배치 · 결정 줄 칸 표기 · 주장별 묶음을 내는 명령 · §11.1 문구와 스킬 수 · open_decisions 스키마 · git 무시 수단 · 잠금 · 검사 구성과 requirements 검증이 design 으로 넘긴 미정 사항을 결정한다. design 은 ADR 둘로 순차(소유자 2026-11-13) — 워크벤치 서버는 M-027
- Completion criteria: requirements R13 의 'design 전' 실측 넷(정본 §1 · §11.1 개정 뒤 진입점 블록 크기 대 8KB 예산 / 다른 하네스의 새 컨텍스트 검증 수단 / 브랜치 이어받기가 plan_responses 를 옮기는지 / 두 호스트의 보관 번호 충돌)과 common/file_lock.py 로의 import 잠금 재현이 각각 명령과 결과로 ADR 또는 스펙에 적혀 있다
- Completion criteria: M-026 의 'ADR-031 결정 대상' 과 '검증이 design 으로 넘긴 것' · 'M-025 가 넘긴 것' 의 각 항목이 ADR-031 에 식별자 붙은 결정(선택 · 기각한 대안 · 근거)으로 있다
- Completion criteria: core 스펙이 requirements R0~R11 의 모든 요구 사항을 덮는다 — 스펙에 대응 절이 없는 요구 사항이 0 이고, 스펙이 requirements 와 다르게 정한 곳은 ADR 에 'requirements 대비 변경' 으로 전부 적혀 있다
- Completion criteria: ADR · 스펙이 가리키는 기존 코드(모듈 · 함수 · 상수 · 검사 이름)가 전부 HEAD 에 실재하고, 스펙의 상태 계산 규칙(R6.3)이 문면대로 모델링했을 때 순서 무관 · 멱등 · 부분 채택 없음을 지킨다
- Completion criteria: check_docs 통과; roadmap issues 0; M-026 deliverables_missing 이 빈다; ADR 색인 · wiki index 가 새 ADR 을 싣는다

## 🧭 Plan

- Files that change: ai-workflow/wiki/decisions/adr-031-claim-plan.md
- Files that change: workflow-source/core/claim_plan_spec.md
- Files that change: ai-workflow/wiki/index.md (ADR-027~031 색인 — 026 에서 멈춰 있었다)
- Files that change: ai-workflow/memory/active/roadmap/M-026-claim-plan-design.md · M-027-plan-workbench-design.md(신규) · index.md · roadmap_state.json
- Files that change: ai-workflow/memory/active/claude/remote-sync-check-234c32/** (task · backlog · handoff · state.json)
- Files that change: ai-workflow/memory/active/roadmap/M-028-claim-plan-implementation.md (신규 — 구현 마일스톤 선언)
- Order of work: 코드 구조 조사(꽂히는 자리의 파일:줄) → design 전 실측 다섯 건
- Order of work: ADR-031 초안(결정 목록) → core 스펙 → check_docs · 색인 → verifier → 소유자 승인(accepted)
- Plan risks: requirements 를 다시 쓰지 않는다 — 스펙은 계약(무엇을)이고 ADR 은 결정(어떻게 · 왜)이다. 겹치면 갈라진다
- Plan risks: 코드를 고치지 않는다 — design 단계. 실측용 코드는 scratchpad 에만
- Proof: 실측 명령 재실행, ADR 이 가리키는 심볼 grep, 스펙 ↔ requirements 대응표 전수, 상태 계산 모델링, check_docs, verifier

## 🛠️ Implementation / Content

- Progress: 2026-11-13 종결 — ADR-031 accepted(소유자 승인, V1~V10 · 결정 24 · 25 포함) · core 스펙 draft. verifier 5회: 1~2차 기준 2 · 3(대응 · 대안 · 스펙 누락), 3차 기준 4(스펙 내부 모순), 4차 기준 3(내가 넣은 오류 중 discard 허용 — requirements 대로 되돌림), 5차 5/5 PASS. M-026 done · M-027 · M-028 planned
- Next session starting point: M-027 워크벤치 design (먼저 docker 로 nginx · Caddy + 실제 브라우저 실측) 또는 M-028 구현 1 단계 — 둘은 병행 가능. M-028 파일에 design 검증이 구현으로 넘긴 메모 6건
- Remaining risks:

## ✅ Outcome

- Result: ADR-031 (결정 29 · requirements 대비 변경 V1~V10 · 실측 M1~M5) + workflow-source/core/claim_plan_spec.md (§1~§13). 실측: 진입점 +181 바이트(6,844 / 8,192) · seed 는 plan_responses 를 옮기지 않는다 · 카운터 번호는 두 호스트에서 add/add 충돌 · kit file_lock 으로 120회 중복 0 · 유실 0. wiki 색인에 ADR-027~031
- Verification: verifier 5차(새 컨텍스트) 5/5 PASS — 스펙 문면을 상태 기계로 모델링(5,653 구성, 오류 구간 포함 최대 153만 상태): 끝 상태 1종 · 멱등 · done 판정 순서 무관 · 다툼 채택 0 · 오류로 끝난 구성의 done 통과 0, 되주입 5건 전부 red; 1차에 M1~M5 전부 재현, 3차에 결정 1~29 · requirements 단위 전수 대조(대응 없는 것 0 · V 표 밖 차이 0), --changed 133 PASS, roadmap issues []
- Follow-up:
