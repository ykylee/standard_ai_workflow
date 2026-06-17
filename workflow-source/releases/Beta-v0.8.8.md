# Beta v0.8.8 — mypy strict 단계적 격상 8단계 (4 file) + release_pipeline SSOT refactor (2026-06-17)

> v0.8.0 spec §5.3 mypy strict 단계적 격상 — 8단계. `upgrade_diff.py` (1) + `bitbucket_v2.py`
> (4) + `lfu_integration.py` (1) + `cache_size_compare.py` (2) 의 **8 mypy error → 0**.
> 부수적: `tools/release_pipeline.py` 의 `read_workflow_kit_version` /
> `write_workflow_kit_version` 가 v0.8.0+ SSOT (pyproject.toml) 와 정합하도록 refactor.
> 5 module test 122 PASS (변동 없음), dispatcher 47 PASS, version auto-sync 4 PASS.
> cumulative 0.7.x~0.8.x follow-up 13 release 의 아홉 번째. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📐 mypy strict 격상 8단계 (4 file, 8 error)

| File | error type | count | Fix |
|---|---|---|---|
| `upgrade_diff.py` | unused-ignore | 1 | `__lt__` 의 `# type: ignore[override]` 제거 (실제 override 임 — ParsedVersion 간 비교) |
| `bitbucket_v2.py` | no-untyped-def (param) | 1 | `requests_get: Callable[..., Any] \| None = None` |
| `bitbucket_v2.py` | no-untyped-def (return + param) | 2 | inner `def requests_get(...) -> Any:`, `**kwargs: Any` 명시 |
| `bitbucket_v2.py` | no-any-return | 1 | `cast(list[dict[str, Any]], data["values"])` |
| `cache_size_compare.py` | no-untyped-def (param) | 2 | `base_path: Path \| None = None` (line 47, 81) |
| `lfu_integration.py` | type-arg | 1 | `tuple` → `tuple[float, float]` (`(score, e.timestamp)` 명시) |
| **total** | | **8** | **0** |

### 🔧 release_pipeline SSOT refactor (v0.8.0 follow-up)

v0.8.0 의 `__init__.py` SSOT refactor (`__version__ = _read_pyproject_version()`) 가
기존 `tools/release_pipeline.py:read_workflow_kit_version` 의 regex-on-file 패턴과 충돌
(`__version__ = "..."` literal 없음). 본 release 에서 정합:

- `read_workflow_kit_version()`: regex-on-file → `f"v{read_version()}-beta"` (SSOT 동일)
- `write_workflow_kit_version()`: regex-on-file → `write_version(new)` (SSOT 갱신) +
  `__init__.py` 의 loud fallback literal (loud fallback chain §4.3 3번째) 도 정합성 유지

부수적 test update:
- `tests/check_release_pipeline_version_auto_sync.py:_read_init_version` →
  `f"v{_read_pyproject_version()}-beta"` (runtime compute 와 동일 formula)
- `tests/check_release_pipeline_version_auto_sync.py: test_version_bump_no_init_skips`
  → `--no-init` 가 *literal fallback 보존* 임을 명시적으로 verify (`_read_init_fallback_literal`)

## 운영 누적 (v0.7.5 → v0.8.8)

| | v0.7.5 | v0.8.0 | v0.8.7 | **v0.8.8** |
|---|---|---|---|---|
| **mypy strict clean file** | 0 | 1 | 13 | **17** |
| **5 module test** | 64 | 122 | 122 | **122** |
| **dispatcher test** | 6 | 47 | 47 | **47** |
| **version auto-sync test** | 0 | 0 | 0 | **4** |

## In-flight 발견 + fix

- **fix 1**: v0.8.0 의 `__init__.py` SSOT compute 가 `release_pipeline.py:read_workflow_kit_version`
  regex-on-file 과 충돌. 본 release 에서 SSOT 일원화 (pyproject.toml = 단일 출처).
- **fix 2**: `bitbucket_v2.py:47` inner `requests_get` function 의 `**kwargs` 미annotation.
  `Any` 명시.
- **fix 3**: `bitbucket_v2.py:63` 의 `return data["values"]` 가 `Any` 반환.
  `cast(list[dict[str, Any]], ...)` 명시.
- **fix 4**: `cache_size_compare.py` 의 `base_path=None` (no-untyped-def) 2 site.
  `Path | None` 으로 명시 (`cache_file_for_strategy` 가 `Path` 만 받음).
- **fix 5**: `lfu_integration.py:_evict_key_with_lfu` return `tuple` 미명시.
  `tuple[float, float]` (score + timestamp) 로 narrow.

## Test 결과

- `mypy --strict` (4 file): 8 errors → "Success: no issues found in 4 source files"
- `mypy --strict` (cumulative, 30 file): v0.8.8 단계에서 17 file strict clean
- 회귀 (5 module + dispatcher): 변동 없음
  - `check_url_validity.py`: 14/14 PASS
  - `check_path_resolver.py`: 12/12 PASS
  - `check_okf_import.py`: 25/25 PASS
  - `check_release_pipeline_lib.py`: 7/7 PASS
  - `check_cache_migration.py`: 5/5 PASS
  - `check_workflow_kit_cli.py`: 47/47 PASS
  - `check_bitbucket_v2.py`: 2/2 PASS (변동 없음)
  - `check_release_pipeline_version_auto_sync.py`: 4/4 PASS (v0.8.0 follow-up fix)
- `gen-schema --check`: check_status: identical, 85,743 bytes
- **cumulative strict clean file count**: 13 → **17** (+ upgrade_diff + bitbucket_v2 + lfu_integration + cache_size_compare)

## 변경 파일 (6 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/upgrade_diff.py` | -1 (unused-ignore 제거) |
| M | `workflow_kit/bitbucket_v2.py` | +5 / -3 (annotation + cast + Callable import) |
| M | `workflow_kit/lfu_integration.py` | -0 / -1 (tuple → tuple[float, float]) |
| M | `workflow_kit/cache_size_compare.py` | +0 / -2 (Path \| None 명시) |
| M | `tools/release_pipeline.py` | +24 / -16 (read/write_workflow_kit_version SSOT refactor) |
| M | `tests/check_release_pipeline_version_auto_sync.py` | +14 / -3 (runtime compute + fallback literal helper) |
| A | `workflow-source/releases/Beta-v0.8.8.md` | release note |
| A | `ai-workflow/memory/release/v0.8.8/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.9+ / v0.9.0)

1. **v0.8.9**: `workflow_kit/common/state/builder.py` 35 error
2. **v0.8.10**: `workflow_kit/common/contracts/baselines.py` 27 error
3. **v0.9.0** full mypy strict
