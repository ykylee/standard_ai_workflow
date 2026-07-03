# Planning Documentation

- 문서 목적: Standard AI Workflow의 마일스톤, 릴리스 계획, 상위 로드맵을 영구 지식으로 관리한다.
- 범위: 마일스톤 정의, 릴리스 일정, 로드맵 백로그
- 대상 독자: 프로젝트 매니저, 저장소 maintainer, 멀티 에이전트 운영자
- 상태: draft
- 최종 수정일: 2026-07-03
- 관련 문서: [../PROJECT_PROFILE.md](../PROJECT_PROFILE.md), [../RELEASE.md](../RELEASE.md), [../INSTALLATION_AND_USAGE.md](../INSTALLATION_AND_USAGE.md), [../../workflow-source/core/workflow_kit_roadmap.md](../../workflow-source/core/workflow_kit_roadmap.md), [../../workflow-source/core/maturity_matrix.json](../../workflow-source/core/maturity_matrix.json)

> **Note**: 이 디렉토리는 v0.5.10 시점에 **초안** 상태. 정식 milestone 문서와 분기별 planning 회의록은 후속 세션에서 작성 예정. 아래 §1-§3 은 현재까지 진행 상황을 정리한 요약.

## 1. 현재 마일스톤 (v0.5.10-beta 기준)

| Phase | 상태 | 주요 결과물 | 완료일 |
|---|---|---|---|
| Phase 1–5 (기반) | done | 글로벌 표준, 템플릿, 스킬 1차 | 2026-04 ~ 2026-05 |
| Phase 6 (정밀 편집) | done | robust_patcher, smart-context-reader | 2026-04-28 (Beta v0.3.2) |
| Phase 7 (지능형 task modes) | done | workflow_task_modes.md + modes registry | 2026-05-02 |
| Phase 8 (Pilot deployment) | done | Devhub Example + external validation | 2026-05-02 |
| Phase 9 (System maturity + multi-agent evolution) | done | strict Pydantic contracts, MCP v1.0 SDK | 2026-05-03 (commit `2bb8bc7`) |
| Phase 10 (MCP/JSON-RPC draft) | done | read-only JSON-RPC bridge, fixture | 2026-05-03 (commit `2bb8bc7`) |
| Phase 11 (Pilot validation) | **in_progress** | Devhub Example × Contract v1 실전 검증 | 2026-06-07 ~ ongoing |
| Phase 12 (Package promotion) | planned | read-only MCP SDK server 정식 default 배포 | TBD (v0.5.11+) |

상세: [`../../workflow-source/core/workflow_kit_roadmap.md`](../../workflow-source/core/workflow_kit_roadmap.md) + [`../../workflow-source/core/maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json).

## 2. 릴리스 일정 (실제 진행, v0.5.0-beta 이후)

| 버전 | 릴리스 일자 | 핵심 변경 | 비고 |
|---|---|---|---|
| v0.5.0-beta | 2026-05-04 | 다중 에이전트 + 워크플로우 인텔리전스 | Beta 시작점 |
| v0.5.1 | 2026-06-05 | self-dogfooding bootstrap + MCP install 가이드 |  |
| v0.5.2 | 2026-06-06 | bootstrap 풀 리팩터 → `bootstrap_lib/` 6-module |  |
| v0.5.3 | 2026-06-07 | antigravity MCP config 표준화 |  |
| v0.5.4 | 2026-06-07 | orchestrator ↔ sub-agent contract v1 (issue #1) |  |
| v0.5.5 | 2026-06-07 | Phase 11 본격 pilot |  |
| v0.5.6 | 2026-06-07 | contract v1 P0 enforcement (validator + delegator) |  |
| v0.5.7 | 2026-06-08 | multi-component fan-out/in + cross-ref row |  |
| v0.5.7.1 | 2026-06-08 | wheel packaging state/contracts/schemas fix |  |
| v0.5.8 | 2026-06-08 | interactive --harness picker + packaging smoke |  |
| v0.5.9 | 2026-06-08 | wire 가이드 §7/§8/§9 보강 |  |
| v0.5.9.1 | 2026-06-08 | wire 가이드 §3 sub_payloads fix + 회귀 |  |
| v0.5.10 | 2026-06-08 | choose_roles sub.delegation_id parent-prefix spec 정합 |  |
| v0.5.10.1 | 2026-06-09 | smart update (VERSION marker + content hash 기반 silent 갱신) |  |

릴리스 노트 전체: [`../../workflow-source/releases/`](../../workflow-source/releases/). 절차: [`../RELEASE.md`](../RELEASE.md).

## 3. 단기 백로그 (v0.5.11 ~ v0.5.12 후보)

`Beta-v0.5.10.1.md` 의 §6 "Known limitations" 에서 도출된 항목:

1. **sub_id uniqueness 옵션 (b)**: `choose_roles` 에 dedup check 추가 (breaking change 가능, 별도 plan)
2. **`--report <path>` 옵션**: human-readable 갱신 리포트 (v0.5.10.1 hotfix 후속)
3. **`--preserve-user-edits` 옵션**: marker 동일 + hash 다름 시 skip (사용자 편집 보호)
2. **추가 회귀 test**: `parent_delegation_id` 누락, sub_id unique 위반 검출 (현재 17개 + 3개 회귀, 더 강화)
3. **`_generate_delegation_id_with_suffix` deprecation 정리**: function body 살아있음, v0.6.x 에서 제거
4. **bootstrap interactive picker (v0.5.8) 의 비대화형 환경 명세 강화**: `--no-interactive` 플래그 추가 검토
5. **docs/architecture/ 본격 채우기**: ADR-001/002/003 정식 기록
6. **docs/planning/ 분기별 planning 회의록 시작**

장기 (v0.6+):
- **contract v2 streaming/observability** — 대용량 sub-agent 출력의 streaming + observability
- **공식 MCP SDK stdio 안정화** — 현재 `stdio-sdk` 의 connection-closed 회귀 해결 후 default 전환
- **다중 실제 저장소 pilot 적용 사례** — `docs/examples/` 에 3건 이상 정식 기록
- **Mavis/MiniMax 외 추가 하네스 (Claude Code, Cursor, Windsurf 등) 오버레이** — `HARNESS_SPECS` + `register_harness_builder` 한 줄 추가 패턴 확장

## 다음에 읽을 문서

- [`../PROJECT_PROFILE.md`](../PROJECT_PROFILE.md) — 운영 규칙/명령
- [`../RELEASE.md`](../RELEASE.md) — 릴리스 절차
- [`../../workflow-source/core/workflow_kit_roadmap.md`](../../workflow-source/core/workflow_kit_roadmap.md) — 9단계 + Phase 11 로드맵
- [`../../workflow-source/core/maturity_matrix.json`](../../workflow-source/core/maturity_matrix.json) — phase/skill/MCP stage 정량 매트릭스
- [`../../workflow-source/core/phase11_pilot_validation_plan.md`](../../workflow-source/core/phase11_pilot_validation_plan.md) — Phase 11 pilot 검증 계획
- [`../../workflow-source/releases/`](../../workflow-source/releases/) — 전체 릴리스 노트
