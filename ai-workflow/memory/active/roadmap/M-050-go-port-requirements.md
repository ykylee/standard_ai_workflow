---
id: M-050
title: 2.x 전면 Go 전환 — requirements
sdlc_phase: requirements
status: done
order: 50
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - docs/planning/go-port-requirements-2026-11.md
goals: [G1, G3, G5]
---

# M-050 — 2.x 전면 Go 전환 requirements

concept 정본: [`runtime-port-review-2026-11.md`](../../../../docs/planning/runtime-port-review-2026-11.md) §11 (소유자 2026-11-22 — R1 = D 전면 Go).
허브 · 공유 판정(약 19k 줄) · PC 중계를 Go 로. 1.x 는 `release/1.x` 에서 Python 그대로 (2028-07-20 까지).

**종결 (2026-11-22)**: `go-port-requirements-2026-11.md` — 요구 R25~R35, Q1~Q6 소유자 결정 권고안 전부 (3.0.0 · S4 까지 wheel 병행 · hub_client Python 유지 · modernc · `hub-go/` · 실데이터 corpus). ADR-035 Proposed. main-024 · 025 · 026.

## WBS

- **WBS-50.1** 요구 — 계약 불변(MCP 도구 · HTTP 경로 · DB 판 · 1.x 생성물 형식 — 기존 DB 를 Go 허브가 그대로 연다) · 판정 '같은 답' 기준과 차분 검사 · 적합성 검사(허브 검사 재사용) — 산출물: `docs/planning/go-port-requirements-2026-11.md`
- **WBS-50.2** 이행 단계 · 배포(OS별 바이너리 · Windows 서명 실측 R4) · 게이트에 Go 검사 넣기 · Python 판 deprecation — 산출물: `docs/planning/go-port-requirements-2026-11.md`
- **WBS-50.3** ADR-035 초안 — PURPOSE 제외 영역 예외를 2.x 런타임(Go)으로 (R3) · hub_spec R0.3 개정 — 산출물: `ai-workflow/wiki/decisions/`
