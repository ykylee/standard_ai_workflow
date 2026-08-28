# Roadmap — standard_ai_workflow

- 문서 목적: ADR-027 로드맵 층의 SSOT index — 마일스톤 목록과 SDLC 순서를 선언한다.
- 범위: 로드맵·마일스톤·WBS 기능 자체의 구현 로드맵 (스펙 §10 의 자기 적용)
- 대상 독자: AI agent (session-start / backlog-update), 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-28
- 관련 문서: [`roadmap_milestone_wbs_spec.md`](../../../../workflow-source/core/roadmap_milestone_wbs_spec.md), [`roadmap_state.json`](./roadmap_state.json)

> 이 목록의 **순서가 곧 SDLC 순서 선언**이다 (스펙 §3.1). status 는 선언이고,
> 파생 진척과의 불일치는 `roadmap_state.json` 의 issues 가 지목한다.
> `roadmap_state.json` 은 생성물이다 — 손으로 고치지 않는다.

## Milestones

- **M-001** [design] ADR-027 결정 + 정본 스펙 — status: done
  - path: [`./M-001-adr-and-spec.md`](./M-001-adr-and-spec.md)
- **M-002** [implementation] 스키마·파서·상태 생성기·검사·씨앗 — status: done
  - path: [`./M-002-schema-parser-state.md`](./M-002-schema-parser-state.md)
- **M-003** [implementation] refresh-state 통합 + session-start 배선 — status: done
  - path: [`./M-003-wiring-refresh-session-start.md`](./M-003-wiring-refresh-session-start.md)
- **M-004** [implementation] backlog-update 게이트 + 예외 선언 — status: done
  - path: [`./M-004-backlog-gates.md`](./M-004-backlog-gates.md)
- **M-005** [implementation] bootstrap 씨앗 + 온보딩 SDLC 기본 — status: done
  - path: [`./M-005-bootstrap-onboarding-seed.md`](./M-005-bootstrap-onboarding-seed.md)
- **M-006** [release] 릴리스 + 상시 운용 전환 — status: done
  - path: [`./M-006-release-and-operation.md`](./M-006-release-and-operation.md)
- **M-007** [stabilization] 운영 축 (상설) — status: in_progress
  - path: [`./M-007-operations-standing.md`](./M-007-operations-standing.md)
- **M-008** [concept] 검사 입력 표면 선언 + 계층별 회귀 실행 계약 — status: done
  - path: [`./M-008-test-impact-tiering.md`](./M-008-test-impact-tiering.md)
- **M-009** [requirements] 계층별 회귀 실행 계약 — requirements (WATCHES 보급 + 선언 메타 검증) — status: done
  - path: [`./M-009-test-impact-requirements.md`](./M-009-test-impact-requirements.md)
- **M-010** [design] 계층별 회귀 실행 계약 — design (ADR-028 + core 스펙 절) — status: done
  - path: [`./M-010-test-impact-design.md`](./M-010-test-impact-design.md)
- **M-011** [implementation] 계층별 회귀 실행 계약 — implementation (meta-watch 러너 통합) — status: done
  - path: [`./M-011-test-impact-implementation.md`](./M-011-test-impact-implementation.md)
- **M-012** [release] 계층별 회귀 실행 계약 — release (v1.7.0 발행 + CLAUDE.md 전환) — status: in_progress
  - path: [`./M-012-test-impact-release.md`](./M-012-test-impact-release.md)
