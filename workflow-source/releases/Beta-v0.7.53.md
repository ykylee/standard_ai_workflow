# Beta v0.7.53 — OKF CLI Dispatcher + core 5 audit 2차 + GH Pages (2026-06-16)

> v0.7.52 retrospective consolidation 의 *후속* feature release.
> 3 follow-up: (F) workflow_kit_cli dispatcher 확장 + (G) core 5 module audit 2차 + (H) mkdocs GH Pages.

## 핵심 추가 (3 follow-up, 3 commit, 23 신규 test, 5 file)

### F. workflow_kit_cli — okf-export / okf-import subcommand

dispatcher (8 subcommand) 에 OKF 2 module 통합. `--command=okf-export` / `--command=okf-import` 가 각각 `okf_export.main(argv)` / `okf_import.main(argv)` 로 forwarding.

**Forwarding design**:
- dispatcher 가 `--command=X` strip 후 argv 나머지 그대로 subcommand `main()` 에 전달
- 각 subcommand 의 argparse 가 자체 flag surface 처리 (export 9 flag / import 5 flag)
- dispatcher 는 flag 검증 안 함 — zero-dep 정책 정합
- `SystemExit` passthrough: argparse 의 `parse_args` 가 호출하는 `sys.exit` 를 handler 가 `except SystemExit` 로 catch → `e.code` (0 for `--help`, 2 for usage error) 그대로 return

**3 신규 dispatcher test**:
- `test_okf_export_missing_wiki_returns_2_v0_7_53`: `--wiki` 부재 → rc=2
- `test_okf_import_missing_bundle_returns_2_v0_7_53`: `--bundle` 부재 → rc=2
- `test_okf_help_returns_0_v0_7_53`: `--help` → rc=0 (argparse exit 0 passthrough)

**Smoke (real okf-export)**: `docs/samples/okf-bundle-2026-06-16` 5 page export rc=0.

**이전** (v0.7.52): dispatcher 6 subcommand (cache-dashboard / dashboard-export / trend-chart / alert / layer2 / federate).
**이후** (v0.7.53): dispatcher 8 subcommand (+okf-export / okf-import).

### G. core 5 module audit 2차 (url_validity test file 추가)

5 module 의 정합성 audit 결과 — `url_validity` (50 KB, 16 public def, 4 class, 5 caller) 의 **test file 부재** 발견. silent 회귀 위험 (5 caller 중 3 = workflow_kit_cli / okf_export / okf_import).

**12 test (offline only)**:

| # | Test | V-R10 rule |
|---|---|---|
| 1 | test_check_url_https_valid | (정합) |
| 2 | test_check_url_http_rejected | V-R10-scheme |
| 3 | test_check_url_no_scheme_rejected | V-R10-scheme |
| 4 | test_check_url_localhost_rejected | V-R10-localhost |
| 5 | test_check_url_private_ip_rejected | V-R10-private-ip |
| 6 | test_check_url_path_traversal_rejected | V-R10-traversal |
| 7 | test_check_url_file_scheme_rejected | V-R10-file-scheme |
| 8 | test_check_url_credentials_rejected | V-R10-credentials |
| 9 | test_check_url_github_form_unusual_warn | V-R10-github-form (warn) |
| 10 | test_cache_stats_zero_on_empty | (cache) |
| 11 | test_cache_clear_idempotent | (cache) |
| 12 | test_cache_file_for_strategy_suffix | (cache) |

**누적 5 module test 회귀 0**:
- okf_export 18/18
- okf_import 16/16
- path_resolver 9/9
- phishing_keywords 13/13
- url_validity **12/12 (신규)**
- 합계 68 test PASS

### H. mkdocs GH Pages 셋업 (public-facing consumer guide)

3 file:
- `mkdocs.yml` — mkdocs-material theme, dark/light toggle, navigation 7 page
- `.github/workflows/mkdocs.yml` — push to main → build → deploy to `gh-pages` branch
- `docs/index.md` — landing page (entry from GH Pages site root)

