# Beta v0.8.7 — mypy strict 단계적 격상 7단계 (v_r13_commit_diff + cache_analytics*) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 7단계. `v_r13_commit_diff.py` (V-R13 layer 2
> commit-level diff, ADR-019) + `cache_analytics.py` (cache analytics, ADR-021) +
> `cache_analytics_trend_chart.py` (ASCII trend chart) 의 **13 mypy error → 0**. 5 module
> 122 PASS, dispatcher 47 PASS. cumulative 0.7.x~0.8.x follow-up 12 release 의 여덟 번째.
> **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 7단계 (3 file, 13 error)

| File | count | Fix |
|---|---|---|
| `v_r13_commit_diff.py` | 11 | 5 `requests_get` param + 2 nested def + 2 cast + 1 `Callable` import |
| `cache_analytics.py` | 1 | `int(per_strategy[s]["size"])` cast |
| `cache_analytics_trend_chart.py` | 1 | `list[dict]` → `list[dict[str, Any]]` |
| **total** | **13** | **0** |

## 운영 누적 (v0.7.5 → v0.8.7)

| | v0.7.5 | v0.8.0 | v0.8.6 | **v0.8.7** |
|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 10 | **13** |
| **5 module test** | 64 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | **47** |

## In-flight 발견 + fix

- (없음) — 단순 annotation 추가 (real bug fix 없음)

## Test 결과

- `mypy --strict` (3 file):
  - **before v0.8.7**: 13 errors
  - **after v0.8.7**: "Success: no issues found"
- `mypy --strict` (cumulative, 26 file): 8 stray error (v0.8.8 follow-up)
- 회귀 5 module + dispatcher: 변동 없음
- **cumulative strict clean file count**: 10 → **13** (+ v_r13_commit_diff + cache_analytics + cache_analytics_trend_chart)

## 변경 파일 (5 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/v_r13_commit_diff.py` | +7 / -2 (annotation + cast + import) |
| M | `workflow_kit/cache_analytics.py` | +1 / -1 (int cast) |
| M | `workflow_kit/cache_analytics_trend_chart.py` | +1 / -1 (annotation + import) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.7 entry) |
| A | `workflow-source/releases/Beta-v0.8.7.md` | release note |
| A | `ai-workflow/memory/release/v0.8.7/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.8+ / v0.9.0)

1. **v0.8.8**: 4 file strict clean: `upgrade_diff.py` (1) + `bitbucket_v2.py` (4) + `lfu_integration.py` (1) + `cache_size_compare.py` (2)
2. **v0.8.9**: `common/state/builder.py` 35 error
3. **v0.8.10**: `common/contracts/baselines.py` 27 error
4. **v0.9.0** full mypy strict
