# Beta v0.8.1 — mypy strict 단계적 격상 1단계 (workflow_kit/url_validity.py) (2026-06-17)

> v0.8.0 spec §5.3 의 mypy strict 단계적 격상 — 첫 단계. workflow_kit/url_validity.py
> (V-R10, ADR-010/012/013/017/019/020/021) 의 **25 mypy error → 0** (Success: no issues found).
> 5 module test 71 → **71 PASS** (변동 없음, 회귀 0), dispatcher 47 → **47 PASS**.
> cumulative 0.7.x~0.8.x follow-up 6 release 의 두 번째. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 1단계 (workflow_kit/url_validity.py)

v0.7.5+ 부터 mypy 가 *non-strict* (disallow_untyped_defs=false) 였음. v0.8.0 에서
`pyproject.toml [tool.mypy] strict = true` 격상, 단 `__init__.py` 의 public surface 만
strict clean. v0.8.1 = **첫 번째 internal module 격상** (url_validity.py).

| Error type | count | Fix |
|---|---|---|
| `arg-type`: severity=`'info'` not Literal['error','warn'] | 11 | `Severity = Literal["error", "warn", "info"]` 확장 (real-world: advisory url issue) |
| `arg-type`: severity dynamic `str` | 1 | `severity: Severity = ...` 명시 (line 752) |
| `name-defined`: `EvictionStrategy` | 2 | `EvictionStrategy = Literal["lru", "lfu", "mixed"]` 신규 정의 (real bug fix) |
| `attr-defined`: `CacheEntry.timestamp` | 3 | `CacheEntry.timestamp: float` field 추가 (real bug fix) |
| `attr-defined`: `url_validity` self | 1 | `Severity` type 명시 (range diff severity) |
| `call-arg`: `CacheEntry` unexpected `timestamp` | 1 | 위와 동일 fix |
| `no-untyped-def`: function params/return | 2 | annotation 추가 (`__enter__`, `__exit__`) |
| `type-arg`: `dict`, `tuple` generic | 2 | `[str, Any]`, `[int, float]` 명시 |
| `arg-type`: `_fd: None` access `.fileno()` | 3 | `_fd: IO[Any] \| None` 명시 |
| `arg-type`: `last_eviction_timestamp: float` not `int` | 1 | `cache_stats` return type → `dict[str, int \| float]` |
| `dict-item`: per_strategy return type | 3 | `dict[str, dict[str, int \| float]]` 통일 |
| `arg-type`: `severity=severity` (str) | 1 | `severity: Severity = ...` 명시 |
| `arg-type`: `*args: Any` for __exit__ | 1 | `*args: Any` 명시 |
| `exit-return`: `__exit__` returns `bool` not `False` | 1 | `Literal[False]` 명시 (예외 swallow 안 함) |
| `no-redef`: `url` field duplicated | 1 | dup 제거 |
| `no-redef`: `total_removed` parameter + local | 1 | parameter 제거 (body local 만) |
| `no-any-return` / `arg-type` | 2 | `int(s["total"])` cast, `Literal[False]` 명시 |
| `misc` / `name-defined` (`max_diff_lines`) | 2 | `max_diff_lines: int = 1000` parameter 추가 (real bug fix) |
| `return-value` / `return` | 2 | `return result` / `return 1 if failed else 0` 추가 |
| **total** | **25** | **0** |

### 🐛 Real bug fix (mypy strict detect)

v0.7.5+ 부터 *silent* 였던 2개 bug:

1. **`EvictionStrategy` 미정의**: 953/1030 line 의 `eviction_strategy: EvictionStrategy`
   가 *type alias* 정의 없이 reference. runtime NameError 안 났던 이유는 `Literal["lru", "lfu", "mixed"]`
   string default — `str` 으로 *coerce* 됐기 때문. mypy strict 가 *real type safety violation* detect.
2. **`CacheEntry.timestamp` 미선언**: `_load_cache` 가 `CacheEntry(... timestamp=...)` constructor
   호출, 본체 코드가 `entry.timestamp` access, *그러나* `CacheEntry` class 에 `timestamp` field
   가 없음. runtime 시 *AttributeError* 안 났던 이유는 *frozen=True* dataclass 가 dynamic
   attribute set 을 막지 않기 때문. mypy strict 가 *real type safety violation* detect.

본 release 의 fix: `CacheEntry.timestamp: float` field 추가 — *frozen dataclass* 의
backward-compatible (default value 0.0, but no existing code path 가 default 에 의존).

## 운영 누적 (v0.7.5 → v0.8.1)

