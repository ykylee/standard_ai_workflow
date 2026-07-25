# Beta v0.11.11 — Mypy strict CI 통합 (GH Actions mypy-strict workflow) (2026-06-26)

> **SemVer patch** (v0.11.10 → v0.11.11) — v0.11.10 release note 의 "다음" §1 follow-up. **🎯 Mypy strict CI 통합**: v0.11.10 의 "mypy workflow_kit/ exit 0 (FULL STRICT 도달)" 를 **CI 강제** — PR merge 전 strict regression 차단 + 누적 strict clean 35 file 유지 verify. v0.8.0 spec §5.3 정공법 정합. **PyPI 배포: no** (GitHub Releases only).

## 핵심 추가 (1 신규 CI workflow + 1 acceptance test + mypy pin 정합 + version bump)

### 1. `.github/workflows/mypy-strict.yml` 신규 (CI 통합)

v0.11.10 의 FULL mypy strict 도달 을 CI 강제:

- **Triggers**: `push` to main + `pull_request` to main + `workflow_dispatch` (smoke / mkdocs / okf-validate 와 정합한 main-only 정책)
- **Python**: 3.10 (workflow_kit `python_version` 정합)
- **mypy**: 2.1.0 (v0.11.10 release note 의 strict 기준 정합)
- **Mypy invocation**: `mypy --no-incremental workflow-source/workflow_kit/` (**cwd = REPO_ROOT**, 절대경로로 명시). sub-package 의 `workflow_kit/pyproject.toml` (`strict=false`) 와 parent 의 `workflow-source/pyproject.toml` (`strict=true`) 의 merge 가 발생하지 않도록 *target path* 를 REPO_ROOT 기준 절대경로로 명시.
  - **Critical lesson**: `cd workflow-source && mypy workflow_kit/` (subdir 상대경로) 는 mypy 가 `workflow_kit/pyproject.toml` (`strict=false`) 을 발견하여 parent 의 `strict=true` 와 merge — strict check cascade 가 풀려 46 errors in 18 files 가 발생. REPO_ROOT 절대경로 invocation 은 이 merge 회피.

> ### ⚠️ 정정 (v1.0.2, 2026-07-25) — 위 "Critical lesson" 의 인과 설명은 틀렸다
>
> 세 가지가 사실이 아니다.
>
> 1. **mypy 는 config 를 merge 하지 않는다.** 정확히 하나만 고른다. "두 pyproject 의
>    merge" 라는 현상 자체가 존재하지 않는다.
> 2. **발견된 config 는 sub-package 것이 아니었다.** mypy 의 탐색은 *target* 이 아니라
>    *cwd* 기준이다. `cd workflow-source` 에서 걸리는 것은 `workflow-source/pyproject.toml`
>    (`strict=true`) 이고, `workflow_kit/pyproject.toml` 은 어느 경로로도 읽히지 않았다.
>    `mypy -v` 의 `Config File:` 줄로 확인된다.
> 3. **따라서 "REPO_ROOT 절대경로 invocation" 은 merge 회피가 아니라 설정 상실이었다.**
>    REPO_ROOT 의 `pyproject.toml` 은 의도된 root-level placeholder scaffold(`eb62f37`)라
>    `[tool.mypy]` 가 없어 탐색이 전부 실패하고 `Config File: Default` 로 떨어진다.
>    46 → 0 은 코드가 좋아져서가 아니라
>    **strict 를 아예 적용하지 않게 되어서**였다.
>
> 결과적으로 `mypy-strict.yml` 은 v0.11.11(2026-06-26) 이래 **strict 로 돈 적이 없다.**
> v0.11.12 의 release-time gate 도 같은 invocation 을 복제해 같은 상태였다.
> v1.0.2 에서 `--config-file` 명시로 고쳤고, `Config File:` 줄을 실제로 확인하는
> `check_mypy_config_actually_loaded.py` 를 두어 같은 방식으로 다시 조용해지지 않게 했다.
>
> 남길 교훈은 원문과 반대다: **cwd 에 의존하는 암묵적 config 탐색을 쓰지 말 것.**
> 그리고 초록불이 무엇을 근거로 초록인지 — 어떤 설정으로 쟀는지 — 를 산출물에 남길 것.
- **기존 workflow 정합**:
  - `smoke.yml` — `check_*.py` subprocess 실행 (느림, mypy wrapper 경유)
  - `mypy-strict.yml` (본 release) — direct `mypy` 실행 (빠름, dedicated)
  - 둘 다 CI 에서 동작 (smoke = 회귀 verify / mypy-strict = strict maintain)

