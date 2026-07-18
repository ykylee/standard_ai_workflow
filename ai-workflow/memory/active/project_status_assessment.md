# Project Workflow Maturity Assessment

- 문서 목적: 프로젝트의 AI 워크플로우 도입 수준을 자가 진단하고 개선 포인트를 도출한다.
- 범위: 기본 문서화, 도구 활용도, 프로세스 준수도, 지능화 수준
- 대상 독자: 프로젝트 리드, AI 에이전트, 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-07-09
- 관련 문서: [공통 표준](../core/global_workflow_standard.md), [maturity_matrix.json](../core/maturity_matrix.json), [workflow_kit_roadmap.md](../core/workflow_kit_roadmap.md)

## 1. 진단 요약 (Executive Summary)

- **현재 레벨**: Phase 12 (Operational Intelligence, in_progress) — v0.11.22-beta baseline.
- **핵심 강점**: FULL mypy strict 도달 (109 file clean, 0 errors, v0.11.18), 11 skill stable (3 batch: v0.11.19/20/21), ADR-005 Memora-inspired Memory Index Phase 1~3d 8 release 완료, stdio-sdk v0.11.25 정식 stable 승격, 10 harness overlay (CodeWhale 까지), drift prevention automation (v0.11.23).
- **개선 필요 항목**: ADR-006 retrospective 자리만 박힘 (본문 미작성, 30일 후), MCP beta 4종 stable 승격 로드맵 부재, drift prevention silent 차단 사례 미분류, Phase 13 north-star 미정.
- **차기 목표**: Phase 12 마감 (ADR-006 회고 + MCP beta 승격 + drift 사례 분류) 후 Phase 13 정의 (운영 지능화 / 품질 대시보드 / 자동 재현 중 north-star 1개 선정).

---

## 2. 진단 매트릭스 (Assessment Matrix)

| 구분 | 진단 항목 | 현황 (0~3) | 비고 |
| --- | --- | --- | --- |
| **기본 문서** | `PROJECT_PROFILE.md`가 최신 상태인가? | **1** | `docs/PROJECT_PROFILE.md` §1/§3/§4/§5 TODO 잔존 (P0-2 후보). 외부 배포용 `docs/PROJECT_PROFILE.md` 는 최신. |
| | `session_handoff.md`가 매 세션 갱신되는가? | **2** | `ai-workflow/memory/active/` 에 `session_handoff.md` 부재. `session_analysis_YYYY-MM-DD.md` 패턴으로 대체 (audit-session 2026-07-09 등). spec 의 `session_handoff_template.md` 와 명칭/위치 불일치 — 정규화 후보. |
| | `work_backlog.md`가 실제 작업과 동기화되는가? | **3** | `work_backlog.md` 인덱스에 release/v0.11.x + active/session_analysis anchor 등록. session-start skill (v0.11.19 stable, opt-in wiring v0.11.22) 로 자동 load. |
| **도구 활용** | MCP 도구를 사용하여 문서를 조회/수정하는가? | **3** | stable 8종 (`latest_backlog`, `check_doc_metadata`, `check_doc_links`, `create_backlog_entry`, `suggest_impacted_docs`, `create_session_handoff_draft`, `create_environment_record_stub`, `check_quickstart_stale_links`). stdio-sdk v0.11.25 stable. |
| | `workflow-linter`를 주기적으로 실행하는가? | **2** | stable (v0.11.20 2차 batch). drift prevention automation (v0.11.23) 이 6 case smoke + `check_drift_prevention_v0_11_23.py` cross-check 로 일부 자동화. silent fail 91 cycle 사례 미분류 (P1-3 후보). |
| | `session-start` 스킬로 컨텍스트를 복원하는가? | **3** | stable (v0.11.19 1차 batch). ADR-005 Phase 3b memory_index opt-in wiring (v0.11.22). work_backlog.md + state.json + recent_done_items 자동 load. |
| **프로세스** | 작업 전 브리핑 및 계획 수립을 수행하는가? | **3** | `.omo/plans/` 에 v0.5.11+, v0.6.1+, hotfix-smart-update 등 5건 보존. orchestrator-subagent contract v1 + Momus 5-round audit 패턴 정착. |
| | 검증(Validate) 단계를 반드시 거치는가? | **3** | validation-plan skill stable (v0.11.19 1차 batch). 누적 smoke 200+ PASS (roadmap §1.3). 3-layer defense: CI mypy-strict workflow + release-time gate + ci_sanity cross-verify. |
| | 작업 모드(Task Modes)를 명시하여 최적화하는가? | **2** | `workflow_kit/common/modes/registry.py` 존재, `workflow_task_modes.md` 정의. task-modes 가 maturity_matrix 에서 stable 로 기록되나 일부 모드 (예: Pilot, Release) 가 runtime 자동 감지 외 수동 지정 케이스 잔존. |
| **품질/거버넌스** | `maturity_matrix.json`과 문서가 동기화되는가? | **2** | drift prevention automation v0.11.23 추가, sync-maturity-matrix helper. v0.5.x~v0.11.x 13 file drift remediation (4633d34) 완료. 그러나 v0.7.10~v0.11.22 9 release cycle 누적 drift 가 silent 통과 — proactive 회귀 test 보강 필요 (P1-3 후보). |
| | 릴리즈 노트 형식을 준수하여 배포하는가? | **3** | Beta-v0.X.Y.md + backlog/YYYY-MM-DD.md + state.json recent_done_items 3중 동기화 정착. GitHub Release tag push + gh release create 자동화 (release --full-auto). v0.11.19~v0.11.25 6 release 무결. |

