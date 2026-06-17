# Beta v0.8.9 — dispatcher 29/30 (cache-lru-decay + cache-merge-csv) (2026-06-17)

> v0.7.58 release note 의 3 subcommand follow-up 잔여분 2개 ship. `cache-lru-decay`
> (subcommand 29, LRU-stale entry eviction) + `cache-merge-csv` (subcommand 30,
> multi-CSV merge). in-process wrapper 패턴 그대로 (v0.7.59+ 정공법).
> dispatcher 28 → **30** (2 신규). 5 module test 122 PASS, dispatcher 47 → **53 PASS**
> (+6 신규), version auto-sync 4, bitbucket_v2 2. **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 6 신규 test, 2 신규 subcommand)

### 1. `cache-lru-decay` (subcommand 29) — LRU-stale entry eviction

LRU cache 의 size cap enforcement. 기존 `cache_size_compare.py:evict_lru_over_size`
의 in-process wrapper. `--max-bytes=INT` 로 cap 지정, timestamp 기준 oldest first
eviction.

```
$ python -m workflow_kit.workflow_kit_cli --command=cache-lru-decay \
    --max-bytes=10000 --cache-path=~/.workflow_kit/url_validity_cache.json --json
{
  "evicted": 42,
  "max_bytes": 10000,
  "cache_path": "/Users/.../url_validity_cache.json"
}
```

Flags:
- `--max-bytes=INT` (required): target max cache file size
- `--cache-path=PATH`: base cache path (default: `~/.workflow_kit/url_validity_cache.json`)
- `--json`: JSON output

### 2. `cache-merge-csv` (subcommand 30) — multi-CSV merge

여러 CSV 파일을 single cache 로 merge. `--csv=PATH` repeatable. 각 CSV 가
`import_csv_to_cache(merge=True)` 로 같은 cache 에 append. 중복 URL 은 cache_migration
의 merge logic 으로 dedup.

```
$ python -m workflow_kit.workflow_kit_cli --command=cache-merge-csv \
    --csv=first.csv --csv=second.csv --cache-path=merged.json
Merged 2 CSV files: 4 imported, 0 skipped
  first.csv: +2 imported, 0 skipped (of 2 rows)
  second.csv: +2 imported, 0 skipped (of 2 rows)
```

Flags:
- `--csv=PATH` (repeatable, at least 1 required): input CSV file
- `--cache-path=PATH`: target cache file (default: `DEFAULT_CACHE_FILE`)
- `--json`: JSON output with per-CSV breakdown

## 운영 누적 (v0.7.5 → v0.8.9)

| | v0.7.5 | v0.8.0 | v0.8.7 | v0.8.8 | **v0.8.9** |
|---|---|---|---|---|---|
| **dispatcher** | 0 | 28 | 28 | 28 | **30** |
| **dispatcher test** | 0 | 47 | 47 | 47 | **53** |
| **5 module test** | 0 | 122 | 122 | 122 | **122** |
| **cumulative mypy strict clean** | 0 | 1 | 13 | 17 | **17** |

## In-flight 발견 + fix

- (없음) — 단순 dispatcher 등록 + in-process wrapper

## Test 결과

신규 test (6 PASS, v0.8.9+):
- `test_cache_lru_decay_registered_v0_8_9` — `cache-lru-decay` 등록 확인
- `test_cache_lru_decay_missing_args_v0_8_9` — `--max-bytes` 누락 시 rc=2
- `test_cache_lru_decay_dry_run_v0_8_9` — missing cache file → rc=0 (evicted=0)
- `test_cache_merge_csv_registered_v0_8_9` — `cache-merge-csv` 등록 확인
- `test_cache_merge_csv_no_csv_returns_2_v0_8_9` — `--csv` 누락 시 rc=2
- `test_cache_merge_csv_roundtrip_v0_8_9` — 2 CSV merge → cache 에 3 unique URL (a, b, c)

회귀 (5 module + dispatcher): 변동 없음
- `check_url_validity.py`: 14/14 PASS
- `check_path_resolver.py`: 12/12 PASS
- `check_okf_import.py`: 25/25 PASS
- `check_release_pipeline_lib.py`: 7/7 PASS
- `check_cache_migration.py`: 5/5 PASS
- `check_workflow_kit_cli.py`: 47 → **53 PASS** (+6 신규)
- `check_release_pipeline_version_auto_sync.py`: 4/4 PASS
- `check_bitbucket_v2.py`: 2/2 PASS

**cumulative dispatcher test**: 47 → **53 PASS** (6/6 신규, 12.7% 증가)
**cumulative dispatcher subcommand**: 28 → **30** (cache-lru-decay + cache-merge-csv)

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/workflow_kit_cli.py` | +98 (2 신규 cmd_cache_lru_decay + cmd_cache_merge_csv) |
| M | `tests/check_workflow_kit_cli.py` | +73 (6 신규 test) |
| A | `workflow-source/releases/Beta-v0.8.9.md` | release note |
| A | `ai-workflow/memory/release/v0.8.9/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.10+ / v0.9.0)

1. **v0.8.10**: `workflow_kit/common/state/builder.py` 35 error
2. **v0.8.11**: `workflow_kit/common/contracts/baselines.py` 27 error
3. **v0.9.0** full mypy strict
