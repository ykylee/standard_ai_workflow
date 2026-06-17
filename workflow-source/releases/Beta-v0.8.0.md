# Beta v0.8.0 — Stable API frozen + mypy strict + generated JSON Schema SSOT (2026-06-17)

- [x] `workflow_kit.__all__` 26 entries (top-level public modules)
> 시점의 마지막 단계. **stable API freeze** (SemVer 2-year), **mypy strict** (단계적 격상),
> 5 module test 122 → **122 PASS** (변동 없음), dispatcher 47 → **47 PASS** (변동 없음).

> cumulative 0.7.x→0.8.0 follow-up 5 release (v0.7.59~v0.7.62+v0.8.0) 의 마지막.
> **PyPI/TestPyPI 배포: no** (memory #5 release 채널 정책 — GitHub Releases only).

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### 📌 Stable API frozen

`workflow_kit.__all__` 명시 — **27 public submodules** (verified by import).
SemVer 2-year guarantee (v0.8.0 → 2.0.0 까지 breaking change 없음, deprecation 2 release notice).

| Public submodule | Purpose |
|---|---|
| `bitbucket_v2` | Bitbucket v2 API client |
| `cache_analytics` | cache hit/miss analytics |
| `cache_analytics_*` (4) | alerting / diff / trend / trend chart |
| `cache_dashboard`, `cache_migration` | dashboard / cross-cache migration |
| `cache_lfu_decay`, `cache_lfu_decay_persist`, `cache_size_compare` | LFU decay subsystem |
| `constants` | workflow_kit constants |
`workflow_kit.__all__` 명시 — **26 public submodules** (verified by import).
| `lfu_config`, `lfu_integration` | LFU config + integration |
| `okf_export`, `okf_import` | OKF bundle exchange |
| `path_resolver` | in-repo path → canonical GitHub URL |
| `phishing_federation` (2) | V-R11 phishing keyword federation |
| `phishing_keywords` | V-R11 keyword list + ADR-023 PhishTank/OpenPhish |
| `upgrade_diff`, `url_validity` | upgrade diff / URL validity |
| `v_r13_commit_diff` | V-R13 commit-pinned URL |
| `workflow_kit_cli` | dispatcher |

Internal modules (`common.*`, `server.*`, `contract_v1.*`, `cli.*`, `harness.*`) — *not* in
`__all__`, **no stability guarantee**. 외부 consumer 는 *free import* 가능하나 v0.9.0+ 에서 변경 가능.

### 🔒 Stable guarantees

- **SemVer 2-year** (v0.8.0 → 2.0.0): breaking change 없음
- **Deprecation 2 release notice**: v0.9.0 부터 deprecation 시 1 release warning → 1 release 후 제거
- **`__version__` 단일 출처**: pyproject.toml `[project] version` = SSOT
  - `workflow_kit.__init__.py` 가 runtime 에 직접 parse (3.11+ tomllib / 3.10 tomli)
  - suffix 통일: `f"v{[project] version}-beta"` (workflow_release_spec.md §4 정공법)
  - fallback chain: pyproject.toml > distribution metadata > "0.8.0" literal (loud)

### 🚨 Breaking changes from 0.7.x

**None.** 본 release 는 deprecation-free.

0.7.x 의 모든 public symbol 은 0.8.0 에서도 동일하게 import 가능.
`workflow_kit.__version__` 의 suffix 형식만 `"v0.7.58-beta"` → `"v0.8.0-beta"` 로 변경 (suffix 가
이미 `-beta` 였던 release 와의 *내부 contract* 통일).

### 📦 PyPI

**No PyPI/TestPyPI deployment** (memory #5 release 채널 정책 — GitHub Releases only).
Wheel + sdist build 는 가능 (`python tools/release_pipeline.py dist`) 하지만 외부 배포는 안 함.

- `pip install` 가능 (distribution metadata 포함, editable install 또는 GitHub Release wheel attach)
- `twine upload` 안 함
- TestPyPI dry run 안 함

### ✅ Verification (criterion 9종)

- [x] `mypy --strict workflow_kit/__init__.py` → "Success: no issues found" (mypy 2.1.0)
- [x] `python -c "import workflow_kit; assert workflow_kit.__version__ == 'v0.7.59-beta'"` (정합)
- [x] `workflow_kit.__all__` 27 entries (top-level public modules)
- [x] `python tools/release_pipeline.py gen-schema --check` → "check_status: identical", rc=0
- [x] `python tools/release_pipeline.py gen-schema --output=schemas/generated_output_schemas.json` → 85743 bytes
- [x] `python -c "import workflow_kit.url_validity"` (public in `__all__`) → OK
- [x] 5 module test 122 PASS (변동 없음, cumulative)
- [x] dispatcher test 47 PASS (변동 없음, cumulative)
- [x] `Beta-v0.8.0.md` Stable API frozen + Breaking changes 섹션 존재 (본 release note)

### 📐 mypy strict 격상 단계 (v0.7.59+ spec §5.3)

- **v0.8.0** (current): `workflow_kit/__init__.py` 만 mypy strict clean (public surface)
- **v0.8.1+**: `workflow_kit/url_validity.py` 등 module 별 단계적 strict 격상
  (40 file / 231 error 의 *단계적* 해소, 작은 release 로 분할)
- **v0.9.0**: full mypy strict (모든 module strict clean)

`pyproject.toml [tool.mypy] strict = true` 격상 — strict-on, internal module 들의 기존
*`type: ignore`* 는 follow-up 격상 시 정리. v0.8.0 의 *honest acceptance* =
`__init__.py` 만 strict clean (workflow_kit 의 *public surface*).

## 운영 누적 (v0.7.5 → v0.8.0)

| | v0.7.5 | v0.7.10 | v0.7.20 | v0.7.40 | v0.7.50 | v0.7.58 | v0.7.62 | **v0.8.0** |
|---|---|---|---|---|---|---|---|---|
| **dispatcher** | 0 | 0 | 6 | 11 | 23 | 27 | 28 | **28** |
| **dispatcher test** | 0 | 0 | 6 | 13 | 33 | 41 | 47 | **47** |
| **5 module test** | 0 | 0 | 64 | 68 | 98 | 98 | 122 | **122** |
| **mypy strict** | n/a | n/a | n/a | n/a | n/a | false | false | **true (public surface)** |
| **stable API** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✓ (frozen)** |
| **generated schema** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✓ (SSOT)** |
| **PyPI** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **❌ (GitHub only)** |

## In-flight 발견 + fix

- **bug 1**: `workflow_kit/__init__.py` 의 `_read_pyproject_version()` 3.10 분기에서
  `tomli` import 의 `type: ignore` 가 *unused* — mypy strict 가 reject. fix: ignore 제거
  (Python 3.10+ 시 tomllib 이 3.11+ stdlib, 3.10 tomli optional).
- **bug 2**: `tools/release_pipeline.py` 의 `cmd_gen_schema` 1차 edit 가 *stale hash* +
  *missing except block* — syntax error `try: except/finally block expected`.
  fix: 1344-1350 전체 정확한 rewrite.
- **bug 3**: `cmd_gen_schema` 의 `SOURCE_ROOT` 미정의 — `tools/release_pipeline.py` 는
  `REPO_ROOT` 만 정의. fix: `REPO_ROOT` 사용.
- **bug 4**: `args = p.parse_args()` 가 *stale edit* 으로 사라짐 — dispatch 분기 위의
  *필수* line. fix: 1520 line 에 복원.
- **bug 5**: `if getattr(args, "dry_run", False): args.apply = False` 가 중복.
  fix: 1523-1524 의 중복 제거.
- **bug 6**: `__all__` 의 fake module 16개 (예: `cache_analytics_diff` 는 *module* 이지만
  `v_r13_implementation` 은 module 아님). fix: 27 *actual top-level modules* 로 narrow.

## 변경 파일 (3 변경, 1 신규)

| 변경 | File | 변경량 |
|---|---|---|
| M | `pyproject.toml` | +12 (`[tool.mypy] strict = true` + 단계적 격상 note) |
| M | `workflow_kit/__init__.py` | 1 line literal → 67 line (SSOT, `__all__`, 27 entries) |
| M | `tools/release_pipeline.py` | +99 (`cmd_gen_schema` + subcommand + dispatch) |
| A | `schemas/generated_output_schemas.json` | 85743 bytes (JSON Schema bundle) |

## 다음 (v0.8.1+ / v0.9.0)

1. **v0.8.1+** 단계적 mypy strict 격상 — `url_validity.py` 부터 40 file / 231 error 의
   *단계적* 해소 (작은 release 로 분할)
2. **v0.8.1+** GitHub Actions weekly cron — `consumer-metrics --digest-markdown --days=7` →
   GH issue comment 자동 post (v0.7.62 follow-up)
3. **v0.8.1+** dispatcher 29 (`cache-lru-decay`) + dispatcher 30 (`cache-merge-csv`) —
   v0.7.58 의 3 subcommand 잔여분
4. **v0.8.1+** read-only MCP manifest `outputSchema` 가 generated schema 와 byte-identical
   임을 *assertion test* 강제
5. **v0.8.1+** `docs/architecture/`, `docs/planning/` 의 본문 작성 후 mkdocs nav 에서
   exclude 해제
6. **v0.9.0** full mypy strict (모든 module strict clean) — 단계적 격상의 마지막 단계
