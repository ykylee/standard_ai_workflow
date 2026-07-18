---
type: topic
status: active
last_ingested_from: ai-workflow/memory/active/session_analysis_2026-07-09.md + workflow-source/core/maturity_matrix.json + workflow-source/core/workflow_kit_roadmap.md
related_pages: [topics/standard-ai-workflow-architecture-2026, concepts/memory-3-state-lifecycle, concepts/project-architecture, decisions/adr-005-r9-wiki-source-rule, decisions/adr-006-okf-compat-frontmatter, patterns/memory-write-merge]
created: 2026-07-09
updated: 2026-07-09
---

# Workflow Audit & Enhancement Candidates (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 세션에서 진행한 `standard_ai_workflow` 저장소의 워크플로우 구성 점검 결과를 영구 기록한 audit 보고서다. 현 상태 스냅샷, **P0/P1/P2 우선순위별 고도화 후보 10건**, 권장 작업 순서를 정리한다. 입력 SSOT 는 `maturity_matrix.json` (v0.11.22-beta 갱신일자 2026-07-03) 이며, 단기 메모리 (`memory/active/session_analysis_2026-07-09.md`) 와 상호 링크.

## 1. 점검 컨텍스트

- **점검 시각**: 2026-07-09 (UTC)
- **저장소**: `/home/yklee/repos/standard_ai_workflow`
- **베이스라인 버전**: v0.11.22-beta (package: standard-ai-workflow 0.11.22)
- **대상**: Source layer (workflow-source/core), Runtime layer (ai-workflow/memory, ai-workflow/wiki), Maturity SSOT
- **방법**: 정적 문서/manifest 분석 (코드 실행 없음). mypy/CI/smoke 결과는 maturity_matrix 누적치 인용.

## 2. 현 상태 스냅샷

| # | 영역 | 값 | 출처 |
|---|---|---|---|
| 1 | Phase | 1–11 done, **12 in_progress** | maturity_matrix.milestones |
| 2 | Skill 성숙도 | stable=9 / beta=2 / prototype=4 (+ task-modes stable) | maturity_matrix.skills |
| 3 | MCP 도구 | stable=8 / beta=4 | maturity_matrix.mcp_tools |
| 4 | Transport | stdio-sdk stable + jsonrpc-bridge stable | maturity_matrix.transports |
| 5 | Harness overlay | 10종 (마지막: CodeWhale, v0.10.4 cf0060d) | maturity_matrix.harnesses |
| 6 | Mypy strict | 109 file clean, 0 errors | roadmap §1.1, Phase 12 누적 |
| 7 | Memory Index | ADR-005 Phase 1~3d 8 release 완료 | roadmap §1.1, state.json |
| 8 | 누적 smoke | 200+ PASS | roadmap §1.3 |

### 2.1 Skills stable 분포 (9종)

session-start, backlog-update, doc-sync, merge-doc-reconcile, validation-plan, code-index-update, workflow-linter, project-status-assessment, robust-patcher. Beta 잔존 2종: automated-repro-scaffold, git-conflict-resolver (apply=False 유지).

### 2.2 MCP beta 잔존 (4종)

git_history_summarizer, workflow_log_rotator, smart_context_reader, apply_robust_patch. skill 과 달리 stable 승격 batch 진행 이력 없음.

## 3. 고도화 후보 (P0/P1/P2)

### 3.1 P0 — 즉시 가치 (정합성·silent fail 차단)

| # | 후보 | 위치 | 영향 |
|---|---|---|---|
| P0-1 | `project_status_assessment.md` §2 자가진단 매트릭스 11항목 공란 | `ai-workflow/memory/active/project_status_assessment.md:30-43` | Phase 9 표기이나 정량 점수 부재 → 추세 추적 불가 |
| P0-2 | `PROJECT_PROFILE.md` self-dogfood profile 미작성 | `docs/PROJECT_PROFILE.md` §1/§3/§4/§5 TODO | 본 저장소의 운영 profile 부재 |
| P0-3 | `ai-workflow/memory/active/memory_index/` 디렉토리 부재 | `ai-workflow/memory/active/` | opt-in wiring 의 실 데이터 부재 → retrieval silent fail 가능성 |

### 3.2 P1 — 운영 지능화 심화 (Phase 12 마감)

| # | 후보 | 위치 | 영향 |
|---|---|---|---|
| P1-1 | ADR-006 retrospective 본문 미작성 | `ai-workflow/wiki/decisions/adr-006-okf-compat-frontmatter.md` | 30일 후 (대략 2026-08-02) 회고 예정, lessons learned 잠금 |
| P1-2 | Beta MCP 4종 stable 승격 로드맵 부재 | `maturity_matrix.mcp_tools` | promotion_in_release 필드 없음, skill 3-batch 패턴 미적용 |
| P1-3 | Drift prevention silent 91-cycle 사례 미분류 | `workflow_kit/<drift_prevention_module>` (확인 필요) | 차단 원인 운영 노트/dashboard 없음 → 재발 시 추적 어려움 |

### 3.3 P2 — Phase 13 후보 (north-star 미정)

| # | 후보 | 위치 | 영향 |
|---|---|---|---|
| P2-1 | Phase 13 정의 부재 | `workflow-source/core/workflow_kit_roadmap.md` | north-star metric / acceptance criteria 미정 |
| P2-2 | Wiki ↔ Memory 양방향 link 수동 | `ai-workflow/wiki/` ↔ `ai-workflow/memory/` | ADR-005 가 memory side 만 보강, provenance → wiki 자동 link 후보 |
| P2-3 | Quality dashboard 미구현 | roadmap §1.1 "품질 대시보드" 항목 | 운영 지표 시각화 가이드 부재 |
| P2-4 | `automated-repro-scaffold` AI 에이전트 연동 강화 | `workflow-source/skills/automated-repro-scaffold/` | v0.11.23 stable, roadmap §1.1 AI 에이전트 연동 강화 미반영 |

## 4. 권장 작업 순서

1. **빠른 정리 (P0)** — 3개 항목 일괄 처리 (1 release = 1-2 file 격상 정책 적용 가능).
2. **Phase 12 마감 (P1)** — ADR-006 retrospective 먼저, MCP 승격 로드맵 / drift 사례 분류 후속.
3. **Phase 13 설계 (P2)** — north-star 1개 선정 후 roadmap §2 갱신 (예: "운영 지능화" 또는 "품질 대시보드").

## 5. 인용 및 후속

- 단기 메모리: `ai-workflow/memory/active/session_analysis_2026-07-09.md`
- SSOT: `workflow-source/core/maturity_matrix.json`
- 로드맵: `workflow-source/core/workflow_kit_roadmap.md`
- 후속 작업 시 wiki index (`ai-workflow/wiki/index.md`) 에 본 토픽 등록 여부 확인 필요.
