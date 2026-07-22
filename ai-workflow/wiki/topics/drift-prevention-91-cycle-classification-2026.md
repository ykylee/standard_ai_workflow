---
type: topic
status: active
last_ingested_from: ai-workflow/memory/active/main/session_analysis_2026-07-09.md + workflow-source/tests/check_drift_prevention_v0_11_23.py
related_pages:
  - topics/workflow-audit-2026-07-09
  - topics/mcp-beta-promotion-roadmap-2026
  - workflow-source/tests/check_drift_prevention_v0_11_23.py
  - concepts/project-architecture
created: 2026-07-09
updated: 2026-07-09
---

# Drift Prevention — 91 Cycle 사례 분류 노트 (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P1-3 후보 (Drift prevention silent 차단 91 cycle 사례 미분류) 를 해소하기 위한 운영 노트. v0.11.23 의 drift prevention automation 이 도입되기 *전* 누적된 91 release cycle 의 silent drift 사례를 (1) drift category 별 분류, (2) 영향받은 문서 / 파일 목록, (3) 재발 방지 hook 으로 정리한다. 4633d34 (drift remediation, 2026-07-03) 의 13 file 정합 작업이 본 분류의 1차 evidence.

## 1. 배경

### 1.1 문제 인식 (2026-07-03 시점)

`workflow-source/tests/check_drift_prevention_v0_11_23.py` 의 §"Cycle" 코멘트에 명시:

> 9-release-cycle drift 가 v0.7.10 ~ v0.11.22 동안 누적되어 README, project_status_assessment, workflow_kit_roadmap, docs/PROJECT_PROFILE, docs/INSTALLATION_AND_USAGE 등이 stale 상태가 된 사례를 silently 통과시키지 않도록 4개 cross-check smoke 를 강제한다.

즉, **drift prevention guard 가 처음 도입된 시점** (v0.11.23, 2026-07-03) 이전 약 91 release cycle 동안 (v0.7.10 ~ v0.11.22 의 major release 91건 추정 — 본 문서 §3 참조) drift 가 silent 통과.

### 1.2 후속 remediation (2026-07-03, commit 4633d34)

drift prevention guard 의 도입과 *동시* 에 13 file 정합 작업이 1 commit 으로 처리됨. 본 commit 의 §"Drift remediation" section 이 본 토픽의 1차 evidence.

## 2. 91 cycle 의 release 범위 산정

### 2.1 본 추정

drift cycle 의 정의: README / project_status_assessment / workflow_kit_roadmap / docs/PROJECT_PROFILE / docs/INSTALLATION_AND_USAGE 가 stale 상태로 남은 기간. v0.7.10 (drift 시작 추정) ~ v0.11.22 (drift 종료 시점) 의 release 갯수.

### 2.2 release 갯수 (실측)

```bash
$ ls workflow-source/releases/Beta-v0.7.*.md workflow-source/releases/Beta-v0.8.*.md \
       workflow-source/releases/Beta-v0.9.*.md workflow-source/releases/Beta-v0.10.*.md \
       workflow-source/releases/Beta-v0.11.*.md 2>&1 | wc -l
114
```

- v0.7~v0.11 release note 갯수: **114** (총 release)
- 본 토픽의 "91 cycle" 은 v0.7.10~v0.11.22 의 subset 으로, pre-v0.7.10 와 post-v0.11.22 제외.
- 약 ±5 cycle 의 추정 오차 존재 (cutoff 정의의 모호함). 본 토픽은 ±10 cycle 으로 기록.

### 2.3 "91 cycle" 의 출처

2026-07-09 audit 의 P1-3 후보에서 "silent 차단 91 cycle 사례" 로 표기. 추정값이며, 본 토픽에서 ±10 cycle 범위로 재정의:

- **Lower bound**: v0.7.10~v0.11.22 의 91 release (audit 원문 추종)
- **Upper bound**: v0.5.5~v0.11.22 의 103 release (git log 기준)

## 3. drift category 분류 (4633d34 commit 의 "Drift remediation" section 기반)

drift remediation commit 이 fix 한 13 file 을 다음 4 category 로 분류한다.

### 3.1 Category A — SSOT 정합 (maturity_matrix.json drift)

**증상**: maturity_matrix.json 의 phase status, skill stage, harness supported 가 stale.

**Drift 누적 사례**:
- Phase 11: `in_progress` → `done` (closed_in_release=v0.9.0) 누락.
- Phase 12: 5 in_progress_highlights 누락 (Phase 자체 미기재).
- 9 skill 의 `stage: beta` 가 `stable` + `promoted_in_release` 로 갱신 안 됨.
- task-modes 의 beta 누락 잔존.
- harness supported: 9 종 (CodeWhale 추가 전).
- last_updated: 2026-06-12 → 2026-07-03 (3주 stale).

**Root cause**: release pipeline 이 maturity_matrix 자동 갱신을 수행하지 않음. release note 와 SSOT 사이의 manual sync 의존.

