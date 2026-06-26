# Beta v0.11.9 — mypy strict 단계적 격상 23-24단계 (testing + runner) (2026-06-26)

> **SemVer patch** (v0.11.8 → v0.11.9) — v0.11.8 release note 의 "다음" §1 follow-up. **mypy strict 누적 격상 31 → 33 file** (testing 1 + runner 1 = 2 errors 해소). v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 변경 (type annotation fix only, runtime 영향 ❌)

### 1. `common/testing.py` strict clean (1 error → 0)

**v0.11.8 시점 1 error**:
```
testing.py:216: Cannot find implementation or library stub for module named "hypothesis"  [import-not-found]
```

**Fix 정공법**:
- `# type: ignore[import-not-found]` 명시
- `hypothesis` 는 optional dependency 이며 runtime try/except 으로 graceful skip 정합 (mypy strict 단계적 격상 시 stub 부재는 expected)

### 2. `common/runner.py` strict clean (1 error → 0)

**v0.11.8 시점 1 error**:
```
runner.py:229: Incompatible types in assignment
  (expression has type "Path | None", variable has type "Path")  [assignment]
```

**Fix 정공법**:
- `resolved_latest_backlog: Path | None = ...` 명시적 type annotation
- `isinstance(raw_latest_backlog, str) and raw_latest_backlog` guard
- line 204 의 `latest_backlog_path` 와 이름 충돌 회피 (`resolved_latest_backlog` 별도 이름)

### 3. 누적 strict clean file count 갱신 (31 → 33)

**`workflow_kit/__init__.py` docstring**:
```
    - v0.11.9 누적: 33 file strict clean
      v0.11.8 31 + v0.11.9 23-24단계 (testing + runner) = 33 file
```

## 운영 누적 (v0.11.8 → v0.11.9)

| | v0.11.8 | **v0.11.9** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **mypy strict clean file** | 31 | **33** (+2) |
| **전체 workflow_kit/ strict error** | 4 errors in 4 files | **2 errors in 2 files** (2 errors 해소) |
| **cumulative acceptance** | 88/88 | **89/89** (v0.11.9 1 신규) |
| **breaking change** | none | **none** (annotation 만) |

## Test 결과

- 신규 (1 PASS, v0.11.9):
  - `test_mypy_strict_clean_v0_11_9` — testing.py + runner.py strict clean (각 0 errors) + cumulative 31 → 33 + runtime 회귀 ❌ (`evaluate_compliance` + `optional_path_flag` 정상 동작)
- 회귀 (88/88 PASS)
- 누적 acceptance: **89/89 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/common/testing.py` | `# type: ignore[import-not-found]` 추가 — 1 error → 0 |
| M | `workflow-source/workflow_kit/common/runner.py` | `resolved_latest_backlog: Path \| None` 명시적 annotation + isinstance guard — 1 error → 0 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.8-beta"` → `"v0.11.9-beta"` + cumulative 31 → 33 명시 |
| M | `workflow-source/pyproject.toml` | version 0.11.8 → 0.11.9 |
| A | `workflow-source/tests/check_mypy_strict_v0_11_9.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.9.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.9/backlog/2026-06-26.md` | v0.11.9 plan |

## 다음 (v0.11.10+ / v1.0.0)

1. **v0.11.10** — 잔존 2 file (common/project_docs, common/profiling).
2. **v0.11.11** — full mypy strict 도달 (모든 file strict clean).
3. **v1.0.0** — full mypy strict 도달 (semver major 정렬).
