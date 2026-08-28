---
id: M-008
title: 검사 입력 표면 선언 + 계층별 회귀 실행 계약
sdlc_phase: concept
status: planned
order: 8
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/test-impact-tiering-review-2026-08.md
---

# M-008 — 검사 입력 표면 선언 + 계층별 회귀 실행 계약

테스트가 늘수록 회귀 검사 시간이 병목이 된다는 관찰(소유자 제기, 2026-08-28)
에서 출발한 새 기능 축. "수정 영향이 미치는 부분만 부분적/점진적으로" 를
**게이트까지** 확장하려면 휴리스틱이 아니라 **선언 기반 영향 매핑**이 선행돼야
한다 — 각 검사가 자기 입력 표면을 선언하고(기존 `REQUIRES_QUIET_REPO` /
`CHECK_TIMEOUT_S` 선언 패턴의 확장), runner 가 diff ∩ 선언 교집합으로 선택한다.

**전제 이력** (concept 검토가 반드시 대면할 것):

- 조건부 1축 생략은 검토 후 기각됐다 (TASK-2026-08-14-main-004 — '민감 경로'
  휴리스틱 판정이 건전하게 성립하지 않았고, 절감 ~106s/push 대비 오판 1회
  실측 비용 10일).
- 53차 규칙 "전량 게이트는 필터로 대체되지 않는다" — red 2건이 관련 검사
  필터를 전부 통과하고 게이트에서만 잡혔다.
- 벽시계를 정하는 것은 개수가 아니라 무거운 8개다 (2026-08-14 실측) —
  선택 실행의 이득 상한을 실측으로 재고 나서 투자한다.

SDLC 온보딩 기본 순서(concept → requirements → design → implementation)를
따른다. concept 산출물이 채워지기 전에는 다음 단계 leaf 를 열지 않는다.

## WBS

- **WBS-8.1** concept 검토 — 선언 기반 영향 매핑의 건전성 조건, 기각 이력
  (main-004 · 53차 규칙) 대비 차별점, 이득 상한 실측 계획 — 산출물:
  `docs/planning/test-impact-tiering-review-2026-08.md`