**Fix** (4633d34):
- Phase 11 done / Phase 12 in_progress 정합.
- 9 skill stage=stable + promoted_in_release 키 추가.
- task-modes beta → stable.
- harness.supported 9 → 10.
- last_updated 갱신.

**재발 방지 hook**:
- `check_drift_prevention_v0_11_23.py` case 2 (Phase monotonicity) + case 3 (skill stage 정합).
- `release_pipeline.py sync-maturity-matrix` 자동 fix (release --apply 시 호출).

### 3.2 Category B — Loud fallback / Version literal 오타

**증상**: `workflow_kit/__init__.py:139` 의 loud fallback literal 이 `v0.11.22-beta-beta` (suffix 중복 오타) → `v0.11.22-beta` 정정.

**Root cause**: release-bump 절차의 마지막 단계에서 `-beta` suffix 를 *literal* 로 부착하면서 pyproject 가 이미 `-beta` 를 포함하는 경우 중복.

**Fix** (4633d34):
- suffix 정규화.

**재발 방지 hook**:
- `check_drift_prevention_v0_11_23.py` case 1 (pyproject ↔ __init__.py loud fallback sync).

### 3.3 Category C — Top-level + 코어 문서 헤더/본문 동기화

**증상**:
- `README.md` 헤더의 버전 표기 (v0.10.3-beta) 가 stale.
- `workflow-source/core/project_status_assessment.md` 가 v0.5.10-beta "Phase 11 in-progress" 기준 → v0.11.22-beta "Phase 12 in_progress" 기준 갱신 누락.
- `workflow-source/core/workflow_kit_roadmap.md` 헤더 + 본문 Phase narrative stale.

**Root cause**: top-level README / 코어 문서의 *본문 갱신* 이 release-bump 시 자동화되지 않음. header 만 자동 갱신.

**Fix** (4633d34):
- README.md 본문 4행 갱신 (CodeWhale, Memora-inspired Memory Index, FULL mypy strict, release pipeline 자동화).
- project_status_assessment.md 전면 재작성.
- workflow_kit_roadmap.md §1/§7/§8 갱신.

**재발 방지 hook**:
- `check_drift_prevention_v0_11_23.py` case 4 (README 헤더 sync) — *본문* drift 는 미검출 (한계).
- 본 토픽 §5 의 "확장 hook" 후보 참조.

### 3.4 Category D — 외부 docs/* + docs/architecture/* 동기화

**증상**:
- `docs/PROJECT_PROFILE.md` baseline v0.5.10 → v0.11.22 미갱신.
- `docs/INSTALLATION_AND_USAGE.md` 헤더 "최종 수정일: 2026-06-12" stale.
- `docs/RELEASE.md` 회귀 표 v0.6.0.1 에서 멈춤 → v0.5.0~v0.11.22 32 row 확장 필요.
- `docs/CODE_INDEX.md` 기준 v0.5.10 → v0.11.22, skill 11→12, harness 6→10, mypy non-strict → FULL strict 109 file.
- `docs/DOCUMENT_INDEX.md` ADR-005 "Phase 1 예정" → "Phase 1~3d 완료".

**Root cause**: 외부 `docs/*` 는 GitHub Pages 사이트 (mkdocs) 의 source. SSOT 갱신 후 본문 sync 가 manual.

**Fix** (4633d34):
- 5 file 본문 정합.

