---
type: topic
status: draft
related_pages:
  - topics/workflow-audit-2026-07-09
  - topics/mcp-beta-promotion-roadmap-2026
  - topics/drift-prevention-91-cycle-classification-2026
  - workflow-source/core/workflow_kit_roadmap.md
  - workflow-source/core/maturity_matrix.json
created: 2026-07-09
updated: 2026-07-09
---

# Phase 13 정의 — north-star metric 및 acceptance criteria (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P2-1 후보 (Phase 13 정의 부재) 를 해소하기 위한 *제안*. roadmap §1.1 의 4 미이행 항목 중 stdio-sdk 안정화 (v0.11.25 완료) 를 제외한 3 항목을 north-star 후보로 평가하고, **운영 지능화 (operational intelligence)** 를 1차 north-star 로 제안한다. acceptance criteria 3+1개 정의 + 검증 helper 후보 명시.

## 1. Phase 13 후보 평가

### 1.1 후보 north-star 3종 (roadmap §1.1 미이행 항목 중)

| 후보 | 정의 | 강점 | 약점 | 본 토픽 평가 |
|---|---|---|---|---|
| **N1. 운영 지능화** | MCP 도구 + memory_index 의 실사용 활용도, drift 자동 차단, retrospective 자동화 | 본 프로젝트의 core 차별점 (multi-agent evolution). 이미 memory_index (ADR-005) + drift prevention (v0.11.23) 의 *인프라* 가 있음. 활용도만 높이면 됨. | "활용도" 측정 어려움. 정량 metric 모호. | **1차 north-star 추천** |
| **N2. 품질 대시보드** | 운영 지표 (mypy trend / drift count / skill maturity) 시각화 | 가시성 확보로 운영 의사결정 가속. P2-3 와 직접 매핑. | metric 정의는 부분적. dashboard 자체가 end 가 아니라 *수단*. | 1차 north-star *보조 지표* 로 |
| **N3. 자동 재현 고도화** | `automated-repro-scaffold` 의 AI 에이전트 연동 강화 | reproduction 자동화는 디버깅 비용 절감. 외부 consumer 도움. | ROI 가 project 마다 다름. metric 측정이 운영 단계와 분리. | 2차 north-star (Phase 13 후속) |

### 1.2 north-star 선정 근거

**운영 지능화** 를 1차 north-star 로 선정:

1. **본 프로젝트의 차별점 정합**: standard_ai_workflow 는 *multi-agent evolution* (Phase 9) 의 extension. "운영 지능화" 는 그 진화 방향의 *운영 측 counterpart*.
2. **인프라 already built**: ADR-005 Memory Index + v0.11.23 Drift Prevention + ADR-007 OKF Consumer Mode 의 *인프라* 가 존재. 활용도만 높이면 됨 (재창조 ❌).
3. **측정 가능성**: 3 정량 metric (drift count / skill maturity 평균 / memory_index hit rate) 으로 측정 가능.
4. **전략 일치**: roadmap §1.1 의 첫 미이행 항목.

**품질 대시보드** 는 운영 지능화의 *수단* (visualization layer) 으로 흡수. N1 의 sub-metric.

**자동 재현 고도화** 는 Phase 13 의 *sub-milestone* 으로 흡수. 별도 phase 는 아님.

## 2. Phase 13 정의 (제안)

### 2.1 Phase 13 이름

**"Operational Intelligence v1.0 — Self-aware, Self-documenting, Self-recovering"**

핵심: *workflow 운영이 외부 intervention 없이 자가 인식 / 자가 문서화 / 자가 복구* 되는 단계.

### 2.2 north-star metric

**north-star: silent_failing_cycles_count**

정의: drift prevention guard 가 검출했으나 manual fix 까지 걸린 release cycle 의 누적 갯수. 본 metric 는 *0* 으로 수렴하는 것이 목표.

산정식 (제안):
```
silent_failing_cycles_count = sum(
    1 for release in releases
    if check_drift_prevention_v0_11_23.py would have failed
    AND was not detected by CI
)
```

### 2.3 acceptance criteria (3+1)

#### AC1. drift zero (P0)

- `check_drift_prevention_v0_11_23.py` 가 모든 release 직전 PASS.
- 신규 추가 case (P1-3 §5.2 의 5 hook 후보) 가 모두 PASS.
- silent_failing_cycles_count = 0 (연속 N release 동안).

