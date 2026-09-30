---
id: M-019
title: compact 중계 — requirements (안 B: 스킬 + hook 3종 + 요약 대조)
sdlc_phase: requirements
status: done
order: 19
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/compact-relay-requirements-2026-09.md
goals: [G1, G2]
---

# M-019 — compact 중계 — requirements

concept 검토([`M-018`](./M-018-compact-relay.md) →
[`compact-relay-review-2026-09.md`](../../../../docs/planning/compact-relay-review-2026-09.md))
의 소유자 결정 **안 B** (2026-09-30) 를 받는 requirements 단계:

- **명령 계약**: 정본 §11.1 신설 명령과 모드(스킬 기록 · hook 기록 · 요약 대조 · 재주입 · 정리).
- **checkpoint 형식**: 워크트리 로컬 `active/<branch>/.compact/`, gitignore, 기계 층 + 판단 층, 재주입 우선순위.
- **재주입 예산**: 4KB — Claude Code hook 출력 인라인 상한(≈10,000자, 실측)과의 거리.
- **'잃지 않음' 판정**: `PostCompact` 요약과 식별자형 항목 대조.
- **불변 조건**: handoff · state.json 무쓰기 · 커밋 안 함 · hook 이 세션을 막지 않음.

**종결 (2026-09-30)**: 소유자 sign-off — Q1~Q3 권고안대로 (산출물 §11). design 단계는
[`M-020`](./M-020-compact-relay-design.md) 으로 이어진다.

## WBS

- **WBS-19.1** requirements 확정 — 명령 계약 · checkpoint 형식 · 재주입 예산 · 누락 판정 ·
  하네스 선언 · 검증 · design 진입 조건 — 산출물: `docs/planning/compact-relay-requirements-2026-09.md`
  (TASK-2026-09-30-main-004)
