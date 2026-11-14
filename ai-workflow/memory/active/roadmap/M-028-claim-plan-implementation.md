---
id: M-028
title: 주장 트리 계획 — implementation (라벨 · 린트 · 게이트 · plan-status · plan-import · 검사)
sdlc_phase: implementation
status: in_progress
order: 28
parallel_allowed:
  - M-007
  - M-027
deliverables:
  - workflow-source/workflow_kit/common/plan_claims.py
  - workflow-source/workflow_kit/common/plan_responses.py
  - workflow-source/workflow_kit/tools/plan_status.py
  - workflow-source/workflow_kit/tools/plan_import.py
goals: [G2, G5]
---

# M-028 — 주장 트리 계획 — implementation

design 승인 ([`M-026`](./M-026-claim-plan-design.md) → ADR-031 accepted 2026-11-13, 계약은
`workflow-source/core/claim_plan_spec.md`) 을 받는 구현 단계. ADR-031 결정 26 대로 **두 단계**로 낸다 — 워크벤치(M-027)를 기다리지 않는다.

- **불변**: 스펙 §1. 리더와 라이터는 같은 릴리스다.
- **design 검증(5차)이 구현으로 넘긴 것**: ①잠금과 0 단계의 판정 순서(0 단계를 먼저 — 잠금 없이 판정할 수 있다) ②dry-run 의 0 단계 출력
  ③오류 상태 파일에서 칸 불일치 경고를 낼지 ④"이번 호출이 들인 오류" 와 "이미 있던 오류" 의 구분, L9 를 `--replace-field` 로 고치는 길
  ⑤`check_plan_import` 의 잠금 무력화 되주입은 옮기는 쪽이 죽어도 멈추지 않게(시간 제한) ⑥오류로 끝난 파일의 `open_decisions`(칸 기준)는 순서 의존.
- **Windows(NTFS)**: `os.link` 공개 · 배타 이동 · 잠금은 미실측 — 구현 뒤 Windows 호스트에서 잰다.

## WBS

- **WBS-28.1** 1 단계 — 라벨 · `PLAN_FIELD_KEYS` · 파서 · 린트 L1~L10 · 게이트 · `--decision-state` · `plan-status` · `open_decisions` · 정본 §1 개정 ·
  검사 `check_plan_claims` · `check_plan_decision_state` · `check_plan_gate` — 이것만으로 안 A 가 완결된다
- **WBS-28.2** 2 단계 — 응답 형식 · 받은편지함(자기 무시 · 잠금) · `plan-import` · 이어받기 · 정본 §11.1 · 스킬 `plan-import` · verifier 한 줄 ·
  검사 `check_plan_import`
- **WBS-28.3** Windows(NTFS) 실측 — `os.link` 공개 · 배타 이동 · 잠금 (`check_plan_import` 를 Windows 호스트에서), 결과를 ADR-031 Implementation Notes 에.
  같은 세션에서 M-029 워크벤치의 포트 bind · 토큰 파일 모드 · 콘솔 인코딩 · `check_workbench_write` 의 inotify 층(Windows 는 미측정 출력)도 잰다
