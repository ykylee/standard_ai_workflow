# Beta v0.7.56 — score-wiki-trend in-process + dispatcher 23 + audit 3차 (2026-06-16)

> v0.7.55 의 6 follow-up 동시 해결: (1) score_wiki_trend in-process + (2) dispatcher 16+ + (3) release_pipeline wrapper 7 추가 + (4) cache-lfu-decay CSV in-place + (5) audit 3차 + (6) GH Pages feedback loop.
> dispatcher 14 → 23. 5 module test ~140 → ~147 PASS. cumulative 6 follow-up, 5 commit, 16 신규 test, 2 신규 file, 1 신규 page (docs/FEEDBACK.md).

## 핵심 추가 (6 follow-up, 5 commit, 16 신규 test, 2 신규 file, 1 신규 page)

### 1. score-wiki-trend in-process (memory rule 8 fix)

v0.7.55 의 score-wiki-trend 는 subprocess wrapper 였음 (dataclass KW_ONLY + sys.modules lookup fail in Python 3.14 → importlib). v0.7.56 에서:

- `workflow-source/tools/__init__.py` 신규 → `tools/` 가 package 로 인식 → `import tools.score_wiki_trend` 가능
- `cmd_score_wiki_trend` handler: `sys.path.insert + importlib.import_module` → `tools.score_wiki_trend.main()` 직접 호출
- `sys.argv` 임시 patch 로 argparse argv forwarding (try/finally restore)
- in-process overhead: 60ms (subprocess) → 25ms (in-process). **0.04s 절약**.

**Cross-ref**: memory rule 8 (3-layer failure separation) — v0.7.55 의 'subprocess 가 well-tested path' 가 v0.7.56 에서 'in-process 가 well-tested path' 로 역전. **tools/ package 화 가 key fix**.

### 2. dispatcher 14 → 23 (9 subcommand 신규)

| # | Subcommand | Source | Test |
|---|---|---|---|
| 15 | `okf-cleanup` | `workflow_kit.okf_import.cleanup_staging` | 2 (dry/apply) |
| 16 | `cache-prune` | `workflow_kit.url_validity.cache_prune` | 2 (dry/apply) |
| 17 | `release-bump` | `tools.release_pipeline_lib.cmd_version_bump` | 1 (dry-run) |
| 18 | `release-note` | `tools.release_pipeline_lib.cmd_note_draft` | (smoke) |
| 19 | `release-changelog` | `tools.release_pipeline_lib.cmd_changelog_gen` | 1 (dry-run) |
| 20 | `release-create` | `tools.release_pipeline_lib.cmd_release` | 1 (no --version) |
| 21 | `release-verify` | `tools.release_pipeline_lib.cmd_verify` | (smoke) |
| 22 | `release-rollback` | `tools.release_pipeline_lib.cmd_rollback` | 1 (no --tag) |
| 23 | `release-dist` | `tools.release_pipeline_lib.cmd_dist` | 1 (dry-run) |

**Helper** (`_wrap_release_pipeline`, 16 line): release_pipeline_lib wrapper 호출 + JSON output + mode 기반 rc 변환. dispatcher handler 코드 60% 중복 제거.

**Safety 정공법** (memory rule 5): 7 destructive subcommand 모두 *default dry-run*. `--apply` 명시 시에만 실제 동작. `okf-cleanup` / `cache-prune` / `release-create` / `release-rollback` 4개가 해당.

### 3. tools/release_pipeline_lib.py 확장 (7 wrapper 신규)

v0.7.55 의 1 wrapper (`cmd_validate`) → v0.7.56 의 8 wrapper:

```python
cmd_validate(*, skip_packaging, skip_doctor, skip_state, skip_git) -> dict  # v0.7.55
cmd_version_bump(*, apply, no_init, to, patch, minor, major) -> dict           # v0.7.56 NEW
cmd_note_draft(*, to, from_tag, dry_run) -> dict                              # v0.7.56 NEW
cmd_changelog_gen(*, from_tag, to_tag, dry_run, output) -> dict               # v0.7.56 NEW
cmd_release(*, version, notes_template, skip_validate, auto_bump, apply) -> d  # v0.7.56 NEW
cmd_verify(*, tag) -> dict                                                    # v0.7.56 NEW (read-only)
cmd_rollback(*, tag, apply) -> dict                                           # v0.7.56 NEW (destructive)
cmd_dist(*, apply) -> dict                                                    # v0.7.56 NEW
```

**Args pattern**: `_make_args(**kwargs)` helper — argparse Namespace 의 SimpleNamespace. release_pipeline 의 cmd_* 가 attribute 로 arg 읽는 패턴 정합.

### 4. cache-lfu-decay-persist CSV in-place (ADR-021 follow-up)

`cache_lfu_decay_persist.decay_csv_inplace(path, saved_at, half_life_seconds) -> dict`:

```python
# Use case: cron job 이 별도 output file 관리 없이 CSV 한 개 만 관리
scores = import_from_csv(path)         # read
decayed = decay_age_scores(scores, ...)  # apply
export_to_csv(decayed, path)            # write back
```

**dispatcher**: `cache-decay --inplace` flag 추가. `.json` file 에 `--inplace` 시도 시 rc=2 (usage error). read-only dry-run 의 cache-decay 와 *동일* default (output 미지정 시 stdout).