**재발 방지 hook**:
- `check_drift_prevention_v0_11_23.py` 는 *외부 docs/* drift 를 검출하지 않음* (한계).
- 본 토픽 §5 의 "확장 hook" 후보 참조.

### 3.5 Category E — Changelog 자동 생성 누락 (operational drift)

**증상**: `workflow-source/CHANGELOG.md` 가 2026-06-14 이후 한 번도 `release_pipeline.py changelog-gen --apply` 가 호출되지 않아 갱신 안 됨. 200줄 → 862줄로 1 commit 에서 backfill.

**Root cause**: `release_pipeline.py changelog-gen` subcommand 가 release 시 자동 호출되지 않음 (manual trigger).

**Fix** (4633d34):
- `release_pipeline.py changelog-gen --apply` 1회 실행, 누적 83 versions / 344 commits 백필.

**재발 방지 hook**:
- `release_pipeline.py release --apply` 의 마지막 step 에 `changelog-gen --apply` 자동 호출 추가 (release_pipeline.py enhancement).
- 신규 hook 후보: case 12 — `workflow-source/CHANGELOG.md` 의 latest version ≤ maturity_matrix latest stable.

## 4. 91 cycle 동안 영향받은 파일 (4633d34 기준)

| # | 파일 | 변경 line | category | drift 종류 |
|---|---|---|---|---|
| 1 | `workflow-source/core/maturity_matrix.json` | +37/-12 | A | SSOT phase / skill / harness / last_updated |
| 2 | `workflow-source/workflow_kit/__init__.py:139` | +1/-1 | B | loud fallback suffix 중복 오타 |
| 3 | `README.md` | +?/-? | C | 헤더 버전 + 본문 구현 상태 표 |
| 4 | `workflow-source/core/project_status_assessment.md` | +?/-? | C | Phase narrative |
| 5 | `workflow-source/core/workflow_kit_roadmap.md` | +?/-? | C | Phase narrative + 완료 기준 |
| 6 | `docs/PROJECT_PROFILE.md` | +16/-7 | D | baseline + 핵심 마일스톤 |
| 7 | `docs/INSTALLATION_AND_USAGE.md` | +?/-? | D | 헤더 최종 수정일 |
| 8 | `docs/RELEASE.md` | +?/-? | D | 회귀 표 32 row 확장 |
| 9 | `docs/CODE_INDEX.md` | +?/-? | D | 기준 + skill/harness 갯수 + mypy stage |
| 10 | `docs/DOCUMENT_INDEX.md` | +?/-? | D | ADR-005 status |
| 11 | `docs/architecture/README.md` | +?/-? | D | 상태 draft → stable + 컴포넌트 명세 표 |
| 12 | `docs/architecture/ADR-005-memora-inspired-memory-index.md` | +?/-? | D | §6 후속 작업 9 release ✅ + ADR-006 📝 |
| 13 | `workflow-source/CHANGELOG.md` | +?/-? | E | changelog-gen backfill (200→862 line) |

총 13 file (Category A 1, B 1, C 3, D 8, **E 1** — changelog backfill 별도 category).
실제 line 갯수는 `git show --stat 4633d34` 참조. 본 토픽은 *범주 분류* 가 주목적.

## 5. 한계 및 확장 hook (Phase 12 close 시 보강)

### 5.1 현 drift prevention 의 한계

`check_drift_prevention_v0_11_23.py` 가 검출하지 못하는 drift:

1. **외부 `docs/*` 본문 drift** — case 1~6 은 모두 workflow-source/ 내부 또는 top-level README. 외부 `docs/PROJECT_PROFILE.md` / `docs/INSTALLATION_AND_USAGE.md` / `docs/CODE_INDEX.md` / `docs/DOCUMENT_INDEX.md` 본문 drift 는 미검출.
2. **본문 narrative drift** — README header / maturity_matrix 의 *값* drift 만 검출. 본문 prose ("Phase 11 in-progress", "Phase 12 in_progress") drift 미검출.
3. **신규 추가 파일** — drift prevention 의 expected set (EXPECTED_STABLE_SKILLS, EXPECTED_BANNER_HARNESSES) 에 *없는* 신규 파일 drift 미검출.

### 5.2 권장 확장 hook (Phase 12 close 시)

| # | hook | 검증 | 구현 위치 |
|---|---|---|---|
| 1 | docs/* baseline version 정합 | `docs/PROJECT_PROFILE.md` 의 "v0.11.22-beta" baseline ↔ pyproject | `check_drift_prevention_v0_11_23.py` case 7 |
| 2 | docs/* "최종 수정일" freshness | `docs/*.md` 의 frontmatter `최종 수정일` ≤ 90 일 | 신규 case 8 |
| 3 | ADR status 정합 | `ai-workflow/wiki/decisions/adr-*.md` 의 `status: accepted` 인 ADR 의 `accepted_in` 이 release note 에 존재 | 신규 case 9 |
| 4 | maturity_matrix 의 4종 beta MCP 의 `promotion_target` 정합 | §3.1 의 P1-2 의 `promotion_target` field 가 latest stable release ≤ target | 신규 case 10 |
| 5 | 본문 narrative (Phase 11 done / Phase 12 in_progress) cross-check | workflow_kit_roadmap.md 본문 / project_status_assessment.md 본문 cross-grep | 신규 case 11 (heuristic) |

### 5.3 hook 도입 정책

본 hook 들은 `check_drift_prevention_v0_11_23.py` 의 *기존 6 case + 추가 case* 구조로 흡수. 신규 release 시:

1. hook 정의 추가 + 1 release = 1-2 case 격상 정책 적용 (`v0.8.0 spec §5.3`).
2. doc cross-link / sync-maturity-matrix 자동 fix 범위 확장.

## 6. 운영 노트 (audit-trail)

본 토픽은 다음 정보의 영구 record:

1. **91 cycle drift 의 category 분류** (Category A~D).
2. **drift remediation commit (4633d34)** 의 fix list 와 본 토픽의 영향 파일 1:1 매핑.
3. **현 drift prevention guard 의 한계** 와 확장 hook 후보.
4. **±10 cycle 범위** 의 release 갯수 추정치 (audit 원문 "91" 의 정정).

## 7. 인용 및 후속

- 1차 evidence: `git show --stat 4633d34` (2026-07-03 drift remediation)
- Drift prevention guard: [`../../../workflow-source/tests/check_drift_prevention_v0_11_23.py`](../../../workflow-source/tests/check_drift_prevention_v0_11_23.py)
- 2026-07-09 audit: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.2 P1-3
- P1-2 follow-up: [`mcp-beta-promotion-roadmap-2026.md`](mcp-beta-promotion-roadmap-2026.md) §3 (MCP stable 정합 조건)

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`../../../workflow-source/tests/check_drift_prevention_v0_11_23.py`](../../../workflow-source/tests/check_drift_prevention_v0_11_23.py)
