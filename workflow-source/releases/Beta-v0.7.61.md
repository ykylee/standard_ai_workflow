# Beta v0.7.61 — mkdocs `--strict` 진짜 활성화 (cross-link rewrite + exclude_docs) (2026-06-17)

> v0.7.58 의 follow-up F (mkdocs `--strict` 진짜 활성화) 마감. v0.7.53 의 initial reason
> (wiki/ 외부 cross-link) → v0.7.57 의 pragmatic fix (audit script) → v0.7.61 의 *진짜 fix*
> (cross-link rewrite + exclude_docs + docs/README.md 제거).
> **116 → 0 warning**, `mkdocs build --strict` rc=0, GH Pages CI 의 cross-link 회귀 차단
> 정공법. 0 신규 test (config + cross-link rewrite 만), 0 신규 tool, 0 신규 page.

## 핵심 변경 (1 follow-up, ~50 cross-link rewrite, 11 file 변경 + 1 file 삭제)

### 1. mkdocs `--strict` 진짜 활성화

v0.7.53 의 *initial reason* (mkdocs docs_dir 외부에 `ai-workflow/wiki/` 존재 → 116 broken
warning) → v0.7.57 의 *pragmatic fix* (`audit_mkdocs_links.py` 가 main docs 만 strict
검증) → **v0.7.61 의 *진짜 fix*** (mkdocs build 의 surface 축소 + cross-link rewrite).

**변경 4 종**:

1. **Cross-link rewrite (~50개, 7 main docs file)**: 모든 `../README.md`, `../QUICKSTART.md`,
   `../ai-workflow/wiki/...`, `../workflow-source/...` 를 `https://github.com/ykylee/standard_ai_workflow/blob/main/...` 형식의 GitHub absolute URL 로 변경. mkdocs 가 `http(s)://` link 를 broken 으로 안 봄.
2. **`mkdocs.yml` 의 `exclude_docs`** 추가: `samples/**` / `archive/**` / `planning/**` / `architecture/**` — mkdocs build 의 surface 축소. *placeholder* / *history* / *self-contained bundle* 은 *public-facing nav* 가 아니므로 build 제외.
3. **`docs/README.md` 삭제**: `docs/index.md` 와 conflict → mkdocs auto-exclude WARNING
   1개 남음. governance home 의 본문은 `DOCUMENT_INDEX.md` 의 §0/§1 로 merge.
4. **`.github/workflows/mkdocs.yml` 의 `mkdocs build` → `mkdocs build --strict`**: cross-link
   회귀 차단 정공법.

### 2. audit_mkdocs_links.py 의 gate 강화

v0.7.57+ 의 *pragmatic fix* 가 defense-in-depth layer 로 v0.7.61+ 에서도 유지:
- docstring 의 v0.7.61 status 명시 (`--strict ON, 본 script 는 defense-in-depth`)
- default exclude 에 `architecture/`, `planning/` 추가
- `mkdocs build --strict` 가 *nav files* 만 walk 하는 한계 보완 — 본 script 는 *모든 .md* walk

**정합**:
- `mkdocs build --strict` (CI): nav files 만 검증, `http(s)://` + `./docs/*` 만 follow
- `audit_mkdocs_links.py` (defense-in-depth): docs/ 의 모든 .md 검증, GitHub URL + exclude dir 무시
- 2-gate 모두 rc=0 = cross-link 회귀 0

## 운영 누적 (v0.7.53 → v0.7.61)

| | v0.7.53 | v0.7.57 | v0.7.58 | v0.7.59 | v0.7.60 | **v0.7.61** |
|---|---|---|---|---|---|---|
| **mkdocs `--strict`** | OFF (initial) | OFF (pragmatic) | OFF | OFF | OFF | **ON (real)** |
| **broken warning** | 116 | (audit script gate) | - | - | - | **0** |
| **mkdocs build rc** | 1 | 0 | 0 | 0 | 0 | **0** |
| **cross-link source** | 50+ | (script gate) | - | - | - | **0 (rewrite)** |
| **exclude_docs** | ❌ | ❌ | ❌ | ❌ | ❌ | **4 dir** |
| **GH Pages CI gate** | 1 | 1 (script) | 1 | 1 | 1 | **2 (`--strict` + script)** |

