# Beta v0.11.12 — Mypy strict release-time gate (cmd_release pre-check 확장) (2026-06-26)

> **SemVer patch** (v0.11.11 → v0.11.12) — v0.11.11 release note 의 "다음" §1 follow-up. **Release-time mypy strict gate**: v0.11.11 의 CI mypy-strict workflow 가 PR-time 1차 방어선이라면, v0.11.12 는 **release-time 2차 방어선**. `cmd_validate` 의 4 source (packaging/doctor/state/git) 에 **5번째 source `mypy`** 추가 + `cmd_release_create` dispatcher 의 `--skip-mypy` / `--full-auto` / `--allow-existing-tag` forwarding 보강 (in-scope fix). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 cmd_validate source + 3 argparse flag + 1 acceptance test + version bump)

### 1. `cmd_validate` 5번째 source `mypy` 추가 (release-time gate)

v0.11.10 의 FULL mypy strict 도달 (35 file strict clean) 을 release-time 강제:

- **Invocation**: `python3 -m mypy --no-incremental <REPO_ROOT>/workflow_kit/`
  - cwd = `REPO_ROOT.parent` (project root)
  - target = **absolute path** (REPO_ROOT/workflow_kit/)
  - sub-package 의 `workflow_kit/pyproject.toml` (`strict=false`) 와 parent 의 `workflow-source/pyproject.toml` (`strict=true`) 의 merge 회피
- **Result schema**: `{ok, exit_code, error_count, first_error}`
  - mypy 부재 시: `{ok: False, error: "mypy module not installed (run pip install -e ./workflow-source/workflow_kit[dev])"}`
  - timeout 시: `{ok: False, error: "mypy timeout (>120s)"}`
- **CI / local invocation 정합**: v0.11.11 의 `mypy-strict.yml` workflow 와 동일 (= mypy 2.1.0 strict 0 errors 강제)
- **기존 4 source** (`cmd_validate` 의 v0.7.9+ baseline):
  - `check_packaging.py` (pyproject ↔ 디스크 정합)
  - `workflow_kit.cli.doctor` (7 baseline evaluate)
  - `state.json` freshness (last_freeze / last_ingest)
  - `git status` (working tree clean)

### 2. argparse `--skip-mypy` flag (validate subcommand)

- `validate` subcommand 의 4 source skip flag 다음
- `action="store_true"` (default False = mypy check 활성)
- 다른 skip flag 와 일관 (`--skip-packaging` / `--skip-doctor` / `--skip-state` / `--skip-git`)
- `cmd_release` 의 `getattr(args, "skip_mypy", False)` 정합

### 3. `cmd_release_create` dispatcher 3 flag forwarding (in-scope fix)

**기존 dispatcher 가 forwarding 하지 않았던 3 flag** (v0.7.21~v0.9.1 사이의 latent bug):
- `--skip-mypy` (v0.11.12+ 본 release 의 핵심)
- `--full-auto` (v0.9.1+ — pre-check conflict 시 `--auto-bump` / `--allow-existing-tag` 자동 활성화)
- `--allow-existing-tag` (v0.7.21+ — remote tag 가 이미 존재해도 진행)

**근거**: `cmd_release` (release_pipeline.py) 가 `getattr(args, "full_auto", False)` 와 `getattr(args, "allow_existing_tag", False)` 로 flag 를 읽지만, dispatcher 가 forwarding 하지 않아 9 release 동안 모든 호출이 no-op 이었음. 본 release 의 mypy pre-check 과 직접 관련 (`full_auto` 의 release-time 동작 = conflict → auto-bump 또는 allow-existing-tag = pre-check 의 hard fail 우회 = 본 release 의 gate 와 정합).

### 4. `release_pipeline_lib._make_args` 5 source default fill (pre-existing fix)

**기존**: `SimpleNamespace(**kwargs)` — kwargs 에 없는 attribute 는 AttributeError
**변경 후**: validate 관련 5 source skip flag (skip_packaging / skip_doctor / skip_state / skip_git / skip_mypy) + skip_validate 를 default False 로 자동 fill

**근거**: v0.11.11 까지 dispatcher 가 `cmd_release` 호출 시 4 source skip flag 를 전달하지 않아 `args.skip_packaging` AttributeError. 본 release 에서 5 source skip flag 모두 default fill 로 fix.

## 운영 누적 (v0.11.11 → v0.11.12)

| | v0.11.11 | **v0.11.12** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **validate source** | 4 (packaging/doctor/state/git) | **5 (+ mypy)** |
| **release-time mypy gate** | ❌ (CI 만) | **✅ (cmd_release auto-gate)** |
| **dispatcher flag forwarding** | 4 source skip + version + auto-bump + apply | **5 source skip + version + auto-bump + full-auto + allow-existing-tag + apply** |
| **cumulative acceptance** | 92/92 | **100/100** (v0.11.12 8 신규) |
| **breaking change** | none | **none** (pre-check 만 추가) |

## Test 결과

- 신규 (1 PASS, v0.11.12, 8 case):
  - `test_mypy_strict_release_gate_v0_11_12` — `cmd_validate` 5번째 source mypy strict (REPO_ROOT.parent cwd + 절대경로) + argparse `--skip-mypy` flag + mypy source schema (ok/exit_code/error_count/first_error) + `--skip-mypy=True` skipped verify + dispatcher 3 flag forwarding + docstring 정합 + release_pipeline_lib.cmd_release 3 kwarg forwarding + _make_args default
- 회귀 (92/92 PASS)
- 누적 acceptance: **100/100 PASS**

## 변경 파일 (3 변경 + 4 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/tools/release_pipeline.py` | `cmd_validate` 5번째 source mypy 추가 (REPO_ROOT.parent cwd + 절대경로) + argparse `--skip-mypy` + mypy 부재/timeout handling |
| M | `workflow-source/tools/release_pipeline_lib.py` | `cmd_release` 3 kwarg 추가 (skip_mypy / full_auto / allow_existing_tag) + `_make_args` 5 source default fill |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_release_create` dispatcher 3 flag forwarding (--skip-mypy / --full-auto / --allow-existing-tag) + docstring 갱신 |
| M | `workflow-source/pyproject.toml` | version 0.11.11 → 0.11.12 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.11-beta"` → `"v0.11.12-beta"` |
| A | `workflow-source/tests/check_mypy_strict_release_gate_v0_11_12.py` | 신규 (1 acceptance test, 8 case) |
| A | `workflow-source/releases/Beta-v0.11.12.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.12/backlog/2026-06-26.md` | v0.11.12 plan |

## 다음 (v0.11.13+ / v1.0.0)

1. **v0.11.13** — `cmd_release_create --json` 의 `mypy` source 를 GH Actions CI 결과 와 cross-verify (CI OK + local OK = 1차 sanity, CI fail + local OK = drift warning).
2. **v0.11.14+** — `workflow_kit/<new_module>.py` 작성 시 mypy strict 자동 통과 verify (CI + release-time gate 2-layer).
3. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`).
