# Beta v0.7.57 — <in-memory> cleanup + dispatcher 26 + mkdocs cross-link audit (2026-06-16)

> v0.7.56 의 3 follow-up 동시 해결: (1) cache_lfu_decay <in-memory> artifact 정공법 +
> (2) dispatcher 23 → 26 (cache format interop 3 신규) + (3) mkdocs cross-link audit
> standalone script.
> 5 module test 83 → **98 PASS** (+15 신규). 4 commit, 1 신규 file, 1 신규 page.

## 핵심 추가 (3 follow-up, 4 commit, 15 신규 test, 1 신규 script)

### 1. <in-memory> artifact cleanup (memory rule 8 fix)

v0.7.55 의 score-wiki-trend 가 `<in-memory>` literal cache_path 를 사용했음. v0.7.56 에서
cmd_score_wiki_trend 를 in-process 전환했지만, v0.7.55 의 `cache_lfu_decay.py:72` 와
`check_cache_lfu_decay.py:47` 가 같은 literal 을 사용 — *매 test 실행 마다*
`workflow-source/<in-memory>` 파일이 생성되어 commit 에 포함될 위험.

v0.7.57 정공법: **API 변경 + caller 변경 2 곳**.

- `save_cache_with_decay(cache, cache_path: str | None, config)`:
  - `None` = compute scores only, no file write
  - caller 가 *compute-only* vs *persist* 의도 type 으로 명시
- `select_eviction_candidates_with_decay`: `cache_path=None` (no file write)
- `check_cache_lfu_decay.py`: `cache_path="<in-memory>"` → `cache_path=None`

**Cross-ref**: memory rule 8 (3-layer failure separation) — v0.7.55 의
*unintentional file artifact* 가 v0.7.57 의 *type-level intent expression* 로
replaced. test artifact 더 이상 commit 위험 없음.

### 2. dispatcher 23 → 26 (cache format interop)

| # | Subcommand | Source | Use case |
|---|---|---|---|
| 24 | `cache-merge-multi` | `cache_migration.merge_per_strategy_to_mixed` | LRU + LFU → mixed (reverse of split) |
| 25 | `cache-import-csv` | `cache_migration.import_csv_to_cache` | external CSV (url, status, timestamp, access_count) → cache |
| 26 | `cache-export-json` | `cache_migration.export_cache_to_json` | cache → standalone JSON (share / archive) |

**Helper 3 신규** (`workflow_kit/cache_migration.py`):
- `merge_per_strategy_to_mixed(base_path, delete_sources=False)`:
  LRU + LRU override on conflict (LFU more-recent/more-used) → mixed file
- `import_csv_to_cache(csv_path, cache_path=None, merge=True)`:
  4-column CSV (url, status, timestamp, access_count), skip empty url
- `export_cache_to_json(output_path, cache_path=None, pretty=True)`:
  standalone flat dict format

**Destructive subcommand**: `cache-merge-multi --delete-sources`,
`cache-import-csv --replace` 모두 명시적 flag. default safe.

### 3. mkdocs cross-link audit (v0.7.53 follow-up)

v0.7.53 의 mkdocs 셋업 NOTE: `--strict OFF` — many cross-links between
docs/*.md and ai-workflow/wiki/*.md (wiki 는 mkdocs docs_dir 외부).
follow-up: *move wiki pages to docs/wiki/ or configure mkdocs-multirepo*.

v0.7.57 의 *pragmatic fix* — standalone script:

**`scripts/audit_mkdocs_links.py`** (130+ line):
- `--docs=PATH` (default: docs/) recursive walk
- default exclude: **samples/** (self-contained OKF bundle), **archive/** (history)
- Markdown link `[text](path)` 파싱 — http/https/mailto/anchor/fragment 제외
- **Code block strip**: ` ``` ` fence 와 inline `` ` `` code 안의 link 무시
  (heredoc 안의 example link 가 false positive 안 되도록)
- target file exists? 검증 → broken link report (source, link, resolved)
- `--json`: JSON output
- rc: 0 = all valid, 1 = broken, 2 = usage error

**Workflow 통합** (`.github/workflows/mkdocs.yml`):
- 'Cross-link audit' step 추가 (build 직전)
- main docs 의 broken link 정공법
- mkdocs `--strict` 는 여전히 OFF (wiki/ 외부 issue 는 follow-up)

**Fix**:
- `docs/PROJECT_PROFILE.md` 의 stale `work_backlog.md` link →
  `archive/2026-06-12/work_backlog.md` (실제 위치)
- 4 broken → **0 broken** (public-facing docs 한정)

**Test** (`check_audit_mkdocs_links.py`, 5 test):
- clean docs → rc 0
- broken link → rc 1 + JSON report
- code block link → ignored
- excluded dir → skipped
- absolute URL → ignored

## 운영 누적 (v0.7.52 → v0.7.57)

| | v0.7.52 | v0.7.53 | v0.7.54 | v0.7.55 | v0.7.56 | **v0.7.57** |
|---|---|---|---|---|---|---|
| **dispatcher** | 6 | 8 | 11 | 14 | 23 | **26** |
| **dispatcher test** | 6 | 9 | 13 | 20 | 33 | **38** |
| **5 module test** | 64 | 68 | 68 | 68 | 83 | **93** |
| **cache_lfu_decay test** | 2 | 2 | 2 | 2 | 4 | **4** (cleanup) |
| **cache_migration test** | 1 | 2 | 2 | 2 | 2 | **5** (3 신규) |
| **mkdocs link audit** | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| **<in-memory> artifact** | ❌ | ❌ | ❌ | ⚠️ leak | ⚠️ leak | **✅ fix** |
| **GH Pages** | ❌ | ✅ | ✅ | ✅ | ✅ (FEEDBACK) | ✅ |

## In-flight 발견 + fix

- **bug 1**: `cache_lfu_decay.py:72` 의 `<in-memory>` literal cache_path → `None` (None-based design)
- **bug 2**: `check_cache_lfu_decay.py:47` 의 `<in-memory>` literal → `None` + 새 test (`test_save_cache_with_decay_persists_v0_7_47`)
- **bug 3**: `docs/PROJECT_PROFILE.md` 의 stale `work_backlog.md` link → `archive/2026-06-12/work_backlog.md` (실제 위치)
- **bug 4**: `mkdocs build` 의 `site/` output 이 commit 에 포함됨 → `.gitignore` 에 `/site/` 추가 + amend

## Test 결과

- `check_workflow_kit_cli.py`: 33/33 → **38/38** PASS (+5 신규)
- `check_url_validity.py`: 14/14 PASS (변동 없음)
- `check_okf_import.py`: 25/25 PASS (변동 없음)
- `check_release_pipeline_lib.py`: 7/7 PASS (변동 없음)
- `check_cache_lfu_decay_persist.py`: 4/4 PASS (변동 없음)
- `check_cache_migration.py`: 2/2 → **5/5** PASS (+3 신규)
- `check_audit_mkdocs_links.py`: **5/5** PASS (NEW)
- **cumulative 5 module test**: 83 → **98 PASS** (+15, 18% 증가)

## 다음 (v0.7.58 / v0.7.60)

1. consumer feedback 1차 metric — GitHub Pages traffic tab dashboard hook
2. 5 module audit 4차 (path_resolver / phishing_keywords 정합)
3. dispatcher 28+ (cache-{lru-decay,lfu-decay-persist,merge-csv} 추가)
4. mkdocs `--strict` 진짜 활성화 (wiki mirror 또는 multirepo)
5. v0.8.0 candidates 정리 (PyPI / stable API / mypy strict / schema)