*점수 가이드: 0(미도입), 1(수동 도입), 2(부분 자동화), 3(완전 정착)*

### 2.1 종합 점수 산정

- **합계**: 26 / 33 (78.8 %)
- **분포**: 3점 × 7개 / 2점 × 3개 / 1점 × 1개 / 0점 × 0개
- **약점 영역**: 기본 문서 (PROJECT_PROFILE.md self-dogfood), 품질/거버넌스 (drift proactive 차단)

---

## 3. 레벨별 정의 (Level Definitions)

### [Alpha] 도입 단계
- 기본 운영 문서(`memory/`)가 존재함.
- 에이전트가 문서를 수동으로 읽고 갱신함.
- 검증 절차가 정의되어 있으나 누락되는 경우가 있음.

### [Beta] 가속 단계
- MCP 도구 및 표준 스킬을 적극 활용함.
- 세션 간 인계(`handoff`)가 정형화됨.
- **작업 모드**를 인지하여 효율적으로 작업을 분담함.

### [Stable] 최적화 단계
- 워크플로우 린트가 자동화되어 문서 정합성이 상시 보장됨.
- 성숙도 매트릭스에 기반한 지능형 작업 분배가 이루어짐.
- 프로젝트 특화 스킬 및 도구가 커스텀 개발되어 적용됨.

### [Phase 9] 지능형 협업 단계 (Multi-Agent Evolution)
- **엄격한 데이터 계약**: 모든 입출력이 Pydantic 모델을 통해 검증됨.
- **공식 MCP v1.0 SDK**: 표준 프로토콜을 통한 양방향 에이전트-도구 통신 실현.
- **다중 에이전트 토폴로지**: 오케스트레이터가 하네스(Antigravity 등)의 역량을 인지하고 전용 워커(Doc/Code/Validation)에게 업무를 동적으로 위임함.

### [Phase 10] 문서·링크 위생 단계 (Document & Link Hygiene)
- mkdocs 자동 빌드 + GitHub Pages 배포 (외부 사이트).
- generated_output_schemas.json SSOT + 외부 schema 배포.
- 위생 audit + README/QUICKSTART cross-check 자동화.

### [Phase 11] 실전 파일럿 검증 단계 (Real-world Pilot Validation) — **closed (v0.9.0)**
- DevHub Example × Contract v1 실전 검증.
- stable API frozen + generated JSON Schema SSOT + read-only MCP transport.
- release-dist 1-command + deprecation 1st cycle 적용.

### [Phase 12] 운영 지능화 + Deprecation 안정화 단계 (Operational Intelligence + Deprecation Stabilization) — **in_progress**
- FULL mypy strict 도달 (109 file clean, 0 errors).
- 11 skill stable (3 batch) + 1 beta (git-conflict-resolver, apply=False).
- ADR-005 Memora-inspired Memory Index Phase 1~3d 8 release.
- stdio-sdk v0.11.25 정식 stable 승격.
- Drift prevention automation (v0.11.23) — 누적 9 release cycle drift 보강.
- 10 harness overlay (CodeWhale 까지, v0.10.4 cf0060d).
- 누적 smoke 200+ PASS.

---

## 4. 향후 개선 계획 (Roadmap to Next Level)

### 4.1 단기 — Phase 12 마감 (2026-Q3 이내)

- [ ] **P0-2**: `docs/PROJECT_PROFILE.md` self-dogfood profile 작성 (§1/§3/§4/§5 TODO 해소).
- [ ] **P0-3**: `ai-workflow/memory/active/memory_index/` 디렉토리 실재성 확인 + opt-in wiring 실 데이터 시드.
- [ ] **P1-1**: ADR-006 retrospective 본문 작성 (2026-08-02 ± 3일, lessons learned 잠금).
- [ ] **P1-2**: Beta MCP 4종 stable 승격 로드맵 (`maturity_matrix.mcp_tools.promotion_in_release` 필드 추가).
- [ ] **P1-3**: Drift prevention silent 차단 91 cycle 사례 분류 운영 노트 + dashboard (quality dashboard 의 seed).

### 4.2 중기 — Phase 13 설계 (2026-Q4 후보)

- [ ] **P2-1**: Phase 13 north-star metric 1개 선정 (운영 지능화 / 품질 대시보드 / 자동 재현 중 택1) + acceptance criteria 작성.
- [ ] **P2-2**: Wiki ↔ Memory 양방향 link 자동화 (provenance → wiki page).
- [ ] **P2-3**: Quality dashboard 구현 (silent drift count / mypy trend / skill maturity 분포 시각화).
- [ ] **P2-4**: `automated-repro-scaffold` AI 에이전트 연동 강화 (roadmap §1.1 후속).

## 다음에 읽을 문서
- [공통 표준](../core/global_workflow_standard.md)
- [maturity_matrix.json](../core/maturity_matrix.json)
- [workflow_kit_roadmap.md](../core/workflow_kit_roadmap.md)
- [workflow_audit_2026-07-09.md](../../wiki/topics/workflow-audit-2026-07-09.md)