### 2. dev extra mypy pin 정합 (`mypy>=1.0` → `mypy==2.1.0`)

**`workflow-source/workflow_kit/pyproject.toml` 의 dev extra**:
```toml
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.1",
    "mypy==2.1.0",  # v0.11.10 strict 기준 정합 (이전: mypy>=1.0)
]
```

**근거**: v0.11.10 release note 가 mypy 2.1.0 strict 기준. CI 가 `mypy==2.1.0` install + local dev 가 `mypy>=1.0` install 이면 strict 결과 drift 가능. CI/local 정합 = pin 통일.

### 3. version bump 0.11.10 → 0.11.11

- `workflow-source/pyproject.toml` `[project] version`: `"0.11.10"` → `"0.11.11"`
- `workflow-source/workflow_kit/__init__.py` loud fallback: `"v0.11.10-beta"` → `"v0.11.11-beta"`
- `__version__` 3-tier fallback (pyproject → importlib.metadata → loud fallback) 자동 derive
- cumulative strict clean = **35 file 유지** (v0.11.10 도달 후 신규 file / strict cleanup 0, 회귀 영향 ❌)

## 운영 누적 (v0.11.10 → v0.11.11)

| | v0.11.10 | **v0.11.11** |
|---|---|---|
| **SemVer bump** | patch | **patch** |
| **CI integration** | smoke (via check_*.py) | **smoke + dedicated mypy-strict** |
| **mypy strict clean file** | 35 | **35** (회귀 ❌) |
| **전체 workflow_kit/ strict error** | 0 errors in 106 files | **0 errors in 106 files** (CI 강제) |
| **mypy pin** | `>=1.0` | **`==2.1.0`** (CI + local 정합) |
| **cumulative acceptance** | 90/90 | **92/92** (v0.11.11 1 신규, 8 case) |
| **breaking change** | none | **none** (CI + pin 만) |

## Test 결과

- 신규 (1 PASS, v0.11.11):
  - `test_mypy_strict_ci_v0_11_11` — `.github/workflows/mypy-strict.yml` 신규 + valid YAML + trigger (push to main + PR to main) + mypy invocation (`mypy --no-incremental workflow-source/workflow_kit/`) + python 3.10 + mypy 2.1.0 pin + dev extra mypy pin ==2.1.0 + loud fallback = v0.11.11-beta + cumulative strict clean 35 file 유지 + pyproject version 0.11.11 + **CI invocation 실제 mypy 실행 exit 0 verify** (8 case)
- 회귀 (90/90 PASS)
- 누적 acceptance: **92/92 PASS**

## 변경 파일 (4 변경 + 3 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow-source/pyproject.toml` | version 0.11.10 → 0.11.11 |
| M | `workflow-source/workflow_kit/pyproject.toml` | dev extra mypy `>=1.0` → `==2.1.0` |
| M | `workflow-source/workflow_kit/__init__.py` | loud fallback `"v0.11.10-beta"` → `"v0.11.11-beta"` |
| A | `.github/workflows/mypy-strict.yml` | 신규 (CI workflow) |
| A | `workflow-source/tests/check_mypy_strict_ci_v0_11_11.py` | 신규 (1 acceptance test) |
| A | `workflow-source/releases/Beta-v0.11.11.md` | release note (본 file) |
| A | `ai-workflow/memory/release/v0.11.11/backlog/2026-06-26.md` | v0.11.11 plan |

## 다음 (v0.11.12+ / v1.0.0)

1. **v0.11.12** — `cmd_release --full-auto` 의 mypy strict pre-check 통합 (release pipeline 자체에 mypy 0 errors gate 추가). 본 release 의 CI workflow 가 1차 방어선이라면, v0.11.12 는 release-time gate.
2. **v0.11.13+** — `workflow_kit/<new_module>.py` 작성 시 mypy strict 자동 통과 verify (CI 가 1차 방어선).
3. **v1.0.0** — full mypy strict milestone release (SemVer major 정렬, `__version__` = `v1.0.0`).