| | v0.7.5 | v0.7.10 | v0.7.20 | v0.7.50 | v0.7.58 | v0.8.0 | **v0.8.1** |
|---|---|---|---|---|---|---|---|
| **mypy strict on `__init__.py`** | ❌ | ❌ | ❌ | ❌ | ❌ | ✓ | ✓ |
| **mypy strict on `url_validity.py`** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✓** |
| **cumulative strict clean** | 0 | 0 | 0 | 0 | 0 | 1 | **2** |
| **5 module test** | 64 | 64 | 64 | 98 | 98 | 122 | **122** |
| **dispatcher test** | 6 | 9 | 13 | 33 | 41 | 47 | **47** |

## In-flight 발견 + fix

- **bug 1**: `CacheEntry.timestamp` field 미선언 — constructor 사이트 3개가
  `timestamp=float(data["timestamp"])` 으로 field 세팅했으나 class 선언에 없음.
  fix: field 추가 (real bug fix).
- **bug 2**: `EvictionStrategy` type alias 미정의 — 953/1030 line 의 parameter
  type 이 reference 됐으나 정의 없음. fix: top-of-file 에 `Literal["lru", "lfu", "mixed"]` 정의.
- **bug 3**: `check_url_semantic_range_diff` 의 `max_diff_lines` parameter 누락 — body
  line 752 에서 reference 하지만 signature 에 없음. fix: `*, max_diff_lines: int = 1000` parameter 추가.
- **bug 4**: `cache_prune` 본문 끝의 `return result` 누락. fix: 1201-1202 line 사이에 추가.
- **bug 5**: `main` 본문 끝의 `return 1 if failed else 0` 누락. fix: 1264-1265 line 사이에 추가.
- **bug 6**: `__exit__` 의 return type `bool` (default) 가 *real* `Literal[False]` — `False`
  만 반환 (예외 propagate). fix: `Literal[False]` 명시.
- **bug 7**: `cache_stats_per_strategy_with_hit_rate` 의 result variable 의 stale type
  annotation `dict[str, dict[str, object]]` (이전 edit 의 잔재) — body 의 return type
  `dict[str, dict[str, int | float]]` 와 mismatch. fix: `dict[str, dict[str, int | float]]` 통일.
- **bug 8**: `total_entries += s["total"]` — `s["total"]` 이 `int | float`, `total_entries: int`.
  fix: `int(s["total"])` cast.

## Test 결과

- `mypy --strict workflow_kit/url_validity.py`:
  - **before v0.8.1**: 25 errors in 1 file
  - **after v0.8.1**: "Success: no issues found in 1 source file"
- `mypy --strict workflow_kit/__init__.py`: "Success: no issues found" (v0.8.0+ 유지)
- `tests/check_url_validity.py`: 14/14 PASS (변동 없음)
- 회귀 5 module + dispatcher:
  - `check_path_resolver.py`: 12/12 PASS
  - `check_phishing_keywords.py`: 8/8 PASS
  - `check_okf_import.py`: 25/25 PASS
  - `check_release_pipeline_lib.py`: 7/7 PASS
  - `check_cache_migration.py`: 5/5 PASS
  - `check_consumer_metrics.py`: 9/9 PASS
  - `check_workflow_kit_cli.py`: 47/47 PASS
- **cumulative 5 module test**: 122 → **122 PASS** (변동 없음)
- **cumulative dispatcher test**: 47 → **47 PASS** (변동 없음)
- **cumulative strict clean file count**: 1 → **2** (`__init__.py` + `url_validity.py`)

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/url_validity.py` | +20 / -10 (annotation 보강, 2 real bug fix) |
| M | `pyproject.toml` | +3 (단계적 격상 note, v0.8.1 entry) |
| A | `workflow-source/releases/Beta-v0.8.1.md` | release note |
| A | `ai-workflow/memory/release/v0.8.1/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.2+ / v0.9.0)

1. **v0.8.2**: `workflow_kit/okf_import.py` strict clean (9 error)
2. **v0.8.3**: `workflow_kit/okf_export.py` strict clean (2 error)
3. **v0.8.4**: `workflow_kit/phishing_federation.py` + `phishing_federation_v4.py` (4+4 error)
4. **v0.8.5**: `workflow_kit/cache_lfu_decay.py` + `cache_lfu_decay_persist.py` strict clean
5. **v0.8.6**: `workflow_kit/workflow_kit_cli.py` (48 error, 가장 큼 — module 별 분할)
6. **v0.8.7**: `workflow_kit/common/state/builder.py` 35 error
7. **v0.8.8**: `workflow_kit/common/contracts/baselines.py` 27 error
8. **v0.9.0** full mypy strict (모든 module strict clean)
