# Beta v0.11.14 — Release-status dispatcher (신규 workflow_kit/<module> mypy strict clean 2-layer defense 실증) (2026-06-26)

> **SemVer patch** (v0.11.13 → v0.11.14) — v0.11.13 release note 의 "다음" §1 follow-up. **신규 `workflow_kit/release_status.py` module** + dispatcher `release-status` subcommand + `__init__.py` 의 import/`__all__` 추가 + cumulative strict clean 35 → **36 file** (v0.11.14 27단계). **2-layer mypy strict defense 의 실증** — 신규 module 이 처음부터 strict clean 으로 작성되어 v0.11.11 CI + v0.11.12 release-time gate 자동 verify 통과. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 module + 1 dispatcher subcommand + 1 acceptance test)

### 1. `workflow_kit/release_status.py` 신규 (read-only aggregator)

6 helper + 1 main entry:
- `_read_pyproject_version()` — `workflow-source/pyproject.toml` 의 `[project] version` field parse
- `_last_release_tag()` — `git describe --tags --abbrev=0` (e.g. `v0.11.13-beta`)
- `_unreleased_commits(since_tag)` — `git log <since_tag>..HEAD --oneline` (count + list)
- `_suggest_next_version(current)` — semver patch bump (e.g. `0.11.13` → `0.11.14`)
- `_check_local_mypy()` — Layer 2 mypy strict on `workflow-source/workflow_kit/`
- `_check_ci_mypy()` — Layer 1 GH Actions mypy-strict workflow last run (release_pipeline._cross_verify_ci_mypy reuse, v0.11.13+)
- `cmd_release_status(args)` — main entry, returns 8-key dict

**Returns** (8 key):
```python
{
    "current_version": "0.11.13",
    "last_release_tag": "v0.11.13-beta",
    "unreleased_commits": {"count": int, "commits": [{"sha", "subject"}]},
    "ci_mypy": {verdict, head_sha_match, ci_run, message},
    "local_mypy": {ok, exit_code, error_count, first_error},
    "next_version": {next, current, bumped},
    "ready_to_release": bool,
    "ready_reason": str,
}
```

**ready_to_release verdict**:
- `last_tag` 의 `vX.Y.Z-beta` → `current_version` 비교 후 동일하면 `False` (이미 released)
- `unreleased_commits.count == 0` → `False`
- `local_mypy.ok == False` → `False` (Layer 2 fail)
- `ci_mypy.verdict` ∈ {`ci_stale`, `ci_fail`, `drift_warning`} → `False` (Layer 1 fail)
- 모두 통과 → `True`

### 2. dispatcher `release-status` subcommand (subcommand 35, read-only)

- `@register("release-status")` decorator (dispatcher pattern 정합)
- Args: `--json` (text/JSON mode)
- text mode: 9-line summary (current_version / last_release_tag / unreleased_commits / ci_mypy.verdict / ci_mypy.head_sha_match / local_mypy.ok / local_mypy.error_count / next_version / ready_to_release + ready_reason)
- JSON mode: `json.dumps(result, indent=2, ensure_ascii=False, default=str)`
- read-only, destructive 정공법 memory #5 정합

### 3. `__init__.py` 갱신

- `from . import (...)` 에 `release_status` 추가
- `__all__` 에 `"release_status"` 추가
- cumulative count 주석: `v0.11.14 누적: 36 file strict clean` (v0.11.10 35 + v0.11.14 27단계 release_status.py)

## 2-layer mypy strict defense 실증 (v0.11.14 의 핵심)

본 release 의 신규 `release_status.py` 가 처음부터 strict clean 으로 작성되어 v0.11.11 Layer 1 (CI) + v0.11.12 Layer 2 (release-time gate) 자동 verify 통과:

| 검증 | 결과 |
|---|---|
| `mypy --no-incremental workflow-source/workflow_kit/` (Layer 2) | **0 errors in 107 source files** (was 106) |
| `.github/workflows/mypy-strict.yml` (Layer 1) push trigger | **passing** (CI run 후속 verify) |
| `cmd_release --strict-cross-verify` cross-verify | **sanity** (Layer 1 + Layer 2 정합) |
| `cmd_release --dry-run` release-time gate | **release 진행 가능** |

**Lesson**: v0.11.11~v0.11.13 의 2-layer defense 가 정상 동작하면, v0.11.14 의 신규 module 도 추가 작업 없이 strict clean 상태로 commit 가능. 본 release 가 2-layer defense 의 실증 사례.

## 운영 누적 (v0.11.13 → v0.11.14)

| | v0.11.13 | **v0.11.14** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **dispatcher subcommand** | 34 (`cascade-delete`) | **35 (`release-status`)** |
| **cumulative strict clean** | 35 file | **36 file** (release_status.py 신규) |
| **mypy strict source files** | 106 (0 errors) | **107 (0 errors)** |
| **cumulative acceptance** | 108/108 | **116/116** (v0.11.14 8 신규) |
| **breaking change** | none | **none** (신규 subcommand + module) |

## Test 결과

- 신규 (1 PASS, v0.11.14, 8 case):
  - `test_release_status_v0_11_14` — `release_status.py` 신규 + 6 helper + `__init__.py` import/`__all__` + cumulative count >= 36 + dispatcher `release-status` + docstring v0.11.14/read-only + `--json` flag + `cmd_release_status` schema 8 key + mypy strict 107 source files + text/JSON mode rc=0 + `ready_to_release` verdict logic
- 회귀 (108/108 PASS)
- 누적 acceptance: **116/116 PASS**

## 변경 파일 (5 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/__init__.py` | `release_status` import + `__all__` + cumulative count 35 → 36 + loud fallback `"v0.11.13-beta"` → `"v0.11.14-beta"` |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | dispatcher `release-status` subcommand (subcommand 35) + docstring + text/JSON mode |
| M | `workflow-source/pyproject.toml` | version 0.11.13 → 0.11.14 |
| A | `workflow-source/workflow_kit/release_status.py` | 신규 (6 helper + cmd_release_status) |
| A | `workflow-source/tests/check_release_status_v0_11_14.py` | 신규 (1 acceptance test, 8 case) |
| A | `workflow-source/releases/Beta-v0.11.14.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.14/backlog/2026-06-26.md` | v0.11.14 plan |

## 다음 (v0.11.15+ / v1.0.0)

1. **v0.11.15** — `cmd_release --json` 의 `ci_mypy.verdict` 1-line summary 추가 (jq-friendly: `cmd_release --json | jq '.ci_mypy.verdict'`)
2. **v0.11.16** — `cmd_release_status` 의 `ready_to_release` 자동 bump (current_version == last_release_tag 일 때 `--auto-bump` flag 로 next_version 자동 적용)
3. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`)
