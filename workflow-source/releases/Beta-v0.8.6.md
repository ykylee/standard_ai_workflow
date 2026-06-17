# Beta v0.8.6 — mypy strict 단계적 격상 6단계 (workflow_kit_cli.py) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 6단계. `workflow_kit_cli.py` (28 subcommand
> dispatcher, v0.7.5+ ADR-013) 의 **44 mypy error → 0** (가장 큰 module). 5 module 122 PASS,
> dispatcher 47 PASS. cumulative 0.7.x~0.8.x follow-up 11 release 의 일곱 번째.
> **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 6단계 (workflow_kit_cli.py)

| Error type | count | Fix |
|---|---|---|
| `untyped-decorator` (@register cascade) | 10+ | `register` decorator return type 명시 |
| `type-arg` (dict generic) | 4 | `dict[str, Any]` 명시 |
| `arg-type` (Literal mismatch) | 3 | `cast(Literal[...], ...)` |
| `no-any-return` (mod.main()) | 2 | `cast(int, mod.main())` |
| `no-untyped-def` (`**kwargs`) | 1 | `**kwargs: Any` |
| `no-untyped-def` (no return) | 1 | `return 2` 추가 |
| `dict[str, object]` access | 4 | `dict[str, Any]` 변경 |
| **total** | **44** | **0** |

### 🐛 Real bug fix (mypy strict detect)

v0.7.5+ 부터 *silent* 였던 1개 bug:

- **`@register(name)` decorator 의 *untyped* — 모든 subcommand handler 가 untyped cascade**:
  fix: `register(name: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]`
  명시 → *untyped-decorator* error 10+ fix (1 fix로 10+ error 제거, cascade 효과).

## 운영 누적 (v0.7.5 → v0.8.6)

| | v0.7.5 | v0.8.0 | v0.8.5 | **v0.8.6** |
|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 9 | **10** |
| **5 module test** | 64 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | **47** |
| **dispatcher subcommand** | 0 | 28 | 28 | **28** |

## In-flight 발견 + fix

- (위 table 외) `cast(Literal[...], ...)` 3개: cosmetic, runtime behavior 동일.

## Test 결과

- `mypy --strict workflow_kit/workflow_kit_cli.py`:
  - **before v0.8.6**: 44 errors in 1 file
  - **after v0.8.6**: "Success: no issues found in 1 source file"
- `mypy --strict` (10 file cumulative): 13 stray error (cache_analytics, cache_analytics_trend_chart, v_r13_commit_diff)
- 회귀 5 module + dispatcher: 변동 없음
- **cumulative strict clean file count**: 9 → **10** (+ workflow_kit_cli.py)

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/workflow_kit_cli.py` | +25 / -10 (annotation + cast + return 추가) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.6 entry) |
| A | `workflow-source/releases/Beta-v0.8.6.md` | release note |
| A | `ai-workflow/memory/release/v0.8.6/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.7+ / v0.9.0)

1. **v0.8.7**: `v_r13_commit_diff.py` (11 error) + `cache_analytics.py` (1) + `cache_analytics_trend_chart.py` (1)
2. **v0.8.8**: `common/state/builder.py` 35 error
3. **v0.8.9**: `common/contracts/baselines.py` 27 error
4. **v0.9.0** full mypy strict
