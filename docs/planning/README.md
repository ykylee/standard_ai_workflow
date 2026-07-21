# Planning Documentation

- 문서 목적: Standard AI Workflow의 마일스톤, 릴리스 계획, 상위 로드맵을 영구 지식으로 관리한다.
- 범위: 마일스톤 정의, 릴리스 일정, 로드맵 백로그
- 대상 독자: 프로젝트 매니저, 저장소 maintainer, 멀티 에이전트 운영자
- 상태: stable
- 최종 수정일: 2026-07-21
- 관련 문서: [../PROJECT_PROFILE.md](../PROJECT_PROFILE.md), [../RELEASE.md](../RELEASE.md), [../INSTALLATION_AND_USAGE.md](../INSTALLATION_AND_USAGE.md), [../../workflow-source/core/workflow_kit_roadmap.md](../../workflow-source/core/workflow_kit_roadmap.md), [../../workflow-source/core/maturity_matrix.json](../../workflow-source/core/maturity_matrix.json)

> 이 문서는 상위 요약이다. 단계별 상태의 SSOT는 `workflow-source/core/maturity_matrix.json`이다.

## 1. 현재 마일스톤 (v0.15.15-beta 기준)

| Phase | 상태 | 주요 결과물 | 완료·진행 기준 |
|---|---|---|---|
| Phase 1–5 | done | 개념, 템플릿, prototype, beta/pilot, intelligence 기반 | 2026-04 ~ 2026-05 |
| Phase 6–10 | done | 정밀 편집, task modes, pilot integration, system maturity, 문서·링크 hygiene | maturity matrix 기준 완료 |
| Phase 11 | done | real-world pilot validation + contract v1 + stable API freeze 기반 | v0.9.0 (2026-06-18) |
| Phase 12 | **in_progress** | operational intelligence + deprecation stabilization | target: **v1.0.0 stable guarantee** |

Phase 12의 현재 근거:

- full mypy strict 도달 및 유지
- skill 12종 stable
- MCP 11종 stable + 1종 removed
- 10개 harness 지원
- Quality Dashboard Panel 1~8 및 telemetry/self-recovery/bidirectional-link 운영
- append-only memory layout와 v0.15.0 deprecation cycle 완료
- v0.15.1~v0.15.15 사용자 문서·sample·harness cross-check 완료

## 2. 최근 릴리스 흐름

| 버전 범위 | 핵심 변경 | 상태 |
|---|---|---|
| v0.11.18~v0.11.22 | full mypy strict, skill stable promotion, Memora-inspired memory index | 완료 |
| v0.13.0~v0.13.3 | dashboard, telemetry, self-recovery, wiki↔memory bidirectional link | 완료 |
| v0.14.0~v0.15.0 | append-only memory + deprecation 2-cycle 안정화 | 완료 |
| v0.15.1~v0.15.15 | dashboard·harness·sample·README·설치·quickstart 정합 보강 | release 준비 |

릴리스 노트 전체는 [`../../workflow-source/releases/`](../../workflow-source/releases/)에서 확인한다.

## 3. 다음 우선순위: v1.0.0 진입 평가

1. public Python API와 CLI surface를 열거하고 stable 보장 대상을 확정한다.
2. Pydantic output 및 generated JSON Schema의 호환성 정책을 명시한다.
3. Python 최소 버전, dependency 범위, MCP transport 지원 단계를 확정한다.
4. breaking change 및 deprecation cycle 정책을 v1.0.0 기준으로 재검증한다.
5. 설치, upgrade, rollback, package verification 절차를 stable gate로 정리한다.
6. repository-wide 검증의 historical fixture/archive exclusion 정책을 결정한다.
7. 조건 충족 시 maturity matrix의 Phase 12를 close하고 v1.0.0 release plan을 승인한다.

## 다음에 읽을 문서

- [`../PROJECT_PROFILE.md`](../PROJECT_PROFILE.md) — 운영 규칙과 명령
- [`../RELEASE.md`](../RELEASE.md) — 릴리스 절차
- [`../../workflow-source/core/workflow_kit_roadmap.md`](../../workflow-source/core/workflow_kit_roadmap.md) — 상위 로드맵
- [`../../workflow-source/core/maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json) — 단계별 정량 SSOT
- [`../architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md`](../architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md) — MCP stdio SDK 승격 평가
- [`../../workflow-source/releases/Beta-v0.15.15.md`](../../workflow-source/releases/Beta-v0.15.15.md) — 현재 release close-out
