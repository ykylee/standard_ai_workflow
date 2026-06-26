# Beta v0.11.6 — mypy strict 단계적 격상 17-18단계 (session_outputs + read_only_bundle) (2026-06-26)

> **SemVer patch** (v0.11.5 → v0.11.6) — v0.11.5 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 25 → 27 file** (session_outputs 3 + read_only_bundle 3 = 6 errors 해소). v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `session_outputs.py` strict clean (3 errors → 0)

**v0.11.5 시점 3 errors**:
```
session_outputs.py:24: "object" has no attribute "__iter__"
  ([t for t in tasks if isinstance(t, dict) ...])
session_outputs.py:37: Argument 1 to "len" has incompatible type "object"; expected "Sized"
session_outputs.py:39: ... (동일, len(handoff['in_progress_items']))
```

**Fix 정공법**:
- `tasks_list = cast("list[object]", tasks)` — `backlog.get("tasks", [])` 의 object narrow
- 중간 변수 `backlog_ip_raw` / `handoff_ip_raw` + `isinstance(...)` guard + `cast("list[object]", ...)` 후 `len(...)` 호환

### 2. `read_only_bundle.py` strict clean (3 errors → 0)

**v0.11.5 시점 3 errors**:
```
read_only_bundle.py:269: "object" has no attribute "__iter__"
  (extend(str(item) for item in backlog.get("in_progress_items", [])))
read_only_bundle.py:270: ... (extend(str(item) for item in backlog.get("done_items", [])))
read_only_bundle.py:271: ... (extend(str(warning) for warning in backlog.get("warnings", [])))
```

**Fix 정공법**:
- `backlog_ip_raw` / `backlog_done_raw` / `backlog_warn_raw` 중간 변수 도입 + `cast("list[object]", ...) if isinstance(...) else []`

### 3. 누적 strict clean file count 갱신 (25 → 27)

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.6 누적: 27 file strict clean
      v0.11.5 25 + v0.11.6 17-18단계 (session_outputs + read_only_bundle) = 27 file
```

## 운영 누적 (v0.11.5 → v0.11.6)

| | v0.11.5 | **v0.11.6** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 25 | **27** (+2) |
| **전체 workflow_kit/ strict error** | 18 errors in 10 files | **12 errors in 8 files** (6 errors 해소, 2 file 격상) |
| **cumulative acceptance** | 85/85 | **86/86** (v0.11.6 1 신규) |
| **breaking change** | none | **none** (annotation 만) |

## Test 결과

- 신규 (1 PASS, v0.11.6):
  - `test_mypy_strict_clean_v0_11_6` — session_outputs.py + read_only_bundle.py strict clean + cumulative 25 → 27 + runtime 회귀 ❌ (`build_session_summary` + `make_session_recommended_action` + `create_session_handoff_draft_payload` 정상 동작)
- 회귀 (85/85 PASS)
- 누적 acceptance: **86/86 PASS**

## 변경 파일 (3 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/session_outputs.py` | cast 도입 (typing import + line 24 + line 36-41) — 3 errors → 0 |
| M | `workflow-source/workflow_kit/common/read_only_bundle.py` | 중간 변수 + cast(list[object]) — 3 errors → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.5-beta"` → `"v0.11.6-beta"` + cumulative 25 → 27 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.5 → 0.11.6 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_6.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.6.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.6/backlog/2026-06-26.md` | v0.11.6 plan |

## 다음 (v0.11.7+ / v1.0.0)

1. **v0.11.7** — `workflow_kit_cli.py` 4 errors (다음 단계). 1 release = 1-2 file.
2. **v0.11.8+** — 잔존 8 file 단계적 해소.
3. **v1.0.0** — full mypy strict 도달.
