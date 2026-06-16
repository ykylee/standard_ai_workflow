# Beta v0.7.58 — consumer feedback metrics (dispatcher 27) + consumer_metrics tool (2026-06-17)

> v0.7.56 의 GH Pages feedback loop (FEEDBACK.md, 4 channel) 의 *1차 metric tool* 정식화.
> `tools/consumer_metrics.py` (155 line, gh CLI 의존) + dispatcher subcommand 27 (`consumer-metrics`).
> 5 module test 98 → **107 PASS** (+9 신규). 2 commit, 1 신규 file.

## 핵심 추가 (1 follow-up, 2 commit, 9 신규 test, 1 신규 tool)

### 1. consumer feedback metrics tool (tools/consumer_metrics.py)

v0.7.56 의 FEEDBACK.md (4 channel: 🐛 bug / 💡 feature / 💬 Q&A / 📖 docs) + v0.7.53 의
GH Pages traffic tab = **consumer engagement 의 정량 metric**. 본 release 의
*1차 signal source* 통합:

- **GH Pages traffic** (gh API `repos/<repo>/traffic/views` + `traffic/clones`):
  views_total / views_uniques / views_daily / clones_total / clones_daily
  → *lookback window* (1-90 day) 기준 filter
- **Consumer feedback issues** (gh issue list `--label=consumer-feedback`):
  total / open / closed / issues[] (number, title, state, createdAt)
- **Recent releases** (gh API `repos/<repo>/releases?per_page=20`):
  tag / name / published_at → lookback 기준 filter

**Helper 3 신규** (tools/consumer_metrics.py):
- `_gh_api(endpoint, repo) -> dict | list`: gh API 호출 + JSON return, error 시 빈 dict + stderr warn
- `_gh_issue_list(label, repo, state='all') -> list[dict]`: gh issue list + JSON parse
- `collect_metrics(repo, days) -> dict`: 3 source 통합 + lookback filter

**Main argparse**:
- `--repo=OWNER/REPO` (default: `ykylee/standard_ai_workflow`)
- `--days=N` (1-90, default 14) — range 밖이면 rc=2
- `--json` (CI integration, default: human-readable)

**Exit code**:
- 0 = success (data collected)
- 1 = gh CLI not authenticated (`gh auth login` 필요)
- 2 = usage error (--days range 위반)

### 2. dispatcher 26 → 27 (subcommand 27 = `consumer-metrics`)

`@register("consumer-metrics")` (workflow_kit/workflow_kit_cli.py:1037):
- subprocess delegation pattern: `subprocess.run([sys.executable, "tools/consumer_metrics.py", ...])`
- `--repo` / `--days` / `--json` argparse forwarding
- `--days` range validation 1+2 (dispatcher 자체 validation + main() 의 validation = *defense in depth*)
- 60s timeout (gh API response)

**In-flight bug 발견 + fix**:
- v0.7.58 의 initial commit 에서 `tools/consumer_metrics.py` 가 *worktree root* (`tools/`) 에
  생성됨 — dispatcher 가 `workflow-source/tools/` 에서 찾으므로 rc=2 (file not found)
- fix: `mv tools/consumer_metrics.py workflow-source/tools/consumer_metrics.py`
- *project convention*: 모든 tools script 는 `workflow-source/tools/` 아래 (v0.7.56+ 의
  in-process pattern 의 prerequisite)
- *follow-up candidate*: v0.7.59+ 에서 in-process 로 refactor (subprocess → import_module)

## 운영 누적 (v0.7.52 → v0.7.58)

| | v0.7.52 | v0.7.53 | v0.7.54 | v0.7.55 | v0.7.56 | v0.7.57 | **v0.7.58** |
|---|---|---|---|---|---|---|---|
| **dispatcher** | 6 | 8 | 11 | 14 | 23 | 26 | **27** |
| **dispatcher test** | 6 | 9 | 13 | 20 | 33 | 38 | **41** |
| **5 module test** | 64 | 68 | 68 | 68 | 83 | 98 | **98** |
| **consumer_metrics test** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **6** |
| **GH Pages** | ❌ | ✅ | ✅ | ✅ | ✅ (FEEDBACK) | ✅ | ✅ (metric) |
| **FEEDBACK → metric** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |

## In-flight 발견 + fix

- **bug 1**: `tools/consumer_metrics.py` 가 worktree root 에 생성됨 (`tools/`) →
  dispatcher path mismatch → `mv` 로 `workflow-source/tools/` 로 이동 (project convention 정합)
- **bug 2**: `cmd_consumer_metrics` 의 subprocess delegation 이 in-process pattern 과
  *불일치* (v0.7.56+ 의 score_wiki_trend 는 in-process) — v0.7.59+ follow-up 으로
  refactor 가능. 본 release 는 *subprocess 도 OK* 의 보수적 패턴 채택

## Test 결과

- `check_workflow_kit_cli.py`: 38/38 → **41/41** PASS (+3 신규)
  - `test_consumer_metrics_registered_v0_7_58` — `COMMANDS["consumer-metrics"]` 등록 확인
  - `test_consumer_metrics_invalid_days_returns_2_v0_7_58` — `--days=0`, `--days=100` rc=2
  - `test_consumer_metrics_default_argv_v0_7_58` — default argv 가 rc 0/1 (gh auth 의존)
- `check_consumer_metrics.py`: **6/6** PASS (NEW, gh auth 있을 때)
  - importable, days validation, default repo, collect_metrics structure, main with gh, JSON output
- `check_cache_lfu_decay.py`: 3/3 PASS (변동 없음)
- `check_cache_migration.py`: 5/5 PASS (변동 없음)
- `check_url_validity.py`: 14/14 PASS (변동 없음)
- `check_okf_import.py`: 25/25 PASS (변동 없음)
- `check_release_pipeline_lib.py`: 7/7 PASS (변동 없음)
- **cumulative dispatcher test**: 38 → **41 PASS** (+3, 8% 증가)
- **cumulative 5 module test**: 98 → **98 PASS** (변동 없음)
- **cumulative +1 tool test**: **6 신규**

## 다음 (v0.7.59 / v0.7.60+)

1. `cmd_consumer_metrics` in-process refactor (subprocess → import_module, v0.7.56+ 정공법)
2. consumer_metrics 의 *trend snapshot* (날짜별 snapshot → trend chart, score_wiki_trend 와 동일 정신)
3. consumer_metrics 의 *weekly digest* 자동화 (cron + slack/webhook)
4. 5 module audit 4차 (path_resolver / phishing_keywords 정합)
5. dispatcher 28+ (cache-{lru-decay,lfu-decay-persist,merge-csv} 추가)
6. v0.8.0 candidates 정리 (PyPI / stable API / mypy strict / schema)