#### AC2. memory_index 활용도 (P1) — **v0.13.1 (2026-07-09) close ✅**

- 3 skill (session-start / doc-sync / backlog-update) 의 opt-in retrieval wiring 의 *실제 호출 횟수* 가 측정 가능.
- 최소 사용 baseline: 1 release = 1+ retrieval 호출 (audit / retrospective 시).
- memory_index entry 갯수가 누적 증가 추세.
- **v0.13.1 telemetry sidecar 인프라** (release v0.13.1-beta, 2026-07-09):
  - `ai-workflow/memory/active/memory_index/telemetry/events.jsonl` 에 3 skill + dispatcher 의 opt-in retrieval 호출 자동 emit
  - `MemoryIndexTelemetryEvent` + `MemoryIndexTelemetrySummary` 2 schema
  - `append_telemetry_event` (in-process lock + JSONL append) + `summarize_telemetry` (JSONL parse + malformed skip + error-flag skip)
  - dashboard panel 3 의 `retrieval_hit_rate: 0.0` placeholder → 실측값 전환 (`retrieval_hit_rate_source: memory_index_telemetry_v0_13_1`)
  - `cmd_memory_index_telemetry` subcommand 36 (read-only inspect, --json / --show-events)
  - `check_memory_index_telemetry.py` 6/6 PASS (1 emit / 2-hit-1-miss / by_source / malformed skip / graceful empty / concurrent append 10 line 보존)
  - mypy strict 0 new error + drift prevention 6/6 PASS + 3 skill smoke 3/3 PASS

#### AC3. self-recovering (P2) — **v0.13.2 (2026-07-09) close ✅**

- drift 발견 시 `release_pipeline.py sync-maturity-matrix` 가 *자동 fix* (manual intervention 0).
- 1 release cycle 내 fix cycle closed.
- self-recovery log 가 release note 본문에 자동 emit.
- **v0.13.2 self-recover orchestrator** (release v0.13.2-beta, 2026-07-09):
  - `cmd_self_recover` dispatcher subcommand 37 (`--apply` / `--dry-run` / `--json`)
  - detect (`_run_drift_prevention_smoke` subprocess) + classify (`_classify_drift_failures` + `_SELF_RECOVER_CASE_MAP` dict) + fix (5 fix callable: `_fix_loud_fallback` / `_fix_readme_header_version` / `_fix_maturity_matrix_drift` × 2 case) + re-check (6/6 PASS) + emit (`_emit_recovery_summary` dict)
  - `cmd_release` 의 validate step 후 `cmd_self_recover` 자동 호출 + manual_required > 0 시 early return + `--skip-self-recover` escape hatch
  - `_emit_self_recovery_log` 가 release note 본문 끝에 `## Self-recovery log` 섹션 자동 append (idempotent marker)
  - `check_self_recovering_v0_13_2.py` 8/8 PASS
  - mypy strict 0 new error (22→21 errors via workflow_kit_cli import explicit export fix)
  - in-scope fix: sys.path standalone import bug + README_PATH root relative 정정
  - manual_required 2 case (`case_2` Phase status / `case_3` skill stage) — release note 의 `closed_phases` / `promoted_skills` frontmatter 가 제공되어야 fix 가능 (drift-prevention-91-cycle-classification §5 hook 와 후속 cycle 흡수 예정)

#### AC4+. (선택) self-documenting — **v0.13.3 (2026-07-09) close ✅**

- `audit_log_standard.md` §4 의 audit log 가 자동 emit.
- 위키 / memory 양방향 link 가 자동 갱신 (P2-2).
- 외부 consumer 가 wiki 의 자동 cross-link 를 *신뢰* 가능.
- **v0.13.3 bidir-link close-out** (release v0.13.3-beta, 2026-07-09):
  - `workflow_kit/common/state/bidir_link.py` 신규 (260 line, R-A sync + R-C audit 통합)
  - `cmd_bidir_link` dispatcher subcommand 38 (`--apply` / `--json` flag, default = audit only)
  - `cmd_release` step 2.8 — sync-maturity-matrix 후 bidir-link audit 자동 호출 (advisory only, `--skip-bidir-link` escape hatch)
  - release note 본문에 `## Bidirectional link audit` 섹션 자동 append (idempotent marker)
  - `check_bidir_link_v0_13_3.py` 6/6 PASS (audit shape / path normalization / dry-run / sync apply / re-audit / format)
  - mypy strict 0 new error (21→21 errors 유지)
  - drift prevention 6/6 PASS (clean state)
  - **audit 실측**: `is_symmetric=true`, `asymmetric_count=0` (1 memory entry × 1 wiki page symmetric link)
  - **R-B (Wiki → Memory reverse lookup)** 별도 sub-milestone (v0.13.4+ 후속)

