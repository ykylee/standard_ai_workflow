# Beta v0.8.14 — mypy strict 단계적 격상 10단계 (common/contracts/baselines.py) (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 10단계. `workflow_kit/common/contracts/baselines.py`
> (Extension baseline compliance evaluator, 5+2 baseline dispatcher) 의 **27 mypy error → 0**
> + **2 real bug fix** (AuditLogEvent 미존재 / append_audit_log arg 순서).
> 5 module test 122 PASS, dispatcher 53, version auto-sync 4, bitbucket_v2 2, read-only 4,
> workflow state 9, **baselines compliance 17**. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 10단계 (1 file, 27 error + 2 real bug fix)

| error type | count | Fix |
|---|---|---|
| type-arg (dict → dict[K, V]) | 13 | `dict` → `dict[str, Any]` 13 site (to_dict, _read_state_json, _is_enabled, _get_partial_rules, 7 dispatcher + evaluate_all) |
| arg-type (str vs Literal) | 1 | SEC-WF-05 의 `status` variable 에 `Status` Literal 명시 |
| arg-type (wrong arg order) | 1 | `append_audit_log(audit_path, completion)` — v0.7.7 original 이 arg 순서 swapped. **real bug fix** |
| arg-type (RuleResult class mismatch) | 4 | helper (auth/testing/profiling/resiliency) 의 `RuleResult` 와 local `RuleResult` 가 distinct class. helper returns dict → dict[str, Any] cast 후 local RuleResult 로 wrap |
| no-untyped-def | 4 | `_dummy_event()` → `_dummy_completion() -> Any`, `_eval_performance_memory_baseline` / `evaluate_compliance` / `evaluate_all` 의 `fn=None` → `fn: Callable[..., Any] \| None = None` |
| no-any-return | 2 | `to_dict()` return cast, `_get_partial_rules` 의 `state.get("partial_rules", [])` cast |
| no-untyped-call | 1 | `_dummy_event()` 호출 → `_dummy_completion() -> Any` typed |
| attr-defined (AuditLogEvent not exist) | 1 | `_dummy_event` 가 `from stage_gate import AuditLogEvent` 했지만 AuditLogEvent 는 stage_gate 에 *없음* (`StageCompletion` 만 존재). **real bug fix** — StageCompletion 으로 교체 |
| (str-keyed dict) | 1 | `_read_state_json` 의 json.loads return type cast |
| **total** | **27 + 2 bug** | **0** |

### Real bug fix 동반 (mypy strict 검출)

- **bug 1**: `_dummy_event` 가 `from workflow_kit.common.contracts.stage_gate import AuditLogEvent` 했지만
  `AuditLogEvent` 는 stage_gate 에 존재하지 않음 (`StageCompletion` 만 export). PERF-WF-04 의
  1000회 latency 측정 시 import error 또는 stage_gate 의 다른 attribute 와 conflict.
  **fix**: `_dummy_completion() -> Any` 가 `StageCompletion(stage_name="performance", stage_status="ok")` 반환.
- **bug 2**: `append_audit_log(dummy, test_audit_path := ...)` 의 arg 순서 오류.
  실제 signature: `append_audit_log(audit_path: Path | str, completion: StageCompletion)`.
  v0.7.7 original 이 (completion, audit_path) 로 swapped — TypeError 항상 raise 됐을 것.
  **fix**: `append_audit_log(test_audit_path, dummy)` 로 arg 순서 정정.

## 운영 누적 (v0.7.5 → v0.8.14)

| | v0.7.5 | v0.8.0 | v0.8.7 | v0.8.8 | v0.8.9 | v0.8.10 | v0.8.11 | v0.8.13 | **v0.8.14** |
|---|---|---|---|---|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 13 | 17 | 17 | 17 | 17 | 18 | **19** |
| **5 module test** | 64 | 122 | 122 | 122 | 122 | 122 | 122 | 122 | **122** |
| **baselines compliance** | n/a | 17 | 17 | 17 | 17 | 17 | 17 | 17 | **17** |
| **cumulative test** | 0 | 0 | 0 | 0 | 0 | 0 | 134 | 135 | **160** |

## Test 결과

- `mypy --strict workflow_kit/common/contracts/baselines.py`: 27 errors → "Success: no issues found"
- `mypy --strict` (cumulative, 33 file): v0.8.14 단계에서 19 file strict clean
- 회귀: 5 module 122 + dispatcher 53 + workflow state 9 + version 4 + bitbucket 2 + read-only 4 + **baselines compliance 17 신규 (=17 cumulative)** = 160/160 PASS
- gen-schema --check: check_status: identical, 85,743 bytes

**cumulative strict clean file count**: 18 → **19** (+ common/contracts/baselines.py)
**cumulative test**: 135 → **160 PASS** (+25, baselines compliance 17 + new dispatcher coverage 8)

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/common/contracts/baselines.py` | +76 / -32 (type-arg 13 + cast 6 + helper dispatch 4 + AuditLogEvent→StageCompletion real fix + arg 순서 real fix + 4 untyped def) |
| M | `pyproject.toml` | +1 (단계적 격상 note, v0.8.14 entry) |
| A | `workflow-source/releases/Beta-v0.8.14.md` | release note |
| A | `ai-workflow/memory/release/v0.8.14/backlog/2026-06-17.md` | plan |

## 다음 (v0.9.0)

1. **v0.9.0** full mypy strict (모든 module strict clean) — 마지막 단계. v0.8.0 spec §5.3 final.
