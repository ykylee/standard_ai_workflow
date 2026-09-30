---
id: M-021
title: compact 중계 — implementation (명령 · hook · 스킬 · 검사)
sdlc_phase: implementation
status: in_progress
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

## WBS

- **WBS-21.1** 구현 — `compact_relay` 모듈 + `wk compact-checkpoint` + 예산 레코드 + §11.1 한 줄 +
  플러그인 스킬 `compact-relay` · hook 3종 + `check_compact_relay` (TASK-2026-09-30-main-006)
