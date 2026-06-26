# Beta v0.11.15 — Release summary 1-line (jq-friendly verdict) (2026-06-26)

> **SemVer patch** (v0.11.14 → v0.11.15) — v0.11.14 release note 의 "다음" §1 follow-up. **`cmd_release` + `cmd_release_status` 의 JSON output 에 `summary` 1-line field 추가** (jq-friendly grep/pipe). `cmd_release --json | jq -r .summary` / `cmd_release_status --json | jq -r .summary` 로 1-line 정합 verify 가능. read-only, breaking change 없음. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (2 summary helper + 모든 cmd_release return wrap + 1 acceptance test)

### 1. `_summarize_release_status` helper (release_status.py)

`cmd_release_status` 결과 dict → 1-line summary string:
```
ci_mypy=<verdict>, local_mypy=<ok|FAIL>, ready=<true|false>, next=<X.Y.Z>, unreleased=<count>
```

5-field stable order, no space in value, grep / pipe / jq friendly.

**Example**:
```
ci_mypy=ci_sanity, local_mypy=ok, ready=false, next=0.11.15, unreleased=0
```

### 2. `_attach_release_summary` helper (release_pipeline.py)

`cmd_release` 결과 dict → `summary` field 추가. 모든 return point (11 site) 에서 호출:
- `validate failed; abort release` early return
- `--strict-cross-verify` hard fail (2 site: ci_stale/ci_fail + final verdict)
- `no dist files found` early return
- `notes_resolution` error
- `release note not found` early return
- `--full-auto` bump fail
- `git push tag` fail
- `gh auth not authenticated`
- `gh release create failed`
- final `return results` (success)

**Format**: `ci_mypy=<verdict>, local_mypy=<ok|FAIL|skipped>, ready=<true|false>, next=<X.Y.Z|->, error=<msg|ok>`

5-field stable order, no space in value, jq-friendly. `--skip-validate` / `--skip-mypy` 시 `local_mypy=skipped` (Layer 2 not checked) + `ci_mypy=no_local_verify` (CI sanity + local skipped) 정합.

### 3. `cmd_release_status` 의 `summary` field 자동 추가

`cmd_release_status` 가 result dict 에 `summary` field 자동 추가:
- text mode: 1-line `summary: ...` 출력
- JSON mode: `summary` field JSON output

## 운영 누적 (v0.11.14 → v0.11.15)

| | v0.11.14 | **v0.11.15** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **summary helper** | ❌ | **✅ (`_summarize_release_status` + `_attach_release_summary`)** |
| **cmd_release --json summary** | ❌ | **✅ 5-field 1-line** |
| **cmd_release_status --json summary** | ❌ | **✅ 5-field 1-line** |
| **jq-friendly** | ❌ | **✅ (`jq -r .summary`)** |
| **cumulative acceptance** | 116/116 | **124/124** (v0.11.15 8 신규) |
| **breaking change** | none | **none** (read-only field 추가) |

## Test 결과

- 신규 (1 PASS, v0.11.15, 8 case):
  - `test_release_summary_v0_11_15` — `_summarize_release_status` 5-field + `cmd_release_status` summary + `cmd_release` 의 `_attach_release_summary` 11 wrap + `--skip-validate` summary + dispatcher text/JSON mode + jq-friendly 5-field parse + full validate sanity + dict mutate
- 회귀 (116/116 PASS)
- 누적 acceptance: **124/124 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/release_status.py` | `_summarize_release_status` helper + `cmd_release_status` summary field 추가 |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | dispatcher `release-status` text mode 에 summary line 추가 |
| M | `workflow-source/tools/release_pipeline.py` | `_attach_release_summary` helper + `cmd_release` 11 return point wrap + cross-verify local_mypy empty → no_local_verify + summary 의 next_v label → "-" 변환 |
| M | `workflow-source/pyproject.toml` | version 0.11.14 → 0.11.15 |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.14-beta"` → `"v0.11.15-beta"` |
| A | `workflow-source/tests/check_release_summary_v0_11_15.py` | 신규 (1 acceptance test, 8 case) |
| A | `workflow-source/releases/Beta-v0.11.15.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.15/backlog/2026-06-26.md` | v0.11.15 plan |

## 다음 (v0.11.16+ / v1.0.0)

1. **v0.11.16** — `cmd_release_status` 의 `ready_to_release` 자동 bump (`--auto-bump` flag, current_version == last_release_tag 일 때 next_version 자동 적용 + version-bump)
2. **v0.11.17** — `summary` field 의 `--format=jsonl` / `--format=kv` 변형 (jq-friendly 외 human-readable)
3. **v0.11.18+** — v1.0.0 spec layer 갱신 (full mypy strict milestone release)
4. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`)