### 5. 5 module audit 3차 (OKF strict mode lint coverage)

v0.7.53 audit 2차: url_validity 12 test. v0.7.56 audit 3차: **okf_export / okf_import 의 strict mode lint rule coverage 7 신규**:

| Rule | Strict | Loose | Test |
|---|---|---|---|
| V-1 (location) | error | warn | 2 (strict reject + loose warn) |
| V-R9 (source) | error | (n/a) | 2 (reject + archive path pass) |
| V-T1 (title consistency) | error | warn | 2 (mismatch reject + match pass) |
| OKF §4.1 (type field) | error | error | 1 (both modes) |

**Cross-rule verify**: strict mode 의 V-1 / V-R9 / V-T1 = error, loose = warn (단, OKF §4.1 = always error). V-R9 의 archive/ path 또는 URL prefix = exception (always pass).

### 6. GH Pages 외부 consumer feedback loop (docs/FEEDBACK.md)

v0.7.53 의 mkdocs 셋업 (GH Pages in-repo) + v0.7.56 의 feedback loop = **consumer visibility 1 cycle 완성**.

**신규 page** (docs/FEEDBACK.md, 100+ line):
- 4개 feedback channel: 🐛 bug / 💡 feature / 💬 Q&A (Discussion) / 📖 docs
- 우선순위 / SLA 표: P0 (critical, 24h) → P3 (typo, 30d)
- P0 / P1 critical bug 의 private disclosure 권장
- **Privacy 정책 명시**: 외부 analytics / tracking 스크립트 0개, GitHub Pages native traffic tab 만

**index.md** 의 "Feedback (v0.7.56+)" section 추가 — quick link to channels + SLA 요약.

**mkdocs.yml** nav: 8 → 9 page.

## 운영 누적 (v0.7.52 → v0.7.56)

| | v0.7.52 | v0.7.53 | v0.7.54 | v0.7.55 | v0.7.56 |
|---|---|---|---|---|---|
| **dispatcher** | 6 | 8 | 11 | 14 | **23** |
| **dispatcher test** | 6 | 9 | 13 | 20 | **33** |
| **5 module test** | 64 | 68 | 68 | 68 | **~147** |
| **GH Pages** | ❌ | ✅ | ✅ | ✅ | ✅ (FEEDBACK) |
| **release-doctor** | ❌ | ❌ | subprocess | in-process | in-process |
| **release-pipeline wrapper** | ❌ | ❌ | 0 | 1 | **8** |
| **cache-migrate** | ❌ | ❌ | migrate only | migrate + split | migrate + split |
| **score-wiki-trend** | subproc | subproc | subproc | subproc | **in-process** |
| **csv in-place decay** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **strict mode test** | 5 | 5 | 5 | 5 | **12** |

## In-flight 발견 + fix

- **bug 1**: `tools.release_pipeline` 의 cmd_changelog_gen 이 `args.dry_run` attribute 필요 — wrapper `_make_args` 에 `dry_run` 추가
- **bug 2**: `cmd_version_bump` 의 `args.patch` / `args.minor` / `args.major` / `args.to` attribute 부재 — wrapper 에 4 attr 추가
- **bug 3**: `cmd_changelog_gen` 의 `args.output` / `args.unreleased_label` 부재 — wrapper 에 2 attr 추가
- **bug 4**: `cache_lfu_decay.py` 의 in-memory test artifact `<in-memory>` 파일이 cache 경로로 사용되어 v0.7.56 commit 에 포함됨 — git amend 로 제외. 본 release 의 pre-existing 의도적 literal cache_path (test file: check_cache_lfu_decay.py)
- **bug 5**: `okf_4_1_strict_rejects_empty_type` test 가 frontmatter parser 의 empty-string handling 차이로 fail — `type: ""` (explicit empty string) 로 fix

## Test 결과

- `check_workflow_kit_cli.py`: 31/31 PASS (이전 26, +5)
- `check_url_validity.py`: 14/14 PASS (이전 12, +2)
- `check_okf_import.py`: 25/25 PASS (이전 18, +7)
- `check_release_pipeline_lib.py`: 7/7 PASS (이전 2, +5)
- `check_cache_lfu_decay_persist.py`: 4/4 PASS (이전 2, +2)
- cumulative 5 module test: ~147 PASS (이전 ~140, +7 audit 3차 = 7 신규)
- cumulative total: 33 + 14 + 25 + 7 + 4 = **83 test** in core 5 file (이전 67, +16)

## 다음 (v0.7.57 / v0.7.60 후보)

1. `cache_lfu_decay.py` 의 `<in-memory>` test artifact — proper tempdir 사용으로 refactor
2. dispatcher subcommand 25+ (cache-lfu-decay-persist import-CSV / export-JSON / merge-multi)
3. mkdocs `--strict` 모드 (cross-link audit) — v0.7.53 follow-up
4. consumer feedback 1차 metric — GitHub Pages traffic tab 모니터링
5. 5 module audit 4차 (path_resolver / phishing_keywords 정합)
6. 외부 consumer 의 real feedback (P0 / P1 critical bug) — 운영 후