### 2.4 검증 helper (제안)

| helper | 위치 | 검증 |
|---|---|---|
| `check_silent_failing_cycles.py` | `workflow-source/tests/check_silent_failing_cycles_v0_13_0.py` | N release 동안 drift prevention smoke 가 fail 한 적이 0 회 |
| `check_memory_index_utilization.py` | **v0.13.1 구현**: `workflow-source/tests/check_memory_index_telemetry.py` | 3 skill + dispatcher 의 opt-in 호출 ≥ baseline + by_source 분해 + error path 음성 예제 보존 |
| `check_self_recovering.py` | 신규 | drift 발견 → fix 까지 cycle ≤ 1 release |
| `tools/release_pipeline.py` enhancement | `release --apply` | changelog-gen / sync-maturity-matrix / docs-snapshot 자동 호출 |

## 3. Phase 12 close 와의 관계

### 3.1 Phase 12 마감 후 Phase 13 진입

Phase 12 의 close acceptance (P0/P1 진행 후 다음 단계):

- P0 3건 완료 (P0-1, P0-2, P0-3) ✅
- P1 3건:
  - P1-1: ADR-006 retrospective (full, scheduled 2026-07-16) — close 시점 필수
  - P1-2: Beta MCP stable 승격 로드맵 — *로드맵 자체* 완료 (실제 stable 승격은 Phase 13 의 sub-milestone)
  - P1-3: Drift 91 cycle 사례 분류 — 완료 ✅
- v0.11.25 stdio-sdk 정식 stable 승격 — 완료 ✅

### 3.2 Phase 13 kick-off 조건

다음 조건 모두 충족 시 Phase 13 kick-off:

- [ ] Phase 12 close acceptance 모두 충족
- [ ] 본 토픽 (north-star metric) 의 maintainer 승인
- [ ] `maturity_matrix.json` 에 `Phase 13` 필드 추가 (status: planned)
- [ ] `workflow_kit_roadmap.md` §1.1 의 미이행 4 항목 → Phase 13 entry 로 전환
- [ ] release `v0.13.0-beta` 첫 release 의 kick-off commit 작성

## 4. Risk / Open issues

1. **north-star metric 의 proxy 적합성**: silent_failing_cycles_count 는 drift prevention 도입 *이후* (v0.11.23+) 만 측정 가능. 그 이전 91 cycle 의 metric 은 추정치.
2. **memory_index 활용도 측정**: 3 skill 의 opt-in wiring 의 호출 횟수 측정은 *agent side* telemetry 가 필요. 현재 infra 부재.
3. **self-recovering 의 blast radius**: 자동 fix 가 잘못된 fix 를 emit 하면 production drift. dry-run + human-in-the-loop 옵션 필수.
4. **Phase 13 의 north-star 가 *운영 지능화* 가 맞는지**: maintainer 의 *전략적 우선순위* 에 따라 변경 가능. 본 토픽은 *제안*.

## 5. 인용 및 후속

- 2026-07-09 audit: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.3 P2-1
- Roadmap §1.1: [`../../../workflow-source/core/workflow_kit_roadmap.md`](../../../workflow-source/core/workflow_kit_roadmap.md)
- 본 P1-2 follow-up: [`mcp-beta-promotion-roadmap-2026.md`](mcp-beta-promotion-roadmap-2026.md)
- 본 P1-3 follow-up: [`drift-prevention-91-cycle-classification-2026.md`](drift-prevention-91-cycle-classification-2026.md)
- Phase 13 kick-off 시 본 토픽의 §2 acceptance criteria 를 roadmap §1.1 에 정식 반영.

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`../../../workflow-source/core/workflow_kit_roadmap.md`](../../../workflow-source/core/workflow_kit_roadmap.md)
