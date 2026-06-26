# Beta v0.11.4 — mypy strict 단계적 격상 13-14단계 (output_contracts + milestones) (2026-06-26)

> **SemVer patch** (v0.11.3 → v0.11.4) — v0.11.3 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 21 → 23 file** (기존 14 file 중 가장 단순한 fix 패턴의 2 file 부터 단계적 해소). v0.8.0 spec §5.3 의 단계적 격상 정공법 정합 — **1 release = 1-2 file 단계적 격상**. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `output_contracts.py` strict clean (6 errors → 0)

**v0.11.3 시점 6 errors**:
```
output_contracts.py:296: Incompatible types in assignment
  (expression has type "type[BaseModel] | None", variable has type "type[ErrorOutput]")
output_contracts.py:297: Function "model_cls" could always be true in boolean context
output_contracts.py:323: Dict entry 0 has incompatible type
  "str": "dict[str, dict[str, object]]"; expected "str": "dict[str, object]"
output_contracts.py:324: Dict entry 1 has incompatible type ... (동일 패턴)
output_contracts.py:357: "object" has no attribute "get"
output_contracts.py:368: Incompatible return value type
  (got "object", expected "dict[str, object]")
```

**Fix 정공법**:
1. `model_cls: type[BaseModel] = ErrorOutput` (line 293 explicit annotation) + `if registry_cls is None: return ...` (line 296 narrow)
2. `outputs: dict[str, dict[str, object]] = {}` (explicit annotation) + outer `cast("dict[str, dict[str, object]]", {...})` (return type 명시)
3. `_resolve` 함수에서 `cast("dict[str, object]", node)` (object narrowing) + `defs.get(ref_name)` 결과를 `object` 명시

### 2. `milestones.py` strict clean (4 errors → 0)

**v0.11.3 시점 4 errors**:
```
milestones.py:49: "object" has no attribute "__iter__" (done_tasks)
milestones.py:50: "object" has no attribute "__iter__" (in_progress_tasks)
milestones.py:52: Incompatible types in assignment
  (expression has type "object", variable has type "list[Any]")
milestones.py:53: ... (동일)
```

**Fix 정공법**:
- `done_tasks_raw` / `in_progress_tasks_raw` 의 type narrowing (`isinstance(..., list)` check)
- `done_tasks: list[Any] = ... if isinstance(..., list) else []` (explicit annotation + fallback)
- `[t for t in done_tasks if isinstance(t, str) and target_thread in t]` (iter element type guard)

### 3. 누적 strict clean file count 갱신 (21 → 23)

**`workflow_kit/__init__.py` docstring 갱신**:
```
    - v0.11.3 누적: 21 file strict clean (mypy 2.1.0 strict 기준)
      cycle 3/4 신규 모듈 (purpose_ingest + purpose_graph) + 계속한 장면
    - v0.11.4 누적: 23 file strict clean
      v0.11.3 21 + v0.11.4 13-14단계 (output_contracts + milestones) = 23 file
```

## 운영 누적 (v0.11.3 → v0.11.4)

| | v0.11.3 | **v0.11.4** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 21 | **23** (+2) |
| **전체 workflow_kit/ strict error** | 34 errors in 14 files | **24 errors in 12 files** (10 error 해소, 2 file 격상) |
| **cumulative acceptance** | 83/83 | **84/84** (v0.11.4 1 신규) |
| **breaking change** | none | **none** (type annotation 만 변경, runtime 동일) |

## Test 결과

- 신규 (1 PASS, v0.11.4):
  - `test_mypy_strict_clean_v0_11_4` — output_contracts.py + milestones.py strict clean verify (각 0 errors) + cumulative 21 → 23 갱신 + runtime 회귀 영향 ❌ verify (`output_json_schema_bundle` / `output_json_schema_for_family` / `validate_output_payload` / `assess_milestone_progress` 정상 동작)
- 회귀 (83/83 PASS, 변동 ❌)
  - v0.11.3 mypy: 1/1
  - v0.11.2 graph insights skill integration: 5/5
  - v0.11.1 graph insights: 8/8
  - v0.11.0 cycle 3: 6/6
  - v0.10.3 cascade: 7/7
  - v0.10.2 delivery: 9/9
  - v0.10.1 entry: 6/6
  - v0.10.0 deprec: 6/6
  - v0.9.x: 35/35
- 누적 acceptance: **84/84 PASS**

## 변경 파일 (3 변경 + 2 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/output_contracts.py` | type annotation 추가 (cast + explicit dict typing) — 6 errors → 0 |
| M | `workflow-source/workflow_kit/common/milestones.py` | type narrowing + isinstance guard — 4 errors → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.3-beta"` → `"v0.11.4-beta"` + cumulative strict clean 21 → 23 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.3 → 0.11.4 |
| M | `ai-workflow/memory/active/state.json` | recent_done + in_progress + latest_backlog_path 갱신 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_4.py` | 신규 (1 acceptance test, ≈ 140 line) |
| A | `workflow-source/releases/Beta-v0.11.4.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.4/backlog/2026-06-26.md` | v0.11.4 plan |

## 다음 (v0.11.5+ / v1.0.0)

1. **v0.11.5** — `decorators.py` 6 errors + `linter.py` 4 errors (다음 단계적 해소 대상). 1 release = 1-2 file.
2. **v0.11.6** — `session_outputs.py` 3 errors + `read_only_bundle.py` 3 errors.
3. **v0.11.7+** — 잔존 12 file 단계적 해소.
4. **v1.0.0** — full mypy strict 도달 (semver major 정렬, 100+ release 후 예상).

## Bundle 비율 (변동 ❌, 95% 유지)

순수 type annotation fix, 기능 변경 ❌, 외부 API 시그니처 동일.
