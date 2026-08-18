---
type: meta
status: draft
r9_skip: true
title: Wiki Maintainability Score Dashboard
description: 6 dim 별 0.0~5.0 점수 + overall grade. `wk score-wiki-maintainability --emit-dashboard` 자동 산출.
last_touched: 2026-08-18
---

# Wiki Maintainability Score Dashboard (v0.7.1, 2026-06-13)

> Generated: 2026-08-18T12:03:35
> 6 dim 별 0.0~5.0 점수 + overall grade. 자동 산출 — `wk score-wiki-maintainability --emit-dashboard`

## Overall

**Overall Score**: 4.71 / 5.0 — **Grade A**

| Dim | Score | Bar |
|---|---|---|
| Coverage | 4.22 / 5.0 | `████████████████░░░░` |
| Freshness | 5.0 / 5.0 | `████████████████████` |
| Discoverability | 5.0 / 5.0 | `████████████████████` |
| Cross-ref | 4.04 / 5.0 | `████████████████░░░░` |
| Lifecycle | 5.0 / 5.0 | `████████████████████` |
| Operational | 5.0 / 5.0 | `████████████████████` |

## Detail

### Coverage (4.22 / 5.0)
- L1 wiki page with concept/topic/pattern + last_ingested_from marker
- + frontmatter `status: active` 비율
- Total: 45 / Active: 38 (84%)

### Freshness (5.0 / 5.0)
- drift (updated > 7일 vs code mtime) 비율의 (1 - ratio)
- Total: 34 / Drift: 0 (0%)

### Discoverability (5.0 / 5.0)
- vault L2 page with 본문 ≥ 200자 비율 (frontmatter-only 제외)
- Total: 4 / Searchable: 4 (100%)

### Cross-ref (4.04 / 5.0)
- L1 wiki with related_pages ≥ 2 비율
- Total: 83 / Linked: 67 (80%)

### Lifecycle (5.0 / 5.0)
- vault L2 page 의 `last_touched` 신선도 비율 (emit 이 멈추면 하락 — L2 계층 방치 탐지)
- Total: 4 / Reviewed: 4 (100%)

### Operational (5.0 / 5.0)
- wiki 관련 smoke test PASS 비율
- Total: 11 / Passed: 11 (100%)

## Grade 기준

| Grade | Score |
|---|---|
| A | ≥ 4.5 |
| B | ≥ 4.0 |
| C | ≥ 3.5 |
| D | ≥ 3.0 |
| F | < 3.0 |

## 다음 개선 (전체 점수 < 4.5 시)

- **Coverage < 4.5**: v0.7.0+ step 의 concept page 추가
- **Freshness < 4.5**: drift >= 7일 page 의 last_ingested_from 갱신
- **Discoverability < 4.5**: vault L2 sources/ 의 `<needs content>` 해소 (emit_wiki_l2_body.py --apply)
- **Cross-ref < 4.5**: related_pages ≥ 2 page 추가
- **Lifecycle < 4.5**: vault L2 status: draft → reviewed 자동 갱신
- **Operational < 4.5**: smoke test 신규 추가 또는 회귀 fix

## Trend Over Time (v0.7.1+)

| Commit | Subject | Overall | Grade |
|---|---|---|---|
| `0052da1` | v0.7.0 step 7 (Extension System) | 3.11 | D |
| `021ec16` | v0.7.0 wiki maintainability (5 concept + L2 emit + | 3.70 | D |
| `7a4dbae` | v0.7.0 L2 30 page emit (L1 1:1) | 3.70 | D |
| `49dfc78` | v0.7.0 score metric + dashboard | 3.70 | D |
| `c72bdc3` | v0.7.0 L2 499 page metadata-only emit | 4.66 | A |
| `f09034d` | v0.7.1 (follow-up 4건 + wiki 개선 4건) | 4.66 | A |
| `bad14d8` | v0.7.1 (current HEAD) | 4.67 | A |
| `3bffba3` | v0.7.2 (sub-cat + 4종 본 구현) | 4.66 | A |
| `be49e0f` |  | 4.67 | A |
| `1818dd6` |  | 4.67 | A |
| `29af65d` |  | 4.68 | A |
| `29af65d` |  | 4.68 | A |
| `29af65d` |  | 4.68 | A |
| `29af65d` |  | 4.68 | A |
| `29af65d` |  | 4.68 | A |
| `29af65d` |  | 4.68 | A |
| `9351e17` |  | 4.68 | A |
| `9351e17` |  | 4.68 | A |

자동 추출: `wk score-wiki-trend --show`
history: `workflow-source/workflow_kit/tools/.score_history.jsonl` (v0.7.1+ 누적)


## References

- tool: `workflow-source/workflow_kit/tools/score_wiki_maintainability.py`
- tool: `workflow-source/workflow_kit/tools/score_wiki_trend.py` (v0.7.1+, trend over time)
- helper: `workflow-source/workflow_kit/tools/emit_wiki_l2_body.py` (L2 emit)
- smoke: `workflow-source/tests/check_wiki_drift.py` (drift)
- 6 dim 정의: 본 dashboard §Score 기준
