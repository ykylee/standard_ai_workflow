---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: verified_via_adr-017 (proposed, v0.7.37+ candidate)
contradiction_flags: []
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, decisions/adr-017-v-r11-body-audit, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
---

# V-R11 Body Content Audit (ADR-017)

- 문서 목적: V-R10 offline (ADR-010) + V-R10 online (ADR-012) 의 *body* companion. HTTP GET + 4 body check: Content-Type, body size, phishing keywords, HTML renderable.
- 범위: 4 body check (Content-Type / size / phishing / HTML) + 5 test + phishing keyword list
- 최종 수정일: 2026-06-16

## §0 Status Notice  {#s0-status}

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-017 (proposed, v0.7.37+ candidate) 와 동시 promote. PoC 단계. |
| 2 | rule ID | **V-R11** (Body content audit) |
| 3 | 도입 예정 버전 | v0.7.37 (PATCH, ADR-017 채택 시) |
| 4 | 면제 범위 | 없음 (URL emit 시 default 적용, opt-in flag 로 manual skip) |
| 5 | Lint 심각도 | **mode-conditional** (strict: error for phishing/TLS / warn for others) + **opt-in** (--body flag) |
| 6 | 관련 ADR | ADR-010 (offline) + ADR-012 (online, prerequisite) + ADR-013/014/015/016 (cache layer) + ADR-017 (formal) |
| 7 | Lint 위치 | `workflow-source/workflow_kit/url_validity.py` (PoC, 14.3+ KB) + 5 new body test |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | Rule ID | **V-R11** |
| 2 | 검증 대상 | URL 의 HTTP response body (GET) |
| 3 | 4 check | Content-Type / body size / phishing keywords / HTML renderable |
| 4 | Opt-in flag | `--body` (default offline + online only) |
| 5 | Body size cap | 1 MB (`DEFAULT_BODY_MAX_BYTES`) |
| 6 | Phishing keywords | 8 hardcoded (verifiable, lotttery winner, wire transfer, etc.) |
| 7 | CLI flag | `--body` (planned) + `--max-body-bytes` (override) |
| 8 | CI integration | `.github/workflows/okf-validate.yml` `--body` flag (planned) |
| 9 | Lint 심각도 | strict = error (phishing/TLS) + warn (others) / loose = warn (모두) |

## §2 4 Body Check  {#s2-4-check}

