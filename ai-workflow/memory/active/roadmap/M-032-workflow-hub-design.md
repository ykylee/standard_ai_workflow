---
id: M-032
title: 2.0 허브 — design (ADR-033 Accepted + core 스펙)
sdlc_phase: design
status: done
order: 32
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/core/hub_spec.md
  - ai-workflow/wiki/decisions/adr-033-workflow-hub.md
goals: [G1, G2, G5]
---

# M-032 — 2.0 허브 — design (ADR-033 Accepted + core 스펙)

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

requirements(M-031) 를 스키마 · 형식 · 흐름으로 고정한다. ADR-033 을 Accepted 로 올린다.

## WBS

- **WBS-32.1** DB 스키마 · 이관 — 프로젝트(git 주소 별칭) · 콜사인 · task · 이력 · handoff · 지침 · 위키 · 로드맵 — 산출물: core/hub_spec.md §스키마
- **WBS-32.2** MCP 도구 · HTTP API 형식 — 부트스트랩 묶음(토큰 없음) · 나머지(콜사인 토큰) · 판 협상 — 산출물: core/hub_spec.md §도구
- **WBS-32.3** 흐름 — 부트스트랩 · 세션 시작 확인 · 세션 끝 · 지침 렌더링 · 1.x 전환 매핑 — 산출물: core/hub_spec.md §흐름
- **WBS-32.4** ADR-033 Accepted — 산출물: adr-033-workflow-hub.md
