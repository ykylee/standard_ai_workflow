# Beta v0.8.11 — phishing_keywords 2 pre-existing test fail fix (5 module 122/122 완결) (2026-06-17)

> v0.7.60+ 부터 pre-existing 으로 fail 하던 2 test fix.
> 1) `test_load_external_feed_jsonl_v0_7_60` — 함수 의 case-insensitive normalize 미구현
> 2) `test_fetch_openphish_empty_on_error_v0_7_60` — test 가 offline env 가정, network 있는 CI 에서 fail
> 5 module test **120 → 122 PASS** (전부 0 fail). **PyPI 배포: no**.

## 핵심 추가 (1 TASK, 1 commit, 0 신규 test, 0 신규 subcommand)

### fix 1: `_load_external_feed` case-insensitive normalize (v0.8.11)

`workflow_kit/phishing_keywords.py:_load_external_feed` 가 raw keyword 를 그대로
return (case 보존, dedup 없음). `load_phishing_keywords` (custom + bundled 합치는
upper layer) 가 lowercase + dedup 하지만, `_load_external_feed` 직접 호출 경로
(test / external usage) 에서는 normalize 누락.

본 release 에서 `_load_external_feed` 자체에 lowercase + dedup 추가. test 의
expected pattern ("scama" + "scamb" lowercase, dup 제거) 과 정합.

- 변경: `out.append(kw.strip())` → `norm = kw.strip().lower(); if norm not in seen: seen.add(norm); out.append(norm)`
- 효과: 외부 feed 의 `"ScamA"`, `"scama"` 같은 case-insensitive 중복 자동 dedup
- 정합: `load_phishing_keywords` 의 custom + bundled normalize 와 동일 (lowercase + first-occurrence)

### fix 2: `test_fetch_openphish_empty_on_error_v0_7_60` 의 no-mock 호출 제거 (v0.8.11)

기존 test 는 *offline test env* 를 가정하고 `mod.fetch_openphish_feed()` (no mock) 호출 후
`result == []` 검증. 그러나 CI/dev 환경에서는 network 가 *available* 이고
OpenPhish feed 가 정상 return → 300+ real URLs → test fail.

본 release 에서 `requests_get` mock 으로 OSError raise → function 이 offline-safe
fallback 으로 `[]` return 하는지 verify. *real network* 환경에서도 test 가
deterministic 하게 동작.

- 변경: 두 번째 no-mock 호출 (`mod.fetch_openphish_feed()`) 제거
- 효과: offline-safe contract 의 mock-based 검증. *real network unavailable* 이라는
  환경 의존성 제거.

## 운영 누적 (v0.7.5 → v0.8.11)

| | v0.7.5 | v0.8.0 | v0.8.7 | v0.8.9 | v0.8.10 | **v0.8.11** |
|---|---|---|---|---|---|---|
| **phishing test** | 6 | 8 | 8 | 8 | 8 | **8** |
| **5 module test** | 64 | 122 | 122 | 122 | 122 | **122** |
| **phishing test fail** | 0 | 2 | 2 | 2 | 2 | **0** |

## In-flight 발견 + fix

- **fix 1**: `phishing_keywords.py:_load_external_feed` 가 raw keyword 그대로 return.
  test 의 case-insensitive dedup expectation 과 정합하지 않음. 본 release 에서
  lowercase + dedup 추가.
- **fix 2**: `tests/check_phishing_keywords.py: test_fetch_openphish_empty_on_error_v0_7_60`
  가 offline test env 가정. CI/dev 의 network availability 에 따라 fail.
  본 release 에서 mock-based verify 로 변경, environment 의존성 제거.
- (없음) — pre-existing bug fix 만, 신규 기능 0

## Test 결과

- **phishing_keywords**: 6/8 → **8/8 PASS** (2 pre-existing fix)
  - `test_load_external_feed_jsonl_v0_7_60` — `_load_external_feed` 의 case-insensitive normalize verify
  - `test_fetch_openphish_empty_on_error_v0_7_60` — mock-based offline-safe fallback verify
- 회귀 (5 module + dispatcher + read-only): 변동 없음
  - 5 module: **122/122 PASS** (이전 120, +2 phishing fix)
  - dispatcher: 53/53 PASS
  - version auto-sync: 4/4 PASS
  - bitbucket_v2: 2/2 PASS
  - read-only manifest: 4/4 PASS
- gen-schema --check: check_status: identical, 85,743 bytes

**cumulative test**: 122 (phishing 8 + url_validity 14 + path_resolver 12 + okf_import 25 + release_pipeline_lib 7 + cache_migration 5) + dispatcher 53 + version 4 + bitbucket 2 + read-only 4 = **134 PASS**

## 변경 파일 (3 변경)

| 변경 | File | 변경량 |
|---|---|---|
| M | `workflow_kit/phishing_keywords.py` | +10 / -3 (lowercase + dedup) |
| M | `tests/check_phishing_keywords.py` | +8 / -4 (mock-based test, no-mock 호출 제거) |
| A | `workflow-source/releases/Beta-v0.8.11.md` | release note |
| A | `ai-workflow/memory/release/v0.8.11/backlog/2026-06-17.md` | plan |

## 다음 (v0.8.12+ / v0.9.0)

1. **v0.8.12**: `workflow_kit/common/state/builder.py` 35 error (mypy strict 9단계)
2. **v0.8.13**: `workflow_kit/common/contracts/baselines.py` 27 error (mypy strict 10단계)
3. **v0.9.0** full mypy strict
4. (별도) GH Actions weekly cron — `consumer-metrics --digest-markdown`
5. (별도) spec §9 acceptance 미완 3건
