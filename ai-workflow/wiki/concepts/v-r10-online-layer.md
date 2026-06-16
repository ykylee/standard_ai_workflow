---
type: concept
status: active
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: verified_via_adr-012 (proposed, v0.7.36+ candidate)
contradiction_flags: []
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
---

# V-R10 Online HEAD Layer (ADR-012 + ADR-013)

- 문서 목적: V-R10 offline 8 check (ADR-010) 의 *online* companion. runtime HTTP HEAD request 로 stale URL / TLS error / DNS failure / 5xx transient / rate limit detect. 24h disk cache + smart retry (ADR-013).
- 범위: 8 online case (HTTP 200/3xx/404/410/5xx/429/timeout/TLS/DNS) + cache layer + mode matrix + 16 test
- 최종 수정일: 2026-06-16

## §0 Status Notice  {#s0-status}

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **active** (v0.7.35 release 시점 PoC, v0.7.36 release 시 formal) |
| 2 | ADR | ADR-012 (online layer) + ADR-013 (cache) |
| 3 | 도입 버전 | v0.7.35 (PoC) / v0.7.36 (formal) |
| 4 | 면제 범위 | offline only (default) — `--online` opt-in, `--cache` opt-in |
| 5 | Lint 심각도 | strict = error (404/410/TLS/DNS) / warn (5xx/timeout/429) — loose = warn (모두) |
| 6 | CI integration | `.github/workflows/okf-validate.yml` — weekly cron + on-PR |
| 7 | Lint 위치 | `workflow-source/workflow_kit/url_validity.py` (PoC, 14.3 KB) + 16 test |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | Layer | **Online HEAD** (HTTP HEAD request) |
| 2 | 8 case | 200 OK (pass) / 3xx (follow 1 hop) / 404/410 (error stale) / 5xx (warn transient) / 429 (warn) / timeout (warn) / TLS (error) / DNS (error) |
| 3 | Opt-in flag | `--online` (default offline only) |
| 4 | Cache layer | `--cache` (default off) + 24h TTL + exponential backoff (1s/2s/4s) + max 3 retries |
| 5 | Default cache | `~/.workflow_kit/url_validity_cache.json` |
| 6 | CLI flag | `--cache --ttl <sec> --max-retries <n> --cache-stats --cache-clear` |
| 7 | CI integration | `GITHUB_TOKEN` auto-inject (rate limit 5000 req/h, unauth 60 req/h) |
| 8 | Lint 심각도 | strict = error (404/410/TLS/DNS) + warn (5xx/timeout/429) / loose = warn (모두) |

## §2 Online 8 Case  {#s2-online-case}

| # | Case | HTTP code / behavior | Severity (strict) | Severity (loose) |
|---|---|---|---|---|
| 1 | OK | 200 | (no issue) | (no issue) |
| 2 | Redirect | 3xx (Location header) | (follow 1 hop, recheck) | (same) |
| 3 | Not found / gone | 404 / 410 | **error** (stale URL) | warn |
| 4 | Server error | 5xx (after 3 retries) | warn (transient) | warn |
| 5 | Rate limit | 429 (after 3 retries) | warn (back off) | warn |
| 6 | Connection timeout | socket.timeout (after 3 retries) | warn (slow host) | warn |
| 7 | TLS error | ssl.SSLError | **error** (security risk) | warn |
| 8 | DNS failure | urllib.error.URLError (Name or service not known) | **error** (host does not exist) | warn |

## §3 Cache Layer (ADR-013)  {#s3-cache}

| # | 항목 | 값 |
|---|---|---|
| 1 | Cache key | URL (canonical form) |
| 2 | Cache value | `{"timestamp": <unix epoch>, "issues": [{"rule", "severity", "message"}]}` |
| 3 | Cache file | `~/.workflow_kit/url_validity_cache.json` (default, override) |
| 4 | TTL | 86400s (24h, default, override) |
| 5 | Storage format | JSON (human-readable) |
| 6 | Concurrent access | *not safe* (future: `fcntl.flock`) |
| 7 | Size cap | *unbounded* (future: 10MB + LRU) |

## §4 Smart Retry (Exponential Backoff)  {#s4-retry}

| Attempt | Delay | Trigger |
|---|---|---|
| 1 (initial) | 0s | first try |
| 2 | 1s | 5xx / 429 / timeout |
| 3 | 2s | 5xx / 429 / timeout |
| 4 | 4s | 5xx / 429 / timeout (final, max 3 retries) |

**Non-retry cases** (surface immediately):
- 4xx (404/410) — stale URL detection
- TLS error (ssl.SSLError) — security risk
- DNS failure (urllib.error.URLError) — host does not exist

## §5 CLI  {#s5-cli}

```bash
# offline only (default, 8 check)
python -m workflow_kit.url_validity <url>...

# online HEAD (opt-in, 8 case)
python -m workflow_kit.url_validity <url>... --online

# online + 24h cache + smart retry
python -m workflow_kit.url_validity <url>... --online --cache

# cache management
python -m workflow_kit.url_validity --cache-stats    # print stats
python -m workflow_kit.url_validity --cache-clear    # clear cache
```

