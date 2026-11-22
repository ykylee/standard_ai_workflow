---
id: M-041
title: 허브 오케스트레이션 — 중앙 허브 · PC 중계 허브 · 하네스 · 세션 4계층, 메인 오케스트레이터 세션의 작업 분배 (concept)
sdlc_phase: concept
status: in_progress
order: 41
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - docs/planning/hub-orchestration-review-2026-11.md
goals: [G1, G5]
---

# M-041 — 허브 오케스트레이션 (concept)

소유자 제기(2026-11-22): 중앙 허브 → 각 PC 중계 허브 → 각 하네스 → 세션 으로 관리되는 오케스트레이션 시스템으로
발전시킨다. 메인 오케스트레이터로 선언된 세션이 다른 세션을 관리하고 작업을 분배한다. PC 중계 허브는 로컬에 띄워
웹으로 접근하거나, 스탠드얼론 앱 · VS Code 확장으로 제공할 수 있다.

**부딪치는 기존 결정** — concept 이 소유자 결정으로 다시 열어야 한다:

- 2.0 D5 · 요구 R15.3: A2A(환경끼리 메시지) · 유휴 점검은 **첫 판에서 뺀다**, 허브는 하네스에 메시지를 보내지 않는다
- `multi_workspace_orchestration.md` §0.6: 중앙이 하네스에 메시지를 보내지 않는다 — 지시는 워크스페이스에 놓인다
- 2.0 H4 · R0.4: 작업 환경은 kit 을 깔지 않는다 (중계 허브가 PC 에 무엇을 까는가)
- PURPOSE 제외 영역: non-Python runtime (VS Code 확장 · 스탠드얼론 앱)

## WBS

- **WBS-41.1** concept 검토 — 4계층 모델 · 오케스트레이터 권한 · 세션 전달 방식 · 중계 허브 · 화면 3안 · 부딪치는 결정 · 열린 결정 · 단계 — 산출물: `docs/planning/hub-orchestration-review-2026-11.md`
