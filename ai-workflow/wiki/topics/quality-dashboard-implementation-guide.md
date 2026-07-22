---
type: topic
status: active
last_ingested_from: ai-workflow/memory/archive/2026-07-22/main/session_analysis_2026-07-09.md + workflow-source/core/maturity_matrix.json
related_pages:
  - topics/workflow-audit-2026-07-09
  - topics/phase-13-definition-north-star
  - topics/drift-prevention-91-cycle-classification-2026
  - workflow-source/core/maturity_matrix.json
created: 2026-07-09
updated: 2026-07-09
---

# Quality Dashboard 구현 가이드 (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P2-3 후보 (Quality dashboard 미구현) 를 해소하기 위한 구현 가이드. 본 프로젝트의 운영 지표 (mypy trend / drift count / skill maturity / memory_index hit rate / smoke 누적) 를 단일 surface 에 시각화하는 dashboard 의 설계 가이드. 본 가이드는 Phase 13 의 sub-milestone 으로 추진되며, 본 토픽은 *구현 청사진* 만 정의.

## 1. Dashboard 의 목적

### 1.1 의도

운영자가 1 화면에서 다음을 한눈에 파악:

1. **drift 발생 여부 + 누적 추세**
2. **skill / MCP maturity 분포 + promotion 진행도**
3. **memory_index 활용도**
4. **smoke 누적 + 실패 추세**
5. **release cycle 누적 (recent_done_items 의 시각화)**

### 1.2 비대상 (Out of scope)

- 외부 consumer 용 dashboard (외부 공개 시 별도 ADR)
- 실시간 streaming (snapshot 기반; Phase 13 AC3 의 self-recovering 후속)

## 2. Dashboard 의 5 panel

### 2.1 Panel 1 — Drift Prevention Status

**출처**: `check_drift_prevention_v0_11_23.py` 결과 + 91 cycle 분류 (P1-3 토픽).

**시각화**:
- 6 case 의 PASS/FAIL 상태 (라벨 + 색상)
- last_updated ↔ HEAD commit date 의 delta (gauge)
- 누적 silent_failing_cycles_count (number) — Phase 13 AC1 의 north-star

**data source**:
- `workflow-source/core/maturity_matrix.json` (last_updated, skill stage)
- `workflow_kit/__init__.py` (loud fallback version)
- git log (HEAD commit date)

### 2.2 Panel 2 — Skill + MCP Maturity Distribution

**출처**: `maturity_matrix.json.skills` + `.mcp_tools`.

**시각화**:
- bar chart: stable / beta / alpha 분포 (skill 12종 + MCP 12종 = 24)
- line chart: 최근 10 release 동안 stable 비율 추세
- table: stable beta alpha 항목별 detail

**data source**: maturity_matrix.json (전체 key)

### 2.3 Panel 3 — Memory Index Utilization

**출처**: `ai-workflow/memory/active/memory_index/entries/*.json` + opt-in wiring 호출 카운트.

**시각화**:
- number: total entries (현재 7+)
- heatmap: cue_anchors 의 frequency (top 20)
- line chart: cumulative entries over time
- number: hit rate (session-start / doc-sync / backlog-update 의 opt-in 호출 hit / total)