## §6 CI Integration  {#s6-ci}

`.github/workflows/okf-validate.yml` (v0.7.36) 의 `okf-online-validation` job:

```yaml
- name: V-R10 offline + online + cache
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    python3 -m workflow_kit.url_validity \
      --mode=strict --online --cache \
      --ttl 86400 --timeout 10 --max-retries 3 \
      <extracted URLs>
```

**Triggers**:
- push to `main` (paths: wiki/sample/workflow)
- pull_request to `main`
- weekly cron (Sunday 03:00 UTC)
- manual `workflow_dispatch`

**Cache isolation**: `$RUNNER_TEMP/url_validity_cache/` (PR-isolated, ephemeral)

## §7 Mode Matrix (ADR-007 §3 + ADR-010 §4 + ADR-012 §5)  {#s7-mode-matrix}

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012) — 404/410/TLS/DNS | **error** | warn |
| online HEAD (ADR-012) — 5xx/timeout/429 | warn | warn |
| cache layer (ADR-013) | (no new error) | (no new error) |

## §8 Linter Spec  {#s8-linter}

### §8.1 API

```python
from workflow_kit.url_validity import check_url, check_url_online, check_url_with_cache

# offline only
issues = check_url("https://example.com/spec.md")

# online (opt-in)
issues = check_url_online("https://example.com/spec.md", timeout=10.0, max_retries=3)

# online + 24h cache
issues = check_url_with_cache(
    "https://example.com/spec.md",
    cache_file=Path("~/.workflow_kit/url_validity_cache.json"),
    ttl_seconds=86400,
)
```

### §8.2 Test Cases (16 test, 16/16 PASS)

| # | Test | Expected |
|---|---|---|
| 1-6 | offline 8 check | (offline tests, see v-r10-url-validity-lint.md) |
| 7-12 | online 8 case (200/404/500/timeout/TLS/DNS) | (online tests) |
| 13 | test_cache_miss_then_hit | 1st = live check, 2nd = cache hit (no network) |
| 14 | test_cache_ttl_expired | TTL > 1s → fresh re-check |
| 15 | test_cache_stats | total/fresh/expired counters |
| 16 | test_cache_clear | cache file removal |

## §9 Rationale  {#s9-rationale}

### §9.1 Why opt-in (not default)?

- **Local dev offline 원칙**: ADR-010 §4 의 "local dev offline" 정신. `--online` opt-in = local dev 의 *no network* 환경 preserve.
- **CI vs local 분기**: CI 는 `--online` 자동 활성, local dev 는 opt-out (default offline).
- **Runtime 비용**: 100 URL × 5s = 500s per CI run. opt-in = *conscious choice*.

### §9.2 Why 24h TTL (not 1h or 1w)?

- **Balance**: 너무 짧으면 (1h) cache hit rate ↓ → runtime 비용 ↑. 너무 길면 (1w) stale URL catch lag ↑.
- **24h = daily** + **weekly cron (Sunday)** 의 *24h 간격* 으로 *weekly* stale URL catch. 
- **Default 만 override 가능**: 운영자가 `ttl_seconds=3600` (1h) 또는 `ttl_seconds=604800` (1w) 설정 가능.

### §9.3 Why JSON (not pickle / msgpack)?

- **Human-readable**: 운영자가 `cat ~/.workflow_kit/url_validity_cache.json` 으로 직접 확인 가능.
- **Cross-version**: JSON 의 forward-compatibility — schema 변경 시 *partial parse* 가능.
- **No dep**: stdlib `json` 만 사용. *no extra dep*.

### §9.4 Why smart retry (exponential backoff)?

- **Transient 5xx mitigation**: GitHub 의 *temporarily 5xx* (load balancer) 가 *real* stale URL 로 misclassify 방지. retry 후 *real* 5xx 면 *warn*.
- **Rate limit back-off**: 429 즉시 *warn* (not error). 다음 run 에서 retry.
- **Bounded cost**: max 3 retries + exponential 1s/2s/4s = *at most 7s extra delay* per URL.

## §10 Compliance  {#s10-compliance}

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 online row 추가
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-010 §8](../decisions/adr-010-v-r10-url-validity-lint) Follow-up: V-R10 v2 = ADR-013 의 정공법
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online 8 case unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache + smart retry

## §11 Related  {#s11-related}

- [[concepts/v-r10-url-validity-lint]] — V-R10 offline rule. 본 page 의 *companion* (online layer).
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 page 의 *parent* ADR.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. 본 page 의 *primary* ADR.
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. cache layer ADR.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL populate 직후 cache store.

## §12 Revision Log  {#s12-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-012 (online) + ADR-013 (cache) 의 concept page. 8 online case + cache + retry + 16 test spec. | Sisyphus (orchestrator) |