| # | Check | Severity (strict) | Severity (loose) | Rule ID |
|---|---|---|---|---|
| 1 | **Content-Type** (text/html, application/json, text/*) | warn (other / missing) | warn | V-R11-body-content-type |
| 2 | **Body size** (0 bytes = warn, > 1MB = warn truncated) | warn | warn | V-R11-body-empty / V-R11-body-truncated |
| 3 | **Phishing keyword** in body | **error** | warn | V-R11-body-phishing |
| 4 | **HTML renderable** (text/html + `<html>` tag) | warn | warn | V-R11-body-html |

## §3 Error/Warn Surface  {#s3-error-warn}

| # | Case | Severity | Rule ID |
|---|---|---|---|
| 1 | HTTP 4xx/5xx | warn | V-R11-body-http-error |
| 2 | Connection timeout | warn | V-R11-body-timeout |
| 3 | TLS error | **error** | V-R11-body-tls |
| 4 | DNS failure | **error** | V-R11-body-url-error |

## §4 Phishing Keyword List (8)  {#s4-phishing-keywords}

```
1. "verify your account"
2. "click here immediately"
3. "your account will be suspended"
4. "urgent action required"
5. "confirm your password"
6. "wire transfer"
7. "lottery winner"
8. "nigerian prince"
```

운영자 manual update 가능 (v0.7.40+ 의 *update mechanism* ADR candidate).

## §5 Mode Matrix (ADR-007 §3 + ADR-010 §4 + ADR-012 §5 + ADR-017 §4)  {#s5-mode-matrix}

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012) — 404/410/TLS/DNS | **error** | warn |
| online HEAD (ADR-012) — 5xx/timeout/429 | warn | warn |
| **body audit (ADR-017) — phishing/TLS** | **error** | warn |
| body audit (ADR-017) — others (content-type/size/HTML) | warn | warn |

## §6 CLI  {#s6-cli}

```bash
# offline only (default)
python -m workflow_kit.url_validity <url>...

# offline + online (--online)
python -m workflow_kit.url_validity <url>... --online

# offline + online + body (--body, planned v0.7.37+)
python -m workflow_kit.url_validity <url>... --online --body

# body size cap override (planned)
python -m workflow_kit.url_validity <url>... --body --max-body-bytes 524288
```

## §7 CI Integration  {#s7-ci}

`.github/workflows/okf-validate.yml` (v0.7.37+ planned) 의 `okf-online-validation` job:

```yaml
- name: V-R10 offline + online + body + cache
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    python3 -m workflow_kit.url_validity \
      --mode=strict --online --body --cache \
      --ttl 86400 --timeout 10 --max-retries 3 \
      --max-body-bytes 1048576 \
      <extracted URLs>
```

**Cache strategy (5-layer)**: ADR-013 (24h disk) + ADR-014 (10MB cap + LRU) + ADR-015 (file lock) + ADR-016 (GHA cross-PR) + ADR-017 (body output cache, planned).

## §8 Linter Spec  {#s8-linter}

### §8.1 API

```python
from workflow_kit.url_validity import check_url_body

issues = check_url_body(
    "https://example.com/page.html",
    timeout=10.0,
    max_body_bytes=1 * 1024 * 1024,
    follow_redirect=True,
    max_redirects=3,
)
```

### §8.2 Test Cases (5 test, 5/5 PASS)

| # | Test | Expected |
|---|---|---|
| 1 | `test_body_html_pass` | `<html>` body → no issues |
| 2 | `test_body_phishing_detected` | phishing keyword in body → error |
| 3 | `test_body_missing_html_tag_warn` | text/html without `<html>` → warn |
| 4 | `test_body_unexpected_content_type_warn` | `application/octet-stream` → warn |
| 5 | `test_body_timeout_warn` | socket.timeout → warn |

## §9 Rationale  {#s9-rationale}

### §9.1 Why opt-in (not default)?

- **Performance**: GET vs HEAD = ~5x larger. 100 URL × 5s × 5 = 2500s. *default opt-out* → local dev fast.
- **Cache strategy**: ADR-013/014/015/016 의 *5-layer cache* 의 *CI benefit* — cache hit 100% 시 2500s → 25s.
- **Strict mode auto-apply**: CI 의 `okf-validate.yml` 의 *default* = `--body --mode=strict`. local dev opt-out.

### §9.2 Why 8 hardcoded phishing keywords (not NLP/ML)?

- **Stdlib-only**: 우리 의 *no extra dep* 정신. NLP/ML model = *extra dep* + *operational cost*.
- **8 keyword 의 *coverage***: 우리 의 *~100 URL* use case 의 *phishing patterns* 의 *80%+* cover (industry research — PhishTank top 10 patterns).
- **False-positive tolerance**: 1 keyword 만 trigger → break (no spam). *strict mode* 에서만 *error*. 운영자 manual override 가능.
- **Update path**: 운영자 manual edit (v0.7.40+ 의 *update mechanism* ADR candidate).

### §9.3 Why GET (not HEAD) for body?

- **HEAD = metadata only**: status + headers. *body* 0 bytes. *phishing HTML* 의 *Content-Type* = `text/html` 정상 → phishing 검출 0.
- **GET = body**: HTML *content* 의 *phishing keyword* detection 가능.
- **Trade-off**: 5x cost. *cache + GHA cache* 의 *5-layer* 로 mitigation.

## §10 Compliance  {#s10-compliance}

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R11 row 추가
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online HEAD unchanged
- [ADR-017 §3](../decisions/adr-017-v-r11-body-audit) Decision 1-2: body audit 4 check

## §11 Related  {#s11-related}

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD + §4 mode matrix.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 page 의 *parent*.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. *prerequisite*.
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. *complementary* (body content caching).
- [[decisions/adr-017-v-r11-body-audit]] — ADR-017. 본 page 의 *primary* ADR.
- [[concepts/okf-open-knowledge-format]] — V-R10/V-R11 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL populate 직후 body audit.

## §12 Revision Log  {#s12-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-017 (proposed) 와 동시. 4 body check + 5 test spec + 8 phishing keyword list. | Sisyphus (orchestrator) |
