# Beta v0.7.54 — dispatcher 11 subcommand (I/J/K) (2026-06-16)

> v0.7.53 의 "dispatcher subcommand 10+ 확장" follow-up.
> 3 신규 subcommand 추가: I (okf-validate) + J (cache-migrate) + K (release-doctor).
> dispatcher 8 → 11.

## 핵심 추가 (3 follow-up, 2 commit, 4 신규 test, 11 subcommand)

### I. --command=okf-validate (OKF v0.1 bundle lint 전용)

기존 `okf-import` 의 *import / staging / promote* 없이 *lint only* — read-only validation. 외부 consumer 가 우리 wiki 에 import 하기 *전* bundle 의 정합성을 확인.

```bash
# human-readable
python -m workflow_kit.workflow_kit_cli --command=okf-validate \
  --bundle=/path/to/okf-bundle --mode=strict

# JSON output
python -m workflow_kit.workflow_kit_cli --command=okf-validate \
  --bundle=/path/to/okf-bundle --mode=loose --json
```

**구현**: `okf_import.lint_page()` 의 8 rule (V-1 / V-4 / V-R9 / V-T1 / OKF §4.1 hard 3 + broken link + unknown key) 호출. `Mode` = `Literal["strict", "loose"]` 라 string 그대로 forwarding.

**Bug fix (in-flight)**: 첫 commit 에서 JSON mode 의 `UnboundLocalError` (err_count 가 else branch 에만 정의). JSON branch 에도 err_count 계산 추가.

### J. --command=cache-migrate (v0.7.41 single-strategy cache → 3 per-strategy files)

ADR-024 follow-up — v0.7.41 이전의 *single* cache file (`<base>.json`) 을 v0.7.41+ 의 *per-strategy* 3 file (`<base>_lru.json` / `<base>_lfu.json` / `<base>_mixed.json`) 로 1-shot migration. idempotent (re-run safe).

```bash
python -m workflow_kit.workflow_kit_cli --command=cache-migrate \
  --cache-path=/path/to/cache.json
# → "Cache migrated: N entries" or "No migration needed: ..."
```

**구현**: `cache_migration.migrate_to_per_strategy_cache()` 단일 호출. result field `reason` 부재 → per-strategy file 존재 / source 부재 / source empty 의 3 case 를 *infer* (filename existence check).

### K. --command=release-doctor (release pre-flight, 4 source check)

`tools/release_pipeline.py validate` 의 *subprocess* wrapper. 4 source 의 release-readiness 동시 검증:

1. **check_packaging** — pyproject `[tool.setuptools.packages]` ↔ 디스크 정합
2. **workflow_kit.cli.doctor** — 7 baseline evaluate
3. **state.json freshness** — wiki memory state
4. **git status** — working tree clean

```bash
# all 4 (default)
python -m workflow_kit.workflow_kit_cli --command=release-doctor

# specific skip
python -m workflow_kit.workflow_kit_cli --command=release-doctor \
  --skip-packaging --skip-git
```

**구현**: `git rev-parse --show-toplevel` 로 repo root 자동 감지 → `tools/release_pipeline.py` 의 *절대 path* + `sys.executable` 로 *subprocess* 호출 (in-process import 아님, 그 *module* 이 package 가 아니라 script). `--json` flag 는 항상 (release-readiness 가 machine-readable).

**Cross-ref**: `docs/RELEASE.md` 의 release pipeline, memory rule 10 (2-source version sync 의 release cut 직전 anchor).

## 검증

- **dispatcher 11 subcommand**: 13/13 test PASS (v0.7.52 6 → v0.7.53 9 → **v0.7.54 13**)
- **Smoke (4)**:
  - `okf-validate` loose  rc=0 (no error)
  - `okf-validate` strict rc=1 (broken link / V-R9 errors)
  - `cache-migrate` noop rc=0 (idempotent)
  - `release-doctor` all-skip rc=0 (4 sources skipped = ok)
- **Bug fix during dev**: 1 (UnboundLocalError in JSON mode) — 같은 commit 에서 해결 (의도적 — bug 발견 즉시 fix 가 cycle 압축)

## Commit

| Hash | Subject |
|---|---|
| `97adc0c` | feat(v0.7.54): workflow_kit_cli — okf-validate / cache-migrate / release-doctor (11 subcommand) |
| `cde0a45` | test(v0.7.54): dispatcher test 4 신규 (okf-validate × 2 + cache-migrate + release-doctor) |
| `chore(v0.7.54)` | version bump 0.7.53 → 0.7.54 + release note (본 commit) |

## 다음 (v0.7.55 / v0.7.60 후보)

- **release-doctor → in-process 호출** — 현재 subprocess. tools/release_pipeline 의 모듈화 후 import 시 더 빠르고 stderr 정합.
- **okf-validate → CI integration** — `.github/workflows/okf-validate.yml` (이미 v0.7.38+ 존재) 의 `--command=okf-validate` dispatcher wrapper. v0.7.55 follow-up.
- **cache-migrate → v0.7.45+ LRU/LFU split** — 현재는 *mixed* 만. `split_to_per_strategy` (v0.7.45+) 까지 노출.
- **dispatcher subcommand 14+** — `--command=okf-version-check` / `--command=cache-decay` / `--command=score-wiki-trend` 등 운영 layer 통합.

## Reference

- [v0.7.53 release note](Beta-v0.7.53.md) (직전, OKF CLI Dispatcher + audit 2차 + GH Pages)
- [v0.7.52 release note](Beta-v0.7.52.md) (Retrospective consolidation 통합본)
- [OKF Consumer Guide](../../docs/OKF_CONSUMER_GUIDE.md) (okf-validate 의 consumer 정합)
- `workflow-source/workflow_kit/workflow_kit_cli.py` (11 subcommand dispatcher, registry pattern)
- `workflow-source/workflow_kit/cache_migration.py` (cache-migrate 의 1차 layer)
- `workflow-source/workflow_kit/okf_import.py` (okf-validate 의 1차 layer, `_parse_bundle_pages` + `lint_page`)
- `workflow-source/tools/release_pipeline.py` (release-doctor 의 1차 layer, `cmd_validate`)
- `workflow-source/tests/check_workflow_kit_cli.py` (13 dispatcher test)
