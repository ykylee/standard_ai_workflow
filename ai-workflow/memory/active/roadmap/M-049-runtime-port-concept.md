---
id: M-049
title: 허브 · PC 중계 런타임 전환 검토 (Go / Rust) — concept
sdlc_phase: concept
status: planned
order: 49
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - docs/planning/runtime-port-review-2026-11.md
goals: [G1, G5]
---

# M-049 — 허브 · PC 중계 런타임 전환 검토 (Go / Rust)

소유자 2026-11-22: "2.1.0 은 유지하고 다음 버전에 go 나 rust 기반으로 전환을 고려하자". 2.1.0 은 Python 그대로 발행했다.
이 마일스톤은 **결정을 위한 concept** 이다 — 구현은 결정 뒤 별도 마일스톤.

판단 쟁점 (139차 검토):
- 허브 `judge.py` 는 1.x 판정 함수를 그대로 부른다 (hub_spec §1-6, R0.7) — 이식하면 판정이 두 런타임으로 갈라진다. 1.x 는 2028-07-20 까지 유지.
- 이식량: 허브 약 7.5k 줄 + 공유 판정 · 스키마 · 진입 파일 생성 6.6k 줄 이상, 게이트 검사 350 이 Python.
- PURPOSE 제외 영역(Python 외 런타임) · hub_spec R0.3 을 바꾸는 결정 → ADR.
- 선택지: 전면 이식 / 입출력 앞단만 이식하고 판정은 Python / **PC 중계만** 단일 바이너리 (판정 로직 없음, 약 900 줄).

## WBS

- **WBS-49.1** Go · Rust 실측 비교 — 공식 MCP SDK 성숙도 · 단일 바이너리 크기 · Windows 백신 평판 · 빌드 · 서명 비용 · 하네스 어댑터 이식량 — 산출물: `docs/planning/runtime-port-review-2026-11.md`
- **WBS-49.2** 범위 선택지 · 권고안 · 소유자 결정 · ADR 초안 — 산출물: `docs/planning/runtime-port-review-2026-11.md`
