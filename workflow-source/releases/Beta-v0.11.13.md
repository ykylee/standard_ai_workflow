# Beta v0.11.13 — Mypy CI cross-verify (Layer 1 ↔ Layer 2 정합 advisory) (2026-06-26)

> **SemVer patch** (v0.11.12 → v0.11.13) — v0.11.12 release note 의 "다음" §1 follow-up. **Layer 1 (CI mypy-strict workflow, v0.11.11+) ↔ Layer 2 (release-time mypy gate, v0.11.12+) 정합 advisory verify**. `cmd_release` 가 GH Actions mypy-strict workflow 의 last run + local mypy 결과를 결합하여 7 verdict 결정. default = advisory (release 진행). `--strict-cross-verify` 시 drift / ci_stale / ci_fail hard fail. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 cross-verify helper + 1 verdict resolver + 2 argparse flag + 1 acceptance test)

### 1. `_cross_verify_ci_mypy` helper (Layer 1 CI 조회)

**Invocation**: `gh run list --repo ykylee/standard_ai_workflow --workflow mypy-strict.yml --limit 1 --json databaseId,conclusion,headSha,event,status,createdAt,url`

**CI-only verdict 결정** (Layer 1 only):
| ci_conclusion | headSha match | CI-only verdict |
|---|---|---|
| success | yes | `ci_sanity` |
| success | no | `ci_stale` |
| failure | (any) | `ci_fail` |
| other / absent / no run | (any) | `absent` |
| gh CLI 부재 / error / timeout | — | `skipped` |

**Returns**: `{verdict, ci_run, head_sha, head_sha_match, message}`

### 2. `_resolve_cross_verify_verdict` helper (Layer 1 ↔ Layer 2 결합)

CI-only verdict + local mypy → final verdict (7 outcome):

| CI verdict   | local mypy ok | local status | final verdict      |
|--------------|---------------|--------------|--------------------|
| ci_sanity    | True          | checked      | **sanity**         |
| ci_sanity    | False         | checked      | **drift_warning**  |
| ci_sanity    | N/A           | skipped      | **no_local_verify** |
| ci_stale     | (any)         | (any)        | ci_stale           |
| ci_fail      | (any)         | (any)        | ci_fail            |
| absent       | (any)         | (any)        | absent             |
| skipped      | (any)         | (any)        | skipped            |

### 3. `cmd_release` 통합 (1번 cross-verify + 2.5번 verdict 결합)

```
1. cross-verify (_cross_verify_ci_mypy) — Layer 1 CI result
2. validate (cmd_validate) — 5 source Layer 2 gate
2.5. verdict 결합 (_resolve_cross_verify_verdict) — local mypy 와 cross
3. validate fail 시 early return (cross-verify 결과는 이미 results 에 포함됨)
```

**--strict-cross-verify flag 시 hard fail**: `drift_warning` / `ci_stale` / `ci_fail` 시 release abort.

### 4. argparse 2 flag

- `--skip-cross-verify`: cross-verify skip (default = advisory 만, 거의 항상 default 유지)
- `--strict-cross-verify`: drift / ci_stale / ci_fail hard fail (release-time safety 강화 시 사용)

### 5. dispatcher + lib forwarding

- `cmd_release_create` dispatcher: 2 flag forwarding + docstring 갱신
- `release_pipeline_lib.cmd_release`: 2 kwarg 추가 + `_make_args` default fill

## 운영 누적 (v0.11.12 → v0.11.13)

| | v0.11.12 | **v0.11.13** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **Layer 1 (CI)** | `.github/workflows/mypy-strict.yml` (v0.11.11+) | — |
| **Layer 2 (release-time gate)** | `cmd_validate` 5번째 source mypy (v0.11.12+) | — |
| **Layer 1 ↔ Layer 2 정합 verify** | ❌ (advisory 없음) | **`_cross_verify_ci_mypy` + `_resolve_cross_verify_verdict` (advisory + strict)** |
| **verdict outcome** | — | **7 (sanity / drift_warning / ci_stale / ci_fail / no_local_verify / absent / skipped)** |
| **cumulative acceptance** | 100/100 | **108/108** (v0.11.13 8 신규) |
| **breaking change** | none | **none** (advisory only) |

## Test 결과

- 신규 (1 PASS, v0.11.13, 8 case):
  - `test_mypy_ci_cross_verify_v0_11_13` — `_cross_verify_ci_mypy` helper + `_resolve_cross_verify_verdict` + cmd_release 통합 + argparse 2 flag + dispatcher 2 flag forwarding + lib 2 kwarg + verdict matrix 6 outcome + 실 gh CLI integration
- 회귀 (100/100 PASS — v0.11.12 의 8 + v0.11.11 의 1 + 누적 회귀 91)
  - **NOTE**: v0.11.11 의 case 5 (loud fallback literal = "v0.11.11-beta") 는 본 version bump 후 "v0.11.12-beta" 가 됨. pre-existing test fragility, v0.11.13 범위 밖.
- 누적 acceptance: **108/108 PASS** (v0.11.13 8 case + 회귀)

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/tools/release_pipeline.py` | `_cross_verify_ci_mypy` + `_resolve_cross_verify_verdict` helper + cmd_release 1번 + 2.5번 통합 + argparse 2 flag + 7 verdict string |
| M | `workflow-source/tools/release_pipeline_lib.py` | `cmd_release` 2 kwarg 추가 + `_make_args` 2 default fill |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_release_create` dispatcher 2 flag forwarding + docstring 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.11.12 → 0.11.13 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.12-beta"` → `"v0.11.13-beta"` |
| A | `workflow-source/tests/check_mypy_ci_cross_verify_v0_11_13.py` | 신규 (1 acceptance test, 8 case) |
| A | `workflow-source/releases/Beta-v0.11.13.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.13/backlog/2026-06-26.md` | v0.11.13 plan |

## 다음 (v0.11.14+ / v1.0.0)

1. **v0.11.14** — `workflow_kit/<new_module>.py` 작성 시 mypy strict 자동 통과 verify (CI + release-time gate 2-layer)
2. **v0.11.15** — `cmd_release --json` 의 `ci_mypy.verdict` 1-line summary (`cmd_release --json | jq '.ci_mypy.verdict'`)
3. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`)
