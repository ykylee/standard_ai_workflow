---
id: M-021
title: compact 중계 — implementation (명령 · hook · 스킬 · 검사)
sdlc_phase: implementation
status: done
order: 21
parallel_allowed:
  - M-007
deliverables:
  - workflow-source/workflow_kit/common/compact_relay.py
  - workflow-source/workflow_kit/tools/compact_checkpoint.py
  - workflow-source/tests/check_compact_relay.py
goals: [G1, G2]
---

# M-021 — compact 중계 — implementation

design ([`M-020`](./M-020-compact-relay-design.md) → ADR-030 accepted,
[`compact_relay_spec.md`](../../../../workflow-source/core/compact_relay_spec.md)) 를 구현한다.

**종결 (2026-09-30)**: 구현 커밋 `5a3c9db4` push 게이트 통과. check_compact_relay 12 cases (되주입 13건 red),
`claude -p` 압축 왕복 E2E 2회. 실측이 설계를 고친 곳: Claude Code 는 `SessionStart(compact)` 재주입을
`PostCompact` 보다 먼저 돌린다 → 누락 목록은 post 출력이 말한다 (스펙 §4). 미실측: 자동 압축 경로 ·
Codex 플러그인 hook · Grok 실동작.

## WBS

- **WBS-21.1** 구현 — `compact_relay` 모듈 + `wk compact-checkpoint` + 예산 레코드 + §11.1 한 줄 +
  플러그인 스킬 `compact-relay` · hook 3종 + `check_compact_relay` (TASK-2026-09-30-main-006)
