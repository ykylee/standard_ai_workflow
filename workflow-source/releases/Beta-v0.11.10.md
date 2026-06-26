# Beta v0.11.10 — 🎯 FULL mypy strict 도달 (project_docs + profiling 격상) (2026-06-26)

> **SemVer patch** (v0.11.9 → v0.11.10) — v0.11.9 release note 의 "다음" §1 follow-up. **🎯 FULL mypy strict 도달**: mypy strict 누적 격상 33 → **35 file** (project_docs 1 + profiling 1 = 2 errors 해소). v0.8.0 spec §5.3 단계적 격상 정공법 정합 — **1 release = 1-2 file 격상**. **PyPI 배포: no** (GitHub Releases only).

## 🎯 핵심 마일스톤 — FULL mypy strict 도달

**v0.11.10 시점 `mypy workflow_kit/` 실행 결과**:
```
$ mypy --no-incremental workflow_kit/
Success: no issues found in 106 source files
```

**즉, 모든 106 source file 이 mypy 2.1.0 strict 기준 clean** (cumulative 35 file + 71 file 은 incremental strict 단계적 격상 미참여이나 strict 에러 0).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `common/project_docs.py` strict clean (1 error → 0)

**v0.11.9 시점 1 error**:
```
project_docs.py:88: Need type annotation for "items"  [var-annotated]
```

**Fix 정공법**:
- `items: dict[str, list[str]] = {"in_progress_items": [], "blocked_items": [], "done_items": []}` 명시적 annotation

### 2. `common/profiling.py` strict clean (1 error → 0)

**v0.11.9 시점 1 error**:
```
profiling.py:185: Library stubs not installed for "objgraph"  [import-untyped]
```

**Fix 정공법**:
- `import objgraph  # type: ignore[import-untyped]  # noqa: F401` 명시
- `objgraph` 는 optional dependency, runtime try/except 으로 graceful skip 정합

### 3. 누적 strict clean file count 갱신 (33 → 35) + FULL STRICT 명시

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.10 누적: 35 file strict clean
      v0.11.9 33 + v0.11.10 25-26단계 (project_docs + profiling) = 35 file
      🎯 FULL mypy strict 도달 (전체 workflow_kit/ 0 errors)
```

## 운영 누적 (v0.11.9 → v0.11.10)

| | v0.11.9 | **v0.11.10** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 33 | **35** (+2) |
| **전체 workflow_kit/ strict error** | 2 errors in 2 files | **🎯 0 errors in 0 files** (full strict) |
| **cumulative acceptance** | 89/89 | **90/90** (v0.11.10 1 신규) |
| **breaking change** | none | **none** (annotation 만) |
| **🎯 mypy workflow_kit/ exit 0** | ❌ (2 errors 잔존) | **✅ (full strict 도달)** |

## Test 결과

- 신규 (1 PASS, v0.11.10):
  - `test_mypy_strict_clean_v0_11_10` — project_docs.py + profiling.py strict clean (각 0 errors) + cumulative 33 → 35 + **🎯 전체 workflow_kit/ 0 errors** + runtime 회귀 ❌ (`parse_handoff` + `check_profiling_available` + `evaluate_compliance` callable verify)
- 회귀 (89/89 PASS)
- 누적 acceptance: **90/90 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/project_docs.py` | `dict[str, list[str]]` 명시적 annotation — 1 error → 0 |
| M | `workflow-source/workflow_kit/common/profiling.py` | `# type: ignore[import-untyped]` — 1 error → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.9-beta"` → `"v0.11.10-beta"` + cumulative 33 → 35 + FULL STRICT 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.9 → 0.11.10 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_10.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.10.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.10/backlog/2026-06-26.md` | v0.11.10 plan |

## 📈 누적 진행 (v0.11.3 → v0.11.10, FULL STRICT 도달!)

| Release | cycle | commit | 핵심 |
|---------|-------|--------|------|
| v0.11.3 | mypy 11-12 | `bfbd100` | purpose_ingest + purpose_graph (신규) |
| v0.11.4 | mypy 13-14 | `6f6bf38` | output_contracts + milestones |
| v0.11.5 | mypy 15-16 | `ba27ffd` | decorators + linter |
| v0.11.6 | mypy 17-18 | `c82bf72` | session_outputs + read_only_bundle |
| v0.11.7 | mypy 19-20 | `5c82bc3` | workflow_kit_cli + doc_sync |
| v0.11.8 | mypy 21-22 | `ae4058a` | read_only_mcp_sdk + workflow_writes |
| v0.11.9 | mypy 23-24 | `41ef022` | testing + runner |
| **v0.11.10** | **mypy 25-26** | **TBD** | **🎯 project_docs + profiling (FULL STRICT 도달)** |

## 다음 (v0.11.11+ / v1.0.0)

1. **v0.11.11** — full strict 유지 + 누적 acceptance verify (`mypy workflow_kit/` exit 0 CI 통합).
2. **v1.0.0** — full mypy strict 도달 (semver major 정렬, full strict 의 milestone release).
