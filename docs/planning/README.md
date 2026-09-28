# Planning Documentation

- 문서 목적: Standard AI Workflow의 마일스톤, 릴리스 계획, 상위 로드맵을 영구 지식으로 관리한다.
- 범위: 계획 문서 목록과, 현재 진척·성숙도·발행 이력의 정본 위치
- 대상 독자: 프로젝트 매니저, 저장소 maintainer, 멀티 에이전트 운영자
- 상태: stable
- 최종 수정일: 2026-09-28
- 관련 문서: [../PROJECT_PROFILE.md](../PROJECT_PROFILE.md), [../RELEASE.md](../RELEASE.md), [../INSTALLATION_AND_USAGE.md](../INSTALLATION_AND_USAGE.md), [../../workflow-source/core/workflow_kit_roadmap.md](../../workflow-source/core/workflow_kit_roadmap.md), [../../workflow-source/core/maturity_matrix.json](../../workflow-source/core/maturity_matrix.json)

> 이 문서는 **계획 문서의 입구**다. 현재 진척을 손으로 요약하지 않는다 — 정본을 가리킨다.

## 1. 현재 진척은 어디서 보나

| 알고 싶은 것 | 정본 | 보는 법 |
|---|---|---|
| 지금 진행 중인 마일스톤 · SDLC 단계 · WBS 진척 | [`roadmap/index.md`](../../ai-workflow/memory/active/roadmap/index.md) (선언) + `roadmap_state.json` (생성물) | `wk session-start` 의 `roadmap_context`, `wk dashboard` Panel 1 `phase` |
| skill · MCP · 하네스 성숙도 | [`maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json) | `wk dashboard` Panel 2 |
| 발행 이력 | [`CHANGELOG.md`](../../workflow-source/CHANGELOG.md) · [`releases/`](../../workflow-source/releases/) | GitHub Releases |

> **왜 요약표를 걷었나** (TASK-2026-09-23-main-015). 이 자리에 'v0.15.15-beta 기준 ·
> Phase 12 in_progress · 다음 우선순위: v1.0.0 진입 평가' 가 있었다. v1.0.0-beta 는
> 2026-07-22 에 발행됐고 'Phase N' 명명은 ADR-027(마일스톤·WBS)로 대체됐는데, 표는
> v1.11.0 까지 그대로였다 — 버전을 올려도 안 바뀌는 **상수 표시**였다. 대시보드의 같은
> 칸도 리터럴이었고, 지금은 로드맵 정본에서 파생한다. 옛 표는 git 이력에 있다.

## 2. 플러그인 배포 전환 (2026-08-12 착수 → v1.2.0-beta 완료)

배포 전략을 플러그인 중심으로 전환하는 주 작업 축. 검토 2건 → 실행 계획 1건:

- [`plugin-distribution-review-2026-08.md`](./plugin-distribution-review-2026-08.md) — Claude Code 플러그인 검토 (채택 권고, "14번째 파생본" 원칙)
- [`multi-harness-plugin-review-2026-08.md`](./multi-harness-plugin-review-2026-08.md) — 멀티 하네스 공유 검토 (공유 payload + 얇은 어댑터 권고)
- [`plugin-transition-plan-2026-08.md`](./plugin-transition-plan-2026-08.md) — **전환 계획·로드맵 P1~P5·WBS** (TASK-2026-08-12-main-013~018)

## 다음에 읽을 문서

- [`../PROJECT_PROFILE.md`](../PROJECT_PROFILE.md) — 운영 규칙과 명령
- [`../RELEASE.md`](../RELEASE.md) — 릴리스 절차
- [`../../workflow-source/core/workflow_kit_roadmap.md`](../../workflow-source/core/workflow_kit_roadmap.md) — 상위 로드맵
- [`../../workflow-source/core/maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json) — 성숙도 정량 SSOT
- [`../../ai-workflow/memory/active/roadmap/index.md`](../../ai-workflow/memory/active/roadmap/index.md) — 마일스톤·WBS 진척 SSOT
- [`../architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md`](../architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md) — MCP stdio SDK 승격 평가
- [`../../workflow-source/CHANGELOG.md`](../../workflow-source/CHANGELOG.md) — 발행 이력
