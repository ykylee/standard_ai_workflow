# Wiki Maintainability Score Dashboard (v0.7.0, 2026-06-13)

> Generated: 2026-06-13T22:35:39
> 6 dim 별 0.0~5.0 점수 + overall grade. 자동 산출 — `python3 workflow-source/tools/score_wiki_maintainability.py --emit-dashboard`

## Overall

**Overall Score**: 4.66 / 5.0 — **Grade A**

| Dim | Score | Bar |
|---|---|---|
| Coverage | 4.13 / 5.0 | `████████████████░░░░` |
| Freshness | 4.2 / 5.0 | `████████████████░░░░` |
| Discoverability | 5.0 / 5.0 | `████████████████████` |
| Cross-ref | 4.63 / 5.0 | `██████████████████░░` |
| Lifecycle | 4.97 / 5.0 | `███████████████████░` |
| Operational | 5.0 / 5.0 | `████████████████████` |

## Detail

### Coverage (4.13 / 5.0)
- L1 wiki page with concept/topic/pattern + last_ingested_from + status: active
- Total: 23 / Active: 19 (82%)

### Freshness (4.2 / 5.0)
- drift (updated > 7일 vs code mtime) 비율의 (1 - ratio)
- Total: 25 / Drift: 4 (16%)

### Discoverability (5.0 / 5.0)
- vault L2 page with 본문 ≥ 200자 비율 (frontmatter-only 제외)
- Total: 539 / Searchable: 539 (100%)

### Cross-ref (4.63 / 5.0)
- L1 wiki with related_pages ≥ 2 비율
- Total: 41 / Linked: 38 (92%)

### Lifecycle (4.97 / 5.0)
- vault L2 page with status: reviewed 비율
- Total: 539 / Reviewed: 536 (99%)

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

## References

- tool: `workflow-source/tools/score_wiki_maintainability.py`
- helper: `workflow-source/tools/emit_wiki_l2_body.py` (L2 emit)
- smoke: `workflow-source/tests/check_wiki_drift.py` (drift)
- 6 dim 정의: 본 dashboard §Score 기준
