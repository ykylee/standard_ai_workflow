# Beta v0.8.4 — mypy strict 단계적 격상 4단계 (phishing_federation + v4) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 4단계. `phishing_federation.py` + `phishing_federation_v4.py`
> (V-R11 phishing URL federation, ADR-023) 의 **8 mypy error → 0** (각 file 4).
> *real bug fix*: TypedDict 으로 inner dict 의 structured type 정합. 5 module 122 PASS, dispatcher 47 PASS.
> cumulative 0.7.x~0.8.x follow-up 9 release 의 다섯 번째. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 4단계 (phishing_federation + v4)

| Error type | count | Fix |
|---|---|---|
| arg-type: `float(url_data[k]["confidence"])` 의 `object` | 4 | TypedDict `_UrlRecord` 정의 + `dict[str, _UrlRecord]` 명시 |
| attr-defined: `"object" has no attribute "append"` | 2 | 위와 동일 fix |
| union-attr: `float \| list[str]` no-attr append | 1 | 위와 동일 fix |
| arg-type: `sorted` 의 `list[tuple[... object, object ...]]` | 1 | 위와 동일 fix |
| **total** | **8** | **0** |

**4 error × 2 file (동일 pattern)**.

### 🐛 Real bug fix (mypy strict detect)

기존 `url_data: dict[str, dict[str, object]] = {}` 의 *implicit* 추론은 inner dict 의
value type 을 모두 `object` 로 — *narrowing* 안 됨. 결과:
- `data["confidence"]` 의 type 이 `object` — `float(...)` 호출이 *unsafe* (TypeError 위험)
- `data["sources"]` 의 type 이 `object` — `.append(...)` 호출이 *unsafe* (AttributeError 위험)

runtime 에는 *self* `{"confidence": 0.0, "sources": []}` literal 의 *narrowing* 덕분에
문제 없었지만, *static* 차원에서 *TypedDict* 으로 구조화하는 게 정공법.

**fix**: PEP 589 `TypedDict` 로 `_UrlRecord` 정의 (`confidence: float` + `sources: list[str]`).
*real bug fix*: future 변경 (예: confidence 를 `int` 로 변경) 시 *static* type check 가
catch.

## 운영 누적 (v0.7.5 → v0.8.4)

| | v0.7.5 | v0.8.0 | v0.8.1 | v0.8.2 | v0.8.3 | **v0.8.4** |
|---|---|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 2 | 3 | 4 | **6** |
| **5 module test** | 64 | 122 | 122 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | 47 | 47 | **47** |
| **real bug fix (cumulative)** | 0 | 0 | 2 | 4 | 4 | **+2 (total: 6)** |

## In-flight 발견 + fix

- **bug 1**: `dict[str, object]` 추론의 *implicit* unsafe access (양쪽 file) — TypedDict 으로
  *real type safety* 회복.

## Test 결과

- `mypy --strict workflow_kit/phishing_federation.py`:
  - **before v0.8.4**: 4 errors in 1 file
  - **after v0.8.4**: "Success: no issues found in 1 source file"
- `mypy --strict workflow_kit/phishing_federation_v4.py`:
  - **before v0.8.4**: 4 errors in 1 file
  - **after v0.8.4**: "Success: no issues found in 1 source file"
- `mypy --strict` (6 file): 7 error in phishing_keywords.py (v0.8.5 follow-up)
- 회귀 5 module + dispatcher: 변동 없음
- **cumulative strict clean file count**: 4 → **6** (`__init__.py` + `url_validity.py` + `okf_import.py` + `okf_export.py` + `phishing_federation.py` + `phishing_federation_v4.py`)

## 변경 파일 (4 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/phishing_federation.py` | +6 / -2 (TypedDict 정의 + url_data type 명시) |
| M | `workflow_kit/phishing_federation_v4.py` | +6 / -2 (동일 fix) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.4 entry) |
| A | `workflow-source/releases/Beta-v0.8.4.md` | release note |
| A | `ai-workflow/memory/release/v0.8.4/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.5+ / v0.9.0)

1. **v0.8.5**: `workflow_kit/phishing_keywords.py` strict clean (7 error: 5 no-untyped-def + 2 no-return)
2. **v0.8.5**: `workflow_kit/cache_lfu_decay.py` + `cache_lfu_decay_persist.py` strict clean
3. **v0.8.6**: `workflow_kit/workflow_kit_cli.py` (48 error, 가장 큼)
4. **v0.8.7**: `workflow_kit/common/state/builder.py` 35 error
5. **v0.8.8**: `workflow_kit/common/contracts/baselines.py` 27 error
6. **v0.9.0** full mypy strict
