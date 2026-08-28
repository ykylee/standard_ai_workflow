---
id: M-011
title: 계층별 회귀 실행 계약 — implementation (meta-watch 러너 통합)
sdlc_phase: implementation
status: done
order: 11
parallel_allowed:
  - M-007
deliverables:
  - workflow-source/workflow_kit/common/meta_watch.py
  - workflow-source/tests/check_meta_watch.py
---

# M-011 — 계층별 회귀 실행 계약 — implementation

design ([`M-010`](./M-010-test-impact-design.md) → ADR-028 + spec §6) 을 받는
구현 단계. spec §6 이 임시 정본으로 선언한 범위:

- 러너 채취 주입·수집·판정 (`meta_watch_verdict`, `--no-meta-watch`)
- `WATCHES_ALL_REASON` 어휘 + 미분류 카운트 (분류 현황 출력)
- 좁은 선언 교정 (ADR-028 실증 사례 포함 — discovery 실측으로 확장)
- 되주입 실증 + 검사 신설 (`check_meta_watch`)

후속 M-012 [release] 는 발행 + R4.2 조건 충족 후 CLAUDE.md 커밋 전 단계
전환 — 구현이 게이트 green 으로 닫힌 뒤 연다.

**종결 (2026-08-28)**: 구현·선언 교정 7건·되주입 실증 완료 — 전량 2축 게이트
green (meta 판정 포함, 좁은 선언 0, 벽시계 118~123s 로 강등 신호 없음).
잔여는 M-012 [release]: 발행 + R4.2 조건 충족 후 CLAUDE.md 커밋 전 단계 전환.

## WBS

- **WBS-11.1** meta-watch 구현·선언 교정·되주입 실증 — 산출물: 정본 모듈 +
  러너 통합 + `check_meta_watch` + 좁은 선언 0 인 게이트 green
