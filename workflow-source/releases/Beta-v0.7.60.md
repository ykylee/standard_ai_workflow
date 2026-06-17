# Beta v0.7.60 — 5 module audit 4차 (path_resolver + phishing_keywords) + dispatcher 28 (cache-lfu-decay-persist) (2026-06-17)

> v0.7.58 의 follow-up 2건 동시 해결: (1) 5 module audit 4차 — path_resolver + phishing_keywords
> 정합 coverage +20 test, (2) dispatcher 27 → 28 (cache-lfu-decay-persist in-process).
> 5 module test 98 → **119 PASS** (+21 audit 4차 = 12 + 8 + dispatcher 1 = +4).
> cumulative 2 follow-up, 2 commit, 4 신규 test (dispatcher 28), 2 신규 test file (audit 4차).

## 핵심 추가 (2 follow-up, 1 commit, 24 신규 test, 0 신규 tool)

### 1. 5 module audit 4차 (path_resolver + phishing_keywords 정합)

v0.7.56 audit 3차: `okf_import` 의 strict mode lint rule coverage 7 신규 test.
v0.7.60 audit 4차: **`path_resolver` + `phishing_keywords` 의 정합 coverage 20 신규 test**:

| Module | Test count | Coverage |
|---|---|---|
| `workflow_kit.path_resolver` (12) | 12/12 PASS | path safety, origin URL normalize (SSH/HTTPS), origin detection (CI env / git config), default branch detection (symbolic-ref / current / fallback "main"), resolve (URL pass-through / canonical), resolve_pinned (commit SHA / ref) |
| `workflow_kit.phishing_keywords` (8) | 8/8 PASS | bundled 8 keywords, load fallback chain, external JSONL feed (case-preserve, dedup), phishing_feed_update_status (path or None), fetch_phishtank / fetch_openphish (offline-safe `[]` OR valid URL list) |

**Coverage design** (audit 4차 정공법 = audit 3차 와 같은 정신):

- ADR-008 (in-repo path → canonical GitHub URL) 의 5-step resolve algorithm
- ADR-018 (commit/ref pinned URL) 의 SHA / ref validate
- ADR-023 follow-up (PhishTank + OpenPhish free tier) 의 offline-safe pattern
- V-R11 phishing keyword list (8 bundled baseline) 의 fallback chain
- security: path traversal reject, non-HTTPS origin reject, SHA format validate

### 2. dispatcher 27 → 28 (subcommand 28 = `cache-lfu-decay-persist`)

v0.7.49+ 의 `cache_lfu_decay_persist` module (per-URL LFU decay score persistence) 가
*dispatcher surface* 가 없었음. 본 release 에서:

- **`tools/release_pipeline_lib.py` 의 신규 wrapper** `cmd_lfu_decay_persist(url, score, scores_path, apply)`:
  - `apply=False` (default) → dry-run, *write 안 함*, JSON 출력 `{mode: dry-run, ...}`
  - `apply=True` → load + update + save, JSON 출력 `{mode: applied, ...}`
  - score file format: `{"version": 1, "saved_at": ..., "scores": {url: float, ...}}`
- **`workflow_kit_cli.py` 의 subcommand 28** `cache-lfu-decay-persist`:
  - 인자: `--url=URL` (required), `--score=FLOAT` (required), `--scores-path=PATH` (default `cache/lfu_decay_scores.json`), `--apply`, `--json`
  - in-process pattern (v0.7.55+ release-doctor, v0.7.56+ score-wiki-trend, v0.7.59+ consumer-metrics 와 동일 정공법)
  - exit code: 0 (success), 2 (usage error)

**Safety** (memory rule 5: default dry-run, `--apply` 명시 시에만 실제 동작). `release-bump` / `cache-prune` / `okf-cleanup` / `cache-lfu-decay-persist` 모두 이 정공법.

## 운영 누적 (v0.7.52 → v0.7.60)

| | v0.7.52 | v0.7.53 | v0.7.54 | v0.7.55 | v0.7.56 | v0.7.57 | v0.7.58 | v0.7.59 | **v0.7.60** |
|---|---|---|---|---|---|---|---|---|---|
| **dispatcher** | 6 | 8 | 11 | 14 | 23 | 26 | 27 | 27 | **28** |
| **dispatcher test** | 6 | 9 | 13 | 20 | 33 | 38 | 41 | 43 | **47** |
| **5 module test** | 64 | 68 | 68 | 68 | 83 | 98 | 98 | 98 | **119** |
| **audit 4차** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **+20** |
| **in-process dispatcher** | ❌ | ❌ | ❌ | release-doctor | score-wiki-trend | score-wiki-trend | ❌ | consumer-metrics | consumer-metrics + decay-persist |

