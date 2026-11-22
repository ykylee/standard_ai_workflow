---
id: M-042
title: 허브 오케스트레이션 — requirements (실측 S · 요구 · ADR 초안)
sdlc_phase: requirements
status: done
order: 42
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - docs/planning/hub-orchestration-requirements-2026-11.md
goals: [G1, G5]
---

# M-042 — 허브 오케스트레이션 — requirements

concept 정본은 [`M-041`](./M-041-hub-orchestration.md) · `docs/planning/hub-orchestration-review-2026-11.md` (소유자 2026-11-22 O1~O10 권고안).
요구의 전제는 하네스가 실제로 무엇을 허락하는가다 — 실측 S 를 먼저 하고, 재지 못한 칸은 '지원'으로 세지 않는다.

**종결 (2026-11-22)**: 실측 S 1차 · 2차 (hook · 신뢰 없는 간접 수단 — 소유자 지시) · 요구 R17~R24 · 소유자 Q1~Q4 권고안 · ADR-034 Proposed. 다음은 design (M-043, 미개설).

## WBS

- **WBS-42.1** 실측 S — Claude Code · Codex (Linux): T1 턴 경계 hook 주입 · T2 비대화형 · 이어 가기 · 상태 읽기 — 산출물: `docs/planning/hub-orchestration-requirements-2026-11.md` 실측 절
- **WBS-42.2** 요구 R · 검증 방법 · 추적표 (concept → 요구) — 산출물: `docs/planning/hub-orchestration-requirements-2026-11.md`
- **WBS-42.3** ADR 초안 (Proposed — design 뒤 Accepted) — 산출물: `ai-workflow/wiki/decisions/adr-034-hub-orchestration.md`
