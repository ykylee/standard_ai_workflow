# Beta v0.7.62 — consumer-metrics trend snapshot + weekly digest (B + D 통합) (2026-06-17)

> v0.7.58 의 follow-up B + D 동시 해결. v0.7.58 의 *수집* 만 가능했던 consumer_metrics 를
> *추세* (history jsonl + ASCII chart) + *digest* (Slack / GH markdown) 까지 확장.
> v0.7.59 의 in-process dispatcher 정공법 그대로 적용 — 별도 subcommand 추가 없이
> `consumer-metrics --record` / `--show-trend` / `--digest` / `--digest-markdown` 으로 노출.
> 5 module test 119 → **122 PASS** (+3 신규), dispatcher 47 → **47 PASS** (변동 없음).

## 핵심 추가 (1 TASK, 1 commit, 5 신규 test, 0 신규 subcommand, 0 신규 tool)

### 1. consumer_metrics — trend snapshot (B)

v0.7.58 의 consumer_metrics 는 *현재 snapshot* 만 출력. v0.7.62 의 trend 기능:

- **`--record`**: 현재 snapshot 을 `tools/.consumer_metrics_history.jsonl` 에 append
  (per-line 1 snapshot, v0.7.1+ score_wiki_trend.jsonl pattern 정합)
- **`--show-trend[=dim]`**: history 로부터 ASCII bar chart
  (x=YYYY-MM-DD, y=value, auto-scaled 0~max, 30-char bar)
- **`--history-path=PATH`**: history file path override (default: `tools/.consumer_metrics_history.jsonl`)
- **`TREND_DIMS`**: 5 dim — `views_total` / `views_uniques` / `clones_total` / `feedback_total` / `feedback_open`
- **offline-safe**: `--show-trend` 는 gh API 호출 없음, history file 만 읽음 → CI / cron 가능

History schema (per line):
```json
{
  "snapshot_at": "2026-06-17T00:00:00+00:00",
  "repo": "owner/repo",
  "days": 7,
  "views_total": 100,
  "views_uniques": 50,
  "clones_total": 20,
  "feedback_total": 5,
  "feedback_open": 2,
  "releases_recent_count": 1
}
```

### 2. consumer_metrics — weekly digest (D)

- **`--digest`**: Slack-style text summary (`*bold*` mrkdwn)
  ```
  *Consumer digest (7d, owner/repo)*
  • views_total: 100  (50 unique)
  • clones_total: 20
  • feedback: 5 (2 open, 3 closed)
  • releases: 1
  ```
- **`--digest-markdown`**: GH issue comment markdown (heading + table + sub-sections)
  ```markdown
  ## Consumer digest — 7d window (owner/repo)
  _snapshot_at: 2026-06-17T00:00:00+00:00_

  | Metric | Value |
  | --- | --- |
  | GH Pages views (total) | 100 |
  | Consumer feedback (open) | 2 |
  ...

  ### Recent releases
  - **v0.7.62** — trend + digest  (2026-06-17)

  ### Open feedback issues
  - #1 Bug X  _(created 2026-06-15)_
  ```
- **Cron / GitHub Actions weekly schedule**: 본 release 의 scope 외 (follow-up).
  digest 자체는 완결 — `python3 tools/consumer_metrics.py --digest-markdown --days=7`
  → stdout capture → GH issue comment post.

## 운영 누적 (v0.7.58 → v0.7.62)

| | v0.7.58 | v0.7.59 | v0.7.60 | v0.7.61 | **v0.7.62** |
|---|---|---|---|---|---|
| **dispatcher** | 27 | 27 | 28 | 28 | **28** |
| **dispatcher test** | 41 | 43 | 47 | 47 | **47** |
| **5 module test** | 98 | 98 | 119 | 119 | **122** |
| **consumer_metrics test** | 6 | 6 | 6 | 6 | **9** |
| **consumer-metrics flags** | 3 (--repo/--days/--json) | (in-process) | (in-process) | (in-process) | **+4 (--record/--show-trend/--history-path/--digest+--digest-markdown)** |
| **trend 기능** | ❌ | ❌ | ❌ | ❌ | **✓ (B)** |
| **weekly digest** | ❌ | ❌ | ❌ | ❌ | **✓ (D)** |

## In-flight 발견 + fix

- **bug 1**: `tests/check_consumer_metrics.py` 의 v0.7.62 3 test 가 pytest `tmp_path` fixture 사용 — 본 test framework 은 plain function 호출이라 TypeError. fix: 시그니처에서 `tmp_path` 제거, 본문에서 `tempfile.TemporaryDirectory()` 직접 사용.

## Test 결과

- `tests/check_consumer_metrics.py`: 6/6 → **9/9** PASS (+3 신규)
  - `test_consumer_metrics_record_snapshot_v0_7_62` — record → load roundtrip
  - `test_consumer_metrics_load_history_empty_v0_7_62` — missing file → `[]` (offline-safe)
  - `test_consumer_metrics_ascii_trend_v0_7_62` — TREND_DIMS 5종 chart render, unknown dim / empty records
  - `test_consumer_metrics_format_digest_v0_7_62` — Slack-style text contain
  - `test_consumer_metrics_format_digest_markdown_v0_7_62` — GH issue markdown heading + table + sub-sections
- 회귀 (5 module + dispatcher): 변동 없음
  - `check_path_resolver.py`: 12/12 PASS
  - `check_phishing_keywords.py`: 8/8 PASS
  - `check_url_validity.py`: 14/14 PASS
  - `check_okf_import.py`: 25/25 PASS
  - `check_release_pipeline_lib.py`: 7/7 PASS
  - `check_cache_migration.py`: 5/5 PASS
  - `check_workflow_kit_cli.py`: 47/47 PASS
- **cumulative 5 module test**: 119 → **122 PASS** (+3, 3% 증가)
- **cumulative dispatcher test**: 47 → **47 PASS** (변동 없음)
- **dispatcher argv forwarding**: `python -m workflow_kit.workflow_kit_cli --command=consumer-metrics --show-trend --history-path=...` rc=0 (offline-friendly message)

## 다음 (v0.8.0)

1. **v0.8.0 J** — stable API freeze + mypy strict + PyPI + generated schema SSOT
   (workflow-source/core/v0_8_0_stable_api_spec.md, draft v0.7.59+ 에서 작성)
2. v0.7.62 follow-up: GitHub Actions weekly cron — `consumer-metrics --digest-markdown` → GH issue comment 자동화
3. v0.7.62 follow-up: dispatcher 29 (`cache-lru-decay`) + dispatcher 30 (`cache-merge-csv`) — v0.7.58 의 3 subcommand 잔여분
4. v0.7.62 follow-up: history file (`.consumer_metrics_history.jsonl`) gitignore 등록
