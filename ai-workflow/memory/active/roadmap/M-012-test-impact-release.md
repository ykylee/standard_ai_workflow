---
id: M-012
title: 계층별 회귀 실행 계약 — release (v1.7.0 발행 + CLAUDE.md 전환)
sdlc_phase: release
status: in_progress
order: 12
parallel_allowed:
  - M-007
deliverables:
  - workflow-source/releases/Beta-v1.7.0.md
---

# M-012 — 계층별 회귀 실행 계약 — release

implementation ([`M-011`](./M-011-test-impact-implementation.md)) 이 게이트
green 으로 닫힌 뒤의 발행 단계 (spec §6):

- **v1.7.0 발행**: 등급은 RELEASE.md §1.5 파생 (breaking 0 · feat 다수 →
  minor). bump 파생물 전수 갱신 — 정답지는 직전 릴리스 준비 커밋 diff
  (60차 규칙).
- **CLAUDE.md 커밋 전 단계 전환** (requirements R4.2): 메타 검증 게이트
  편입 + 되주입 실증이 완료됐으므로 커밋 전 단계를 `--changed` 기반으로
  갱신한다. push 게이트 전량 2축은 불변 (R0).
- 이 호스트 소비 채널 재적용 + drift 0 확인 (62차 전례).

## WBS

- **WBS-12.1** v1.7.0 발행 — bump·파생물·release note·게이트·tag·GH Release·
  fresh venv smoke — 산출물: `releases/Beta-v1.7.0.md`
- **WBS-12.2** CLAUDE.md 커밋 전 단계 `--changed` 전환 (R4.2) + 이 호스트
  채널 재적용 drift 0
