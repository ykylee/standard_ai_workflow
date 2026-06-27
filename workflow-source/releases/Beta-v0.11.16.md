# Beta v0.11.16 — `cmd_release_status --auto-bump` flag (read-only → opt-in write) (2026-06-27)

> **SemVer patch** (v0.11.15 → v0.11.16) — v0.11.15 release note 의 "다음" §1 follow-up. **`cmd_release_status` 에 `--auto-bump` flag 추가** (current_version == last_release_tag 일 때 자동으로 next_version patch bump + sync_release_hash.py post-step 자동 호출). read-only 모드 (default) 에서 **opt-in write** 로 전환. 명시적 flag 없으면 read-only 유지 (backward-compat). **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 helper + 6 변경 + 1 acceptance test)

### 1. `_run_auto_bump` helper (release_status.py)

in-process `tools/release_pipeline.py cmd_version_bump --patch --apply` 호출. subprocess 가 아닌 in-process import → overhead 0 + 에러 propagation 즉시.

```python
def _run_auto_bump(new_version: str) -> dict[str, Any]:
    """v0.11.16+ --auto-bump 의 actual bump stage.

    Returns:
        {"ok": bool, "new_version": str, "result": dict (cmd_version_bump result),
         "error": str | None}
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from release_pipeline import cmd_version_bump  # type: ignore[import-not-found]
    import argparse
    bump_args = argparse.Namespace(
        patch=True, minor=False, major=False, to=None,
        dry_run=False, apply=True,
        no_init=False, skip_sync_hash=False,
    )
    bump_result = cmd_version_bump(bump_args)
    return {"ok": True, "new_version": new_version, "result": bump_result, "error": None}
```

**post-step 자동 호출** (v0.7.27+ TASK-V0727-001 정합):
- `cmd_version_bump --apply` 가 pyproject.toml + workflow_kit/__init__.py version sync + sync_release_hash.py 자동 호출
- sync_release_hash.py 가 state.json + backlog 의 TBD → HEAD hash 갱신
- git add + `git commit --amend --no-edit` (1 commit 통합)

→ `release-status --auto-bump` 1 회 호출로 version bump + hash sync + amend 통합까지 한 호흡.

### 2. `cmd_release_status` 의 `args.auto_bump` 처리

```python
auto_bump_applied = False
auto_bump_result: dict[str, Any] | None = None
if getattr(args, "auto_bump", False) and last_tag \
        and last_tag.lstrip("v").rstrip("-beta") == current:
    auto_bump_result = _run_auto_bump(next_ver["next"])
    auto_bump_applied = auto_bump_result.get("ok", False)
    if auto_bump_applied:
        # bump 성공 시 current_version 재읽기 + next_version 재계산
        current = _read_pyproject_version()
        next_ver = _suggest_next_version(current)
```

**Triggers 조건**: `args.auto_bump=True` + `last_tag` 존재 + `current_version == last_tag (v-prefix/-beta stripped)`. 이 조건에서만 bump 실행. 다른 조건 (unreleased=0, mypy FAIL, ci verdict not sanity) 에서는 --auto-bump 무시 (bump 만 하고 ready=False 인 무의미 상태 회피).

**auto_bump 후 ready_to_release 자동 True**:
```python
if auto_bump_applied:
    ready = True
    ready_reason = f"auto-bumped to {current} (was {last_tag}); all checks pass + unreleased commits present"
```
bump 성공 = next version 으로 정렬 → 다른 ready 조건 (unreleased/mypy/ci) 이 pass 면 ready=True. 첫 call 의 ready_to_release verdict 가 *bump 후의 정합* 반영.

### 3. `_summarize_release_status` 6-field 확장 (v0.11.15+)

v0.11.15 의 5-field (`ci_mypy` / `local_mypy` / `ready` / `next` / `unreleased`) 에 v0.11.16+ `auto_bump` field 추가:

```
ci_mypy=ci_sanity, local_mypy=ok, ready=true, next=0.11.17, unreleased=1, auto_bump=skipped
```

- `auto_bump=skipped`: `--auto-bump` flag 없거나 current != last_tag (bump 불필요)
- `auto_bump=applied`: `--auto-bump=True` + bump 성공
- `auto_bump=failed`: `--auto-bump=True` + bump 실패 (error message 별도)

값에 space 없음, jq-friendly 정합 유지.

### 4. dispatcher `release-status --auto-bump` flag

```python
@register("release-status")
def cmd_release_status(argv: list[str]) -> int:
    """Release pipeline status aggregator (v0.11.14+, read-only, subcommand 35).

    v0.11.16+: --auto-bump flag 추가. current_version == last_release_tag 분기에서
    자동으로 next_version (patch) bump + post-step sync_release_hash.py 자동 호출.
    write 발생 (read-only 깨짐). 명시적 opt-in.
    ...
    Args:
        --json          JSON output
        --auto-bump     v0.11.16+: current_version == last_release_tag 일 때
                        자동으로 next_version (patch) 적용. in-process
                        cmd_version_bump --patch --apply 호출 +
                        sync_release_hash.py post-step 자동 호출.
    """
    use_json = _has_flag(argv, "--json")
    auto_bump = _has_flag(argv, "--auto-bump")
    args = argparse.Namespace(auto_bump=auto_bump)
    result = _impl(args)
```

