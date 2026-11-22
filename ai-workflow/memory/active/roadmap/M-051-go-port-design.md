---
id: M-051
title: 2.x 전면 Go 전환 — design
sdlc_phase: design
status: done
order: 51
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/core/hub_go_spec.md
goals: [G1, G3, G5]
---

# M-051 — 2.x 전면 Go 전환 design

요구 정본: [`go-port-requirements-2026-11.md`](../../../../docs/planning/go-port-requirements-2026-11.md) (R25~R35, Q1~Q6 결정). ADR-035 Proposed.

**종결 (2026-11-22)**: `hub_go_spec.md` — DG1~DG5 소유자 확정(권고안 전부), ADR-035 Accepted, PURPOSE 예외. main-027~030. 다음 M-052 (S1 중계).

## WBS

- **WBS-51.1** 구조 — `hub-go/` 패키지 배치 · Python 모듈 대응 · 순수 판정 입구(DB 와 분리) · 자산 내장의 단일 출처 — 산출물: `workflow-source/core/hub_go_spec.md`
- **WBS-51.2** 검증 — 판정 CLI 프로토콜 · 차분 검사 · corpus 생성 · 적합성 검사 전환 스위치 · 게이트 감싸기 — 산출물: `workflow-source/core/hub_go_spec.md`
- **WBS-51.3** S1 중계 · 빌드 · 배포 — 중계 Go 판 범위 · OS별 빌드 · 체크섬 · 판 머리 — 산출물: `workflow-source/core/hub_go_spec.md`
- **WBS-51.4** design 결정 DG 권고안 · ADR-035 Accepted — 산출물: `ai-workflow/wiki/decisions/adr-035-go-runtime.md`