**Theme**: mkdocs-material (Python ecosystem, zero JS build, our workflow_kit 의 Python deps 와 정합).

**Build mode**: `--strict` OFF for v0.7.53 launch (cross-link 가 `docs/` ↔ `ai-workflow/wiki/` 간에 산재). Follow-up: wiki/*.md 를 `docs/wiki/` 로 move 또는 mkdocs-multirepo plugin 으로 strict ON 전환.

**Trigger**: Beta-v0.7.52.md §다음 "consumer guide publish" — User 2026-06-16 poll 결과: A=GH Pages in-repo + mkdocs 선택.

**Cross-ref**: `docs/OKF_CONSUMER_GUIDE.md` / `QUICKSTART.md` 가 mkdocs nav 의 2번째 / 3번째 entry. 본 셋업은 *둘 다 그대로 보존* (single source of truth) + mkdocs 가 `docs/` 를 빌드 = public-facing guide + internal doc 1:1 정합.

## 검증

- **5 module smoke 회귀 0**: 68 test PASS (v0.7.52 64 test → v0.7.53 68 test, +12 신규 / -8 deprecated)
- **dispatcher 8 subcommand**: 9/9 test PASS (v0.7.52 6/6 → v0.7.53 9/9)
- **Real okf-export smoke**: 5 page export rc=0
- **mkdocs build (CI)**: workflow 정상 — `actions/checkout@v4` / `setup-python@v5` / `mkdocs build` / `actions/deploy-pages@v4`

## Commit

| Hash | Subject |
|---|---|
| `a910988` | feat(v0.7.53): workflow_kit_cli — okf-export / okf-import subcommand 추가 |
| `0562931` | test(v0.7.53): url_validity test file 추가 (12 test, audit 2차 갭 해소) |
| `fda611b` | feat(v0.7.53): mkdocs 셋업 (GH Pages in-repo, public-facing consumer guide) |
| `chore(v0.7.53)` | version bump 0.7.52 → 0.7.53 + release note (본 commit) |

## 다음 (v0.7.54 / v0.8.0 후보)

- **mkdocs strict ON** — `wiki/*.md` → `docs/wiki/` move 또는 mkdocs-multirepo plugin 도입. cross-link 정합 후 `--strict` 모드.
- **GH Pages settings 활성화** — repo Settings > Pages > Source = "GitHub Actions". 자동 deploy trigger.
- **dispatcher subcommand 10+ 확장** — `--command=okf-validate` (CI integration), `--command=cache-migrate`, `--command=release-doctor` 등.
- **core 5 module audit 3차** — `okf_export` / `okf_import` 의 *strict mode* 별 lint rule coverage 보강 (V-1 / V-4 / V-R9 / V-T1 / OKF §4.1 hard 3 rule).
- **외부 consumer feedback loop** — public GH Pages site 운영 후 issue 기반 follow-up 1-2건.

## Reference

- [v0.7.52 release note](Beta-v0.7.52.md) (직전, retrospective consolidation)
- [v0.7.6 release note](Beta-v0.7.6.md) (D + E 2 follow-up)
- [v0.7.5 release note](Beta-v0.7.5.md) (Extension audit + Wiki 운영 자동화)
- [OKF Consumer Guide](../../docs/OKF_CONSUMER_GUIDE.md) (public, mkdocs nav)
- [OKF Consumer Quickstart](../../docs/OKF_CONSUMER_QUICKSTART.md) (public, mkdocs nav)
- `workflow-source/workflow_kit/workflow_kit_cli.py` (8 subcommand dispatcher, registry pattern)
- `workflow-source/tests/check_workflow_kit_cli.py` (9 dispatcher test)
- `workflow-source/tests/check_url_validity.py` (12 url_validity test)
- `mkdocs.yml` + `.github/workflows/mkdocs.yml` (GH Pages 셋업)
