---
id: M-013
title: 세션 시작 컨텍스트 예산 — 필독 문서 부피를 선언하고 잰다
sdlc_phase: concept
status: planned
order: 13
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/session-context-budget-review-2026-09.md
goals: [G2]
---

# M-013 — 세션 시작 컨텍스트 예산

87차 워크플로우 평가([`workflow-assessment-2026-09.md`](../../../../docs/planning/workflow-assessment-2026-09.md) §3.1)에서
도출된 새 기능 축. 세션을 열 때마다 반드시 읽는 문서가 **약 190KB** 다
(2026-09-23 실측 — `session_handoff.md` 108KB 중 §5 57KB·748줄, §1 기준선
한 줄 최대 18KB / `state.json` 65KB 중 `memory_entries` 35KB / `CLAUDE.md` 18KB).
`CLAUDE.md` 의 "handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남긴다"
원칙에 대해 **선언도 측정도 없다** — 기준선 상한은 줄 수로만 걸려 있어 한 줄이
계속 커진다.

**전제 이력** (concept 검토가 대면할 것):

- handoff §1 은 `wk rollover-baselines` 가 줄 수 상한으로 이관한다 — 이관은 삭제가
  아니다(그 산문은 다른 곳에 없다). 예산은 이관 규율을 깨지 않아야 한다.
- `state.json` 은 생성물이다 — 부피를 줄이려면 생성기 입력이나 스키마를 바꾼다.
- 줄이는 것이 목적이 아니라 **다음 세션이 필요한 것을 잃지 않는 것**이 목적이다.
  무엇을 잃었는지 재는 수단 없이 줄이면 '고친 것 없이 숫자만 좋아진다'.

SDLC 온보딩 기본 순서(concept → requirements → design → implementation)를 따른다.
concept 산출물이 채워지기 전에는 다음 단계 leaf 를 열지 않는다.

## WBS

- **WBS-13.1** concept 검토 — 필독 문서별 부피·성장률 실측, 섹션별 '다음 세션이
  실제로 쓰는가' 판정 방법, 예산 단위(바이트/토큰) · 이관 대상 · 소유자 선택지 —
  산출물: `docs/planning/session-context-budget-review-2026-09.md`