**data source**: memory_index/entries/*.json + telemetry (Phase 13 AC2)

### 2.4 Panel 4 — Smoke Accumulation Trend

**출처**: `workflow-source/tests/check_*.py` 의 누적 PASS 갯수.

**시각화**:
- number: cumulative smoke count (현재 200+)
- line chart: 매 release 의 smoke 누적 추세
- number: recent release 의 smoke fail 갯수

**data source**: 각 release note (`workflow-source/releases/Beta-v0.*.md`) 의 `accumulated_smoke` field.

### 2.5 Panel 5 — Recent Release Cycle (state.json.recent_done_items 시각화)

**출처**: `ai-workflow/memory/active/state.json.session.recent_done_items`.

**시각화**:
- timeline: 최근 10 release 의 요약 (commit hash + version + 핵심 변경)
- table: recent_done_items 의 full text (expandable)

**data source**: state.json.

## 3. 구현 청사진

### 3.1 데이터 수집 (read-only)

신규 module: `workflow_kit/common/dashboard_data.py`

```python
def collect_dashboard_snapshot(workspace_root: Path) -> DashboardSnapshot:
    """5 panel 의 data 를 1 dict 로 수집. read-only, atomic."""
    return {
        "drift_prevention": collect_drift_prevention(...),
        "maturity": collect_maturity_distribution(...),
        "memory_index": collect_memory_index(...),
        "smoke_trend": collect_smoke_trend(...),
        "recent_releases": collect_recent_releases(...),
    }
```

CLI: `python -m workflow_kit.cli dashboard --json` (단일 read-only subcommand).

### 3.2 시각화 (markdown + 정적 HTML)

**Option A — markdown 표** (기본):

```bash
python -m workflow_kit.cli dashboard --format markdown > ai-workflow/dashboard/snapshot.md
```

장점: git diff friendly, wiki / docs 에 포함 가능.

**Option B — 정적 HTML** (advanced):

`tools/generate_dashboard.py` 가 markdown + Chart.js 의 정적 HTML 1 page emit. GitHub Pages 에 publish 가능.

장점: 시각적. 단점: HTML 빌드 / publish 인프라 필요.

### 3.3 자동 emit 시점

1. **release --apply 시**: `release_pipeline.py` 의 마지막 step 에 `dashboard --format markdown --output ai-workflow/dashboard/snapshot.md` 호출 추가.
2. **drift prevention smoke fail 시**: `tools/release_pipeline.py sync-maturity-matrix` 가 fix 후 dashboard 갱신.
3. **manual**: maintainer 의 `python -m workflow_kit.cli dashboard --json` 호출.

## 4. acceptance criteria (제안)

| AC | 조건 |
|---|---|
| AC1 | `python -m workflow_kit.cli dashboard --json` 가 5 panel 의 data 를 1 dict 로 emit |
| AC2 | dashboard 의 5 panel 모두 *실제 data* (fixture 아님) 기반 |
| AC3 | release --apply 시 dashboard snapshot 자동 갱신 |
| AC4 | snapshot 의 last_updated ≤ release commit date |

## 5. Risk / Open issues

1. **telemetry 부재**: memory_index hit rate 측정에 agent side telemetry 필요 (Phase 13 AC2 의 인프라).
2. **build time**: 5 panel data 수집이 1~3초 소요 예상. CI 내 추가 step 으로 적합한 수준.
3. **data staleness**: snapshot 기반이므로 마지막 release 이후 drift 발생 시 dashboard 가 stale. release 자동 emit 으로 mitigation.
4. **외부 공개 시**: dashboard 가 운영 metric 노출 → PII / 보안 검토 필요. 본 가이드 범위 외.

## 6. 적용 일정 (제안)

| sub-milestone | release | acceptance |
|---|---|---|
| `dashboard_data.py` + CLI `--json` | v0.13.0 | 5 panel data 1 dict emit |
| dashboard markdown snapshot | v0.13.1 | release --apply 시 자동 emit |
| dashboard 정적 HTML | v0.13.2 | GitHub Pages publish 옵션 |

Phase 13 의 sub-milestone 으로 통합.

## 7. 인용 및 후속

- 2026-07-09 audit: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.3 P2-3
- 본 P1-3 follow-up: [`drift-prevention-91-cycle-classification-2026.md`](drift-prevention-91-cycle-classification-2026.md) (Panel 1 data source)
- 본 P2-1 follow-up: [`phase-13-definition-north-star.md`](phase-13-definition-north-star.md) (Panel 3 data source)
- 본 P0-3 follow-up: [`../../../ai-workflow/memory/active/memory_index/README.md`](../../../ai-workflow/memory/active/memory_index/README.md) (Panel 3 data)

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`phase-13-definition-north-star.md`](phase-13-definition-north-star.md)
- [`drift-prevention-91-cycle-classification-2026.md`](drift-prevention-91-cycle-classification-2026.md)
