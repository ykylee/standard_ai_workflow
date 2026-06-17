# Beta v0.8.5 — mypy strict 단계적 격상 5단계 (phishing_keywords + cache_lfu_decay*) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 5단계. `phishing_keywords.py` (V-R11
> phishing keyword + PhishTank/OpenPhish API, ADR-017/023) + `cache_lfu_decay.py` +
> `cache_lfu_decay_persist.py` (LFU decay integration/persistence, ADR-021) 의
> **11 mypy error → 0**. 5 module 122 PASS, dispatcher 47 PASS.
> cumulative 0.7.x~0.8.x follow-up 10 release 의 여섯 번째. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 5단계 (3 file, 11 error)

| File | count | Fix |
|---|---|---|
| `phishing_keywords.py` | 7 | 4 `requests_get` param type + 2 nested `def requests_get` annotation + 1 import |
| `cache_lfu_decay.py` | 4 | 3 `config: LFUConfig` + 1 `entries: dict[str, Any]` + 1 return type narrowing |
| `cache_lfu_decay_persist.py` | 0 | 이미 strict clean (v0.7.49+ 정공법) |
| **total** | **11** | **0** |

## 운영 누적 (v0.7.5 → v0.8.5)

| | v0.7.5 | v0.8.0 | v0.8.1 | v0.8.4 | **v0.8.5** |
|---|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 2 | 6 | **9** |
| **5 module test** | 64 | 122 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | 47 | **47** |

## In-flight 발견 + fix

- (없음) — 단순 annotation 추가 (real bug fix 없음, type narrowing 만)

## Test 결과

- `mypy --strict workflow_kit/phishing_keywords.py`:
  - **before v0.8.5**: 7 errors
  - **after v0.8.5**: "Success: no issues found"
- `mypy --strict workflow_kit/cache_lfu_decay.py`:
  - **before v0.8.5**: 4 errors
  - **after v0.8.5**: "Success: no issues found"
- `mypy --strict` (9 file cumulative): "Success: no issues found in 9 source files"
- 회귀 5 module + dispatcher: 변동 없음
- **cumulative strict clean file count**: 6 → **9** (+ phishing_keywords + cache_lfu_decay*)

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/phishing_keywords.py` | +6 / -6 (annotation 추가) |
| M | `workflow_kit/cache_lfu_decay.py` | +5 / -3 (annotation + LFUConfig import) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.5 entry) |
| A | `workflow-source/releases/Beta-v0.8.5.md` | release note |
| A | `ai-workflow/memory/release/v0.8.5/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.6+ / v0.9.0)

1. **v0.8.6**: `workflow_kit/workflow_kit_cli.py` (48 error, 가장 큼 — module 별 분할)
2. **v0.8.7**: `workflow_kit/common/state/builder.py` 35 error
3. **v0.8.8**: `workflow_kit/common/contracts/baselines.py` 27 error
4. **v0.9.0** full mypy strict (모든 module strict clean)
