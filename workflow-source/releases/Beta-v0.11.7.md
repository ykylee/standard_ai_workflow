# Beta v0.11.7 — mypy strict 단계적 격상 19-20단계 (workflow_kit_cli + doc_sync) (2026-06-26)

> **SemVer patch** (v0.11.6 → v0.11.7) — v0.11.6 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 27 → 29 file** (workflow_kit_cli 4 + doc_sync 2 = 6 errors 해소). v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `workflow_kit_cli.py` strict clean (4 errors → 0)

**v0.11.6 시점 4 errors** (모두 line 1381 동일):
```
workflow_kit_cli.py:1381: Missing named argument "project_profile_path" for "build_workflow_state_payload"  [call-arg]
workflow_kit_cli.py:1381: Missing named argument "session_handoff_path" for "build_workflow_state_payload"  [call-arg]
workflow_kit_cli.py:1381: Missing named argument "work_backlog_index_path" for "build_workflow_state_payload"  [call-arg]
workflow_kit_cli.py:1381: Missing named argument "generated_at" for "build_workflow_state_payload"  [call-arg]
```

**원인**: `cmd_ingest_purpose` 의 `--apply` 분기에서 `build_workflow_state_payload(workspace_root=workspace_root)` 호출 시 4개 keyword-only arg 누락.

**Fix 정공법**: `cmd_ingest_purpose` 의 advisory 갱신 (destructive 정공법 memory #5 정합) → `build_workflow_state_payload` 호출 제거 + `purpose_context._read_state_digest_and_rev` 직접 호출. dispatcher context 에서 path 3개 + `generated_at` 미보유 이므로 **build_workflow_state_payload 전체 호출은 부적절** (해당 함수는 4개 path 필수). 단순 advisory 비교만 필요하므로 lightweight 헬퍼 사용.

### 2. `doc_sync.py` strict clean (2 errors → 0)

**v0.11.6 시점 2 errors**:
```
doc_sync.py:23: Argument 2 to "path_exists_relative" has incompatible type "object"; expected "str | None"  [arg-type]
doc_sync.py:24: ... (동일, profile.get("document_home"))
```

**Fix 정공법**:
- 중간 변수 `operations_path_raw` / `document_home_raw` + `isinstance(..., str) or ... is None` guard + `cast("str | None", ...)` narrow
- `from typing import cast` import 추가

### 3. 누적 strict clean file count 갱신 (27 → 29)

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.7 누적: 29 file strict clean
      v0.11.6 27 + v0.11.7 19-20단계 (workflow_kit_cli + doc_sync) = 29 file
```

## 운영 누적 (v0.11.6 → v0.11.7)

| | v0.11.6 | **v0.11.7** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 27 | **29** (+2) |
| **전체 workflow_kit/ strict error** | 12 errors in 8 files | **6 errors in 6 files** (6 errors 해소) |
| **cumulative acceptance** | 86/86 | **87/87** (v0.11.7 1 신규) |
| **breaking change** | none | **none** (annotation 만, runtime 동일) |

## Test 결과

- 신규 (1 PASS, v0.11.7):
  - `test_mypy_strict_clean_v0_11_7` — workflow_kit_cli.py + doc_sync.py strict clean (각 0 errors) + cumulative 27 → 29 + runtime 회귀 ❌ (`cmd_ingest_purpose` `--json` 정상 emit + `cmd_graph_insights` 정상 + `build_doc_sync_candidates` 정상)
- 회귀 (86/86 PASS)
- 누적 acceptance: **87/87 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `build_workflow_state_payload` 호출 제거 + `purpose_context._read_state_digest_and_rev` 직접 호출 — 4 errors → 0 |
| M | `workflow-source/workflow_kit/common/doc_sync.py` | 중간 변수 + cast 도입 — 2 errors → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.6-beta"` → `"v0.11.7-beta"` + cumulative 27 → 29 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.6 → 0.11.7 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_7.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.7.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.7/backlog/2026-06-26.md` | v0.11.7 plan |

## 다음 (v0.11.8+ / v1.0.0)

1. **v0.11.8** — 잔존 6 file 단계적 해소 (server/read_only_mcp_sdk 1, common/workflow_writes 1, common/testing 1, common/runner 1, common/project_docs 1, common/profiling 1).
2. **v0.11.9+** — 모든 file 격상 후 full strict 도달.
3. **v1.0.0** — full mypy strict 도달 (semver major 정렬).
