# Beta v0.11.8 — mypy strict 단계적 격상 21-22단계 (read_only_mcp_sdk + workflow_writes) (2026-06-26)

> **SemVer patch** (v0.11.7 → v0.11.8) — v0.11.7 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 29 → 31 file** (read_only_mcp_sdk 1 + workflow_writes 1 = 2 errors 해소). v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `server/read_only_mcp_sdk.py` strict clean (1 error → 0)

**v0.11.7 시점 1 error**:
```
read_only_mcp_sdk.py:116: "object" has no attribute "__iter__"
  (for descriptor in descriptors["tools"])
```

**Fix 정공법**:
- `tools_list = cast("list[object]", descriptors.get("tools", [])) if isinstance(...) else []`
- `descriptor["name"]` 등 5개 field 접근 시 `cast("dict[str, object]", descriptor)["name"]` narrow
- `from typing import cast` import 추가

### 2. `common/workflow_writes.py` strict clean (1 error → 0)

**v0.11.7 시점 1 error**:
```
workflow_writes.py:204: Need type annotation for "current_lists"  [var-annotated]
```

**Fix 정공법**:
- `current_lists: dict[str, list[str]] = {...}` 명시적 type annotation

### 3. 누적 strict clean file count 갱신 (29 → 31)

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.8 누적: 31 file strict clean
      v0.11.7 29 + v0.11.8 21-22단계 (read_only_mcp_sdk + workflow_writes) = 31 file
```

## 운영 누적 (v0.11.7 → v0.11.8)

| | v0.11.7 | **v0.11.8** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 29 | **31** (+2) |
| **전체 workflow_kit/ strict error** | 6 errors in 6 files | **4 errors in 4 files** (2 errors 해소) |
| **cumulative acceptance** | 87/87 | **88/88** (v0.11.8 1 신규) |
| **breaking change** | none | **none** (annotation 만) |

## Test 결과

- 신규 (1 PASS, v0.11.8):
  - `test_mypy_strict_clean_v0_11_8` — read_only_mcp_sdk.py + workflow_writes.py strict clean (각 0 errors) + cumulative 29 → 31 + runtime 회귀 ❌ (`build_lowlevel_server` + `upsert_backlog_entry` / `sync_handoff_status` callable verify)
- 회귀 (87/87 PASS)
- 누적 acceptance: **88/88 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/server/read_only_mcp_sdk.py` | cast(list[object]) + cast(dict[str, object]) 도입 — 1 error → 0 |
| M | `workflow-source/workflow_kit/common/workflow_writes.py` | `dict[str, list[str]]` 명시적 annotation — 1 error → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.7-beta"` → `"v0.11.8-beta"` + cumulative 29 → 31 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.7 → 0.11.8 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_8.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.8.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.8/backlog/2026-06-26.md` | v0.11.8 plan |

## 다음 (v0.11.9+ / v1.0.0)

1. **v0.11.9** — 잔존 4 file 단계적 해소 (common/testing, common/runner, common/project_docs, common/profiling).
2. **v0.11.10+** — full mypy strict 도달.
3. **v1.0.0** — full mypy strict 도달 (semver major 정렬).