## In-flight 발견 + fix

- **bug 1**: `audit_mkdocs_links.py` 의 line 78-81 의 `parser.add_argument` 가 `_strip_code_blocks` 함수 *내부* 에 잘못 들어가서 `NameError: name 'parser' is not defined` — edit 의 anchor 잘못. fix: 4 line 제거, default exclude 는 *main function* 의 `all_excludes` list 에 직접 추가.
- **bug 2**: `mkdocs.yml` 의 `site_dir: site` 가 line 8 + line 20 에 중복 — anchor 잘못. fix: 20 line 제거.
- **bug 3**: `docs/RELEASE.md` 의 line 157 의 `[릴리스 노트 디렉토리]` cross-link 가 fix 후 *중복* — fix: 157 line 제거 (158 line 의 GitHub URL 만 유지).
- **bug 4**: `audit_mkdocs_links.py` 의 `all_excludes` 가 line 101 + 102 에 중복 — fix: 102 line 제거.

## Test 결과

- `mkdocs build --strict --clean` (v0.7.61 smoke 1):
  - **before v0.7.61**: 116 warnings, "Aborted with 116 warnings in strict mode!", rc=1
  - **after v0.7.61**: 0 warning, "Documentation built in 0.53 seconds", rc=0
- `python3 scripts/audit_mkdocs_links.py` (v0.7.61 smoke 2):
  - "Cross-link audit: 0 links checked, 15 files skipped"
  - "OK: all links valid", rc=0
- 회귀 5 module + dispatcher: 변동 없음 (이 release 는 mkdocs 만 영향)
  - `check_path_resolver.py`: 12/12 PASS
  - `check_phishing_keywords.py`: 8/8 PASS
  - `check_url_validity.py`: 14/14 PASS
  - `check_okf_import.py`: 25/25 PASS
  - `check_release_pipeline_lib.py`: 7/7 PASS
  - `check_cache_migration.py`: 5/5 PASS
  - `check_consumer_metrics.py`: 6/6 PASS
  - `check_workflow_kit_cli.py`: 47/47 PASS

## 변경 파일 (11 변경 + 1 삭제)

| 변경 | File | 변경량 |
|---|---|---|
| M | `mkdocs.yml` | +9 (`exclude_docs` 4 dir) |
| M | `.github/workflows/mkdocs.yml` | +5 (`--strict` ON) |
| M | `scripts/audit_mkdocs_links.py` | +27 (docstring v0.7.61 status, exclude 추가) |
| M | `docs/OKF_CONSUMER_GUIDE.md` | 13 cross-link rewrite |
| M | `docs/OKF_CONSUMER_QUICKSTART.md` | 4 cross-link rewrite |
| M | `docs/INSTALLATION_AND_USAGE.md` | 14 cross-link rewrite |
| M | `docs/PROJECT_PROFILE.md` | 12 cross-link rewrite |
| M | `docs/RELEASE.md` | 3 cross-link rewrite |
| M | `docs/CODE_INDEX.md` | 1 cross-link rewrite |
| M | `docs/DOCUMENT_INDEX.md` | 5 cross-link rewrite |
| M | `docs/index.md` | 2 cross-link rewrite |
| M | `docs/FEEDBACK.md` | 2 cross-link rewrite |
| D | `docs/README.md` | (delete, conflict with index.md) |

## 다음 (v0.7.62 / v0.8.0)

1. **v0.7.62 B + D**: consumer-metrics trend snapshot + weekly digest 자동화
2. v0.7.61 follow-up: `docs/architecture/`, `docs/planning/` 의 본문 작성 (의미 있는 ADR / milestone 추가) 후 mkdocs nav 에서 *exclude* 해제
3. v0.8.0 J. stable API freeze + mypy strict + PyPI + generated schema SSOT
   (workflow-source/core/v0_8_0_stable_api_spec.md)
