# Beta v0.11.5 — mypy strict 단계적 격상 15-16단계 (decorators + linter) (2026-06-26)

> **SemVer patch** (v0.11.4 → v0.11.5) — v0.11.4 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 23 → 25 file** (decorators + linter = 2 file 단계적 격상). v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `decorators.py` strict clean (2 errors → 0)

**v0.11.4 시점 2 errors**:
```
decorators.py:73: Incompatible return value type
  (got "Callable[[F], F]", expected "F")  [return-value]
decorators.py:93: No overload variant of "get" of "dict" matches argument types "int", "str"  [call-overload]
```

**Fix 정공법**:
- line 73: `cast(F, _wrap_with_shutdown(fn, ...))` — `Callable[[F], F]` → `F` narrow
- line 74: `cast(F, decorator)` — 내부 decorator 함수 의 `Callable[[F], F]` 추론 → `F` narrow
- line 93: `signal.SIGINT.value` (명시적 int 변환) + `cast(str, {...}.get(...))` — `dict[int, str].get(int, str)` overload 호환
- typing import: `cast` 추가

### 2. `linter.py` strict clean (4 errors → 0)

**v0.11.4 시점 4 errors**:
```
linter.py:138: "object" has no attribute "__iter__" (set comprehension of backlog.get(...))
linter.py:139: ... (동일, handoff.get)
linter.py:160: Argument 1 to "len" has incompatible type "object"; expected "Sized"
linter.py:164: ... (동일, done_items)
```

**Fix 정공법**:
- `backlog_in_progress_raw` / `handoff_in_progress_raw` / `state_in_progress_raw` 중간 변수 도입 + `cast(list[str], ...)` narrow
- `done_items = cast("list[object]", handoff.get("recent_done_items", []))` 후 `len(done_items)` 호환

### 3. 누적 strict clean file count 갱신 (23 → 25)

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.5 누적: 25 file strict clean
      v0.11.4 23 + v0.11.5 15-16단계 (decorators + linter) = 25 file
```

## 운영 누적 (v0.11.4 → v0.11.5)

| | v0.11.4 | **v0.11.5** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 23 | **25** (+2) |
| **전체 workflow_kit/ strict error** | 24 errors in 12 files | **18 errors in 10 files** (6 errors 해소, 2 file 격상) |
| **cumulative acceptance** | 84/84 | **85/85** (v0.11.5 1 신규) |
| **breaking change** | none | **none** (type annotation 만, runtime 동일) |

## Test 결과

- 신규 (1 PASS, v0.11.5):
  - `test_mypy_strict_clean_v0_11_5` — decorators.py + linter.py strict clean (각 0 errors) + cumulative 23 → 25 + runtime 회귀 ❌ (`graceful_shutdown` decorator + `check_workflow_consistency` 정상 동작)
- 회귀 (84/84 PASS, 변동 ❌)
- 누적 acceptance: **85/85 PASS**

## 변경 파일 (4 변경 + 2 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/decorators.py` | cast 도입 (typing import + 2 line) — 2 errors → 0 |
| M | `workflow-source/workflow_kit/common/linter.py` | cast(list[str], ...) narrow + 중간 변수 — 4 errors → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.4-beta"` → `"v0.11.5-beta"` + cumulative 23 → 25 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.4 → 0.11.5 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_5.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.5.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.5/backlog/2026-06-26.md` | v0.11.5 plan |

## 다음 (v0.11.6+ / v1.0.0)

1. **v0.11.6** — `session_outputs.py` 3 + `read_only_bundle.py` 3 (다음 단계). 1 release = 1-2 file.
2. **v0.11.7+** — 잔존 10 file 단계적 해소 (workflow_kit_cli, doc_sync, runner, workflow_writes, project_docs, read_only_mcp_sdk, server/* 등).
3. **v1.0.0** — full mypy strict 도달.