text mode 의 추가 출력:
- `auto_bump_applied: True|False`
- `auto_bump.new_version: <X.Y.Z>` (성공 시)
- `auto_bump.error: <msg>` (실패 시)

### 5. `__init__.py` 의 cumulative mypy strict clean 갱신

v0.11.14 36 file strict clean 유지 (v0.11.16 = 기존 release_status.py 의 in-place 확장, 신규 file 0). docstring 에 v0.11.16 entry 추가:

```python
- v0.11.16 누적: 36 file strict clean (유지)
  v0.11.14 36 + v0.11.16 28단계 (release_status.py --auto-bump 확장, 신규 file 0)
  = 36 file (기존 release_status.py 의 in-place 확장)
```

loud fallback literal `v0.11.15-beta` → `v0.11.16-beta` 갱신.

## 운영 누적 (v0.11.15 → v0.11.16)

| | v0.11.15 | **v0.11.16** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **`--auto-bump` flag** | ❌ | **✅ (current==last_tag 분기 자동 bump)** |
| **read-only → opt-in write** | read-only | **opt-in write** (default read-only 유지) |
| **in-process cmd_version_bump** | ❌ | **✅ (subprocess 0)** |
| **sync_release_hash post-step 자동** | ❌ (release 시만) | **✅ (--auto-bump 시 자동)** |
| **summary field 수** | 5 | **6** (`auto_bump` 추가) |
| **cumulative acceptance** | 124/124 | **132/132** (v0.11.16 8 신규) |
| **breaking change** | none | **none** (--auto-bump 명시 opt-in) |

## Test 결과

- 신규 (1 PASS, v0.11.16, 8 case):
  - `test_release_status_auto_bump_v0_11_16` — release_status._run_auto_bump helper + --auto-bump 처리 + result dict field 추가 + dispatcher --auto-bump flag + args forwarding + docstring v0.11.16/auto-bump + cmd_release_status default 호출 schema 11 key + summary 6-field + mypy strict clean 107 source files + dispatcher text/JSON mode 양쪽 + default auto_bump_applied=False + mock _run_auto_bump applied scenario (auto_bump_applied=True + current re-read + next_version 재계산 + ready_to_release=True + summary auto_bump=applied)
- 회귀 (124/124 PASS)
- 누적 acceptance: **132/132 PASS**

## 변경 파일 (7 변경 + 2 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/workflow_kit/release_status.py` | `_run_auto_bump` helper + `cmd_release_status` args.auto_bump 처리 + auto_bump_applied/auto_bump_result result field + `_summarize_release_status` 6-field 확장 + docstring 갱신 + r-string (escape warning fix) |
| M | `workflow-source/workflow_kit/workflow_kit_cli.py` | dispatcher `release-status` body `_has_flag(argv, "--auto-bump")` parsing + `args.auto_bump` forwarding + auto_bump_applied/result text mode 출력 + docstring v0.11.16/auto-bump 명시 |
| M | `workflow-source/workflow_kit/__init__.py` | docstring v0.11.16 cumulative entry 추가 + loud fallback `"v0.11.15-beta"` → `"v0.11.16-beta"` |
| M | `workflow-source/pyproject.toml` | version 0.11.15 → 0.11.16 |
| M | `workflow-source/tests/check_release_status_v0_11_14.py` | case 8 시간 의존적 assertion ("방금 v0.11.13 release 후" hard-coded) 제거 → conditional assertion (current==last_tag 면 ready=False, 아니면 다른 분기 검증). v0.11.14 release 직후 시나리오 + 다음 release 진행 중 시나리오 둘 다 handle. **in-scope regression fix (v0.11.16 회귀 누적 방지)** |
| M | `workflow-source/tools/release_pipeline.py` | `cmd_release` entry 에 args normalize 추가 — release subcommand argparse 의 attribute 와 cmd_validate 가 기대하는 attribute 비대칭 fix. memory #11 의 `_make_args` 정공법 정합. **in-scope release pipeline fix (cmd_release --full-auto 호출 가능)** |
| M | `workflow-source/workflow_kit/release_status.py` (regression) | docstring r-string prefix (`\`` escape warning fix, v0.11.15 release 직전 backport) |
| A | `workflow-source/tests/check_release_status_auto_bump_v0_11_16.py` | 신규 (1 acceptance test, 8 case) |
| A | `workflow-source/releases/Beta-v0.11.16.md` | release note (본 file) |

## 다음 (v0.11.17+ / v1.0.0)

1. **v0.11.17** — `summary` field 의 `--format=jsonl` / `--format=kv` 변형 (jq-friendly 외 human-readable)
2. **v0.11.18+** — v1.0.0 spec layer 갱신 (full mypy strict milestone release)
3. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`)