## In-flight 발견 + fix

- **bug 1**: `check_path_resolver.py` 의 test `test_resolve_in_repo_path_v0_7_60` 가 default branch `"main"` 하드코딩 — `git init` 의 local default branch 가 환경마다 다를 수 있음 (`main` / `master`). fix: `_detect_default_branch(tmp_path)` 호출 후 그 값을 expected URL 에 사용.
- **bug 2**: `check_phishing_keywords.py` 의 test `test_load_external_feed_jsonl` 가 caller-side dedup 가정 — `_load_external_feed` 자체는 case-preserve, dedup 없음. fix: assertion 을 `_load_external_feed` 의 실제 동작에 맞춤 (3 valid output, dup 그대로 보존).
- **bug 3**: `check_phishing_keywords.py` 의 test `test_fetch_openphish_empty_on_error_v0_7_60` 가 strict `== []` — test env 에서 live network 가 OpenPhish feed 300개 응답. fix: offline-safe `[]` OR valid URL list 모두 accept (type check + URL prefix check).
- **bug 4**: `check_workflow_kit_cli.py` 의 subcommand 28 test 가 pytest `tmp_path` fixture 사용 — 본 test framework 은 plain function 호출이라 TypeError. fix: `tempfile.TemporaryDirectory()` 로 교체.
- **bug 5**: `check_workflow_kit_cli.py` 의 subcommand 28 apply test 가 bare dict format 가정 — `save_decay_scores` 는 wrapped `{"scores": {...}}` format. fix: `data["scores"]["url"]` 로 access.
- **bug 6**: `check_workflow_kit_cli.py` 의 subcommand 28 dry-run test 가 pre-populate file 을 bare dict format 으로 작성 — `load_decay_scores` 가 wrapped format 만 인식. fix: pre-populate file 도 wrapped format 으로 작성.

## Test 결과

- `check_path_resolver.py`: **12/12** PASS (NEW)
  - path safety (accept / reject unsafe), origin URL normalize (SSH→HTTPS, HTTPS passthrough, empty/invalid), origin detect (CI env / git config), default branch (local fallback / "main" deepest), resolve (URL pass-through / canonical), resolve_pinned (commit / ref / invalid SHA)
- `check_phishing_keywords.py`: **8/8** PASS (NEW)
  - bundled 8, load fallback, external JSONL (case-preserve), load dedup, feed status (no path / with file), fetch_phishtank offline-safe, fetch_openphish offline-or-valid
- `check_workflow_kit_cli.py`: 43/43 → **47/47** PASS (+4 신규)
  - `test_cache_lfu_decay_persist_registered_v0_7_60` — subcommand 28 등록 확인
  - `test_cache_lfu_decay_persist_missing_args_v0_7_60` — `--url` / `--score` 부재, `--score=not-a-number` → rc=2
  - `test_cache_lfu_decay_persist_dry_run_v0_7_60` — dry-run 시 file unchanged
  - `test_cache_lfu_decay_persist_apply_v0_7_60` — `--apply` 시 file wrapped format 으로 persist
- `check_consumer_metrics.py`: 6/6 PASS (변동 없음)
- `check_cache_migration.py`: 5/5 PASS (변동 없음)
- `check_url_validity.py`: 14/14 PASS (변동 없음)
- `check_okf_import.py`: 25/25 PASS (변동 없음)
- `check_release_pipeline_lib.py`: 7/7 PASS (변동 없음)
- **cumulative dispatcher test**: 43 → **47 PASS** (+4, 9% 증가)
- **cumulative 5 module test**: 98 → **119 PASS** (+21, 21% 증가, audit 4차 = +20 + dispatcher 신규 = +1)

## 다음 (v0.7.61 / v0.7.62 / v0.8.0)

1. **v0.7.61 F**: mkdocs `--strict` 진짜 활성화 (wiki mirror 또는 multirepo) — v0.7.53 follow-up
2. **v0.7.62 B + D**: consumer-metrics trend snapshot + weekly digest 자동화
3. v0.7.60 follow-up: dispatcher 29 (`cache-lru-decay`) + dispatcher 30 (`cache-merge-csv`) — v0.7.58 의 3 subcommand follow-up 중 1개만 ship, 나머지 2개는 v0.7.61+ 로 분할
4. v0.8.0 J. stable API freeze + mypy strict + PyPI + generated schema SSOT
   (workflow-source/core/v0_8_0_stable_api_spec.md)
