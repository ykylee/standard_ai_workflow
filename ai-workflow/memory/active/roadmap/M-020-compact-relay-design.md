---
id: M-020
title: compact 중계 — design (ADR-030 + core 스펙)
sdlc_phase: design
status: done
order: 20
parallel_allowed:
  - M-007
deliverables:
  - ai-workflow/wiki/decisions/adr-030-compact-relay.md
  - workflow-source/core/compact_relay_spec.md
goals: [G1, G2]
---

# M-020 — compact 중계 — design

requirements sign-off ([`M-019`](./M-019-compact-relay-requirements.md) →
[`requirements 문서`](../../../../docs/planning/compact-relay-requirements-2026-09.md)
§11, 2026-09-30) 를 받는 design 단계. sign-off 가 고정한 범위(명령 하나 · hook 3 · 스킬 1 ·
재주입 4KB · 식별자 대조) 위에서 남은 설계 결정을 ADR 로 내린다:

- **ADR-030 결정 대상**: 모듈 배치와 CLI 등록 · 워크플로우 밖 프로젝트에서의 hook 동작 ·
  gitignore 를 누가 보장하는가 · checkpoint 파일 형식(파서가 읽는 경계) · 예산 레코드 편입 ·
  §11.1 문구와 스킬 · session-end 연결 · 검사 구성.
- **core 스펙**: 명령 · 파일 · 재주입 · 대조 · 하네스 선언의 kit 계약.
- **불변**: requirements R0.

**종결 (2026-09-30)**: 소유자 승인 — ADR-030 accepted (requirements 대비 변경 두 건 포함:
`checkpoint.json` · 스킬 `compact-relay`), core 스펙 draft. 구현은
[`M-021`](./M-021-compact-relay-implementation.md) 으로 이어진다.

## WBS

- **WBS-20.1** design 확정 — ADR-030 + `compact_relay_spec.md` — 산출물:
  `ai-workflow/wiki/decisions/adr-030-compact-relay.md`,
  `workflow-source/core/compact_relay_spec.md` (TASK-2026-09-30-main-005)
