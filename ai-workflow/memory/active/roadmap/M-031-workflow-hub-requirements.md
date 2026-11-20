---
id: M-031
title: 2.0 허브 — requirements (요구 목록 · design 전 실측 · PURPOSE 2.0 판 · 1.x 정책)
sdlc_phase: requirements
status: in_progress
order: 31
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - docs/planning/workflow-hub-requirements-2026-11.md
goals: [G1, G2, G5]
---

# M-031 — 2.0 허브 — requirements (요구 목록 · design 전 실측 · PURPOSE 2.0 판 · 1.x 정책)

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

concept(M-030, docs/planning/workflow-hub-review-2026-11.md) 의 H1~H13 · 결정 전부를 검증 가능한 요구(R 번호)로 옮긴다. design 전에 재야 할 것 셋을 잰다.

## WBS

- **WBS-31.1** 요구 목록 — API · MCP 도구 · 부트스트랩 · 등록 · 콜사인 기억 · 지침 · 위키 · 로드맵 · 세션 시작 확인 · 오프라인 · 노출 · 1.x 전환 — 산출물: docs/planning/workflow-hub-requirements-2026-11.md
- **WBS-31.2** design 전 실측 — 판정 함수 데이터 입구 · 위키 검사 경로 인자화 범위 · 하네스별 원격 MCP 지원 — 산출물: requirements 문서 §실측
- **WBS-31.3** PURPOSE 2.0 판 (G1 · G3 · §4 명제 = D9) · 1.x 유지보수 정책 (G4 deprecation) — 산출물: PURPOSE.md 개정안 · requirements 문서 §1.x
