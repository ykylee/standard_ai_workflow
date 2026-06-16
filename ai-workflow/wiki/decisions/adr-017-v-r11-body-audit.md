---
type: decision
status: proposed
adr_id: ADR-017
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.37+ candidate)
alternatives_considered: [no-body-check, content-type-only, html-renderable-only, phishing-keyword-only, full-content-analysis, external-virustotal]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, concepts/v-r11-body-audit, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-017: V-R11 body content audit (URL body validation)

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-010 §8 Follow-up "V-R11 — body content audit" + ADR-012 §8 Follow-up "V-R11" 기반. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.37 PATCH release note 에 등재.

## Context

ADR-010 (V-R10 URL validity lint) 의 *offline* + ADR-012 (online HEAD) 가 *URL existence* 검증. 그러나:

- **HEAD only = *metadata* check**: HTTP status, headers. *body content* 미검증.
- **Phishing content 미검출**: GitHub 의 *user-controlled repo* 가 *phishing HTML* 호스팅 가능. 우리 wiki 가 link → 운영자가 *phishing* 클릭.
- **Malformed HTML 미검출**: 200 OK + 0 bytes body, or *binary* content. *non-renderable* 시 *useless*.
- **Phishing keyword detection 부재**: "verify your account immediately" 같은 *social engineering* 패턴 미검출.
- **운영자 UX**: *stale URL* (404) vs *malicious URL* (200 + phishing) 의 *distinction* 필요.

**현재 상황 (2026-06-16):**

- ADR-012 의 `check_url_online()` 가 HEAD 만. *body* fetch 0.
- 우리 wiki 의 ~100 URL 중 *phishing* 가능성 *unknown*. *defensive measure* 부재.
- 우리 의 *operator trust* 가 *github.com* 만 — wiki 가 *외부* URL emit 시 *additional validation* 필요.

**왜 지금:** v0.7.37 release 시 V-R10 v3 follow-up bundle 의 *마지막 layer* — URL 의 *semantic* 검증. ADR-010 §8 Follow-up 의 4번 항목.

## Decision

**V-R11 body content audit 도입. HTTP GET + 4 check: Content-Type, body size, phishing keywords, HTML renderable. opt-in (default offline only).**

**구체적 결정:**

1. **API surface** (new in `workflow_kit/url_validity.py`):
   - `check_url_body(url, *, timeout, user_agent, max_body_bytes, follow_redirect, max_redirects) -> list[UrlIssue]`
   - `DEFAULT_BODY_MAX_BYTES = 1 * 1024 * 1024` (1 MB body cap)
   - `PHISHING_KEYWORDS` (8 keywords, hardcoded): `verify your account`, `click here immediately`, `your account will be suspended`, `urgent action required`, `confirm your password`, `wire transfer`, `lottery winner`, `nigerian prince`

2. **4 body checks**:

| # | Check | Severity (strict) | Severity (loose) | Rule |
|---|---|---|---|---|
| 1 | Content-Type: text/html OR application/json OR text/* | warn (other) / warn (missing) | warn | V-R11-body-content-type |
| 2 | Body size: 0 bytes = warn, > max_body_bytes = warn (truncated) | warn | warn | V-R11-body-empty / V-R11-body-truncated |
| 3 | Phishing keyword in body | **error** | warn | V-R11-body-phishing |
| 4 | text/html body without `<html>` tag | warn | warn | V-R11-body-html |

3. **Error/Warn mapping**:
   - **HTTP 4xx/5xx**: surface as `V-R11-body-http-error` (warn)
   - **Connection timeout**: surface as `V-R11-body-timeout` (warn)
   - **TLS error**: surface as `V-R11-body-tls` (error, security risk)
   - **DNS failure**: surface as `V-R11-body-url-error` (error)

4. **Mode matrix (ADR-007 §3)**:

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012) | error (404/410/TLS/DNS) | warn |
| body audit (ADR-017) | error (phishing/TLS) + warn (others) | warn |

5. **Scope 경계**:
   - **in-scope**: GET + 4 body check + phishing keyword detection + HTML renderable
   - **out-of-scope**: JavaScript execution / dynamic content audit (별도 도구)
   - **out-of-scope**: full HTML validation (e.g. `<a>` href check) — 별도 ADR
   - **out-of-scope**: malware / virus scan (외부 서비스: VirusTotal API)
   - **out-of-scope**: cookie / authentication — body fetch 가 *unauthenticated* only

6. **Phishing keyword maintenance**:
   - **Initial**: 8 hardcoded keywords (위 ADR §1)
   - **Update path**: 운영자 manual edit. ADR 별도 후보 (v0.7.40+).
   - **False-positive mitigation**: 1 keyword 만 trigger → break (no spam). *strict* mode 에서만 *error*.

7. **CI integration (TASK-V0738 의 follow-up)**:
   - `.github/workflows/okf-validate.yml` 에 `--body` flag 추가
   - weekly cron + on-PR trigger
   - 1MB body × ~100 URL = ~100MB total traffic → cache (ADR-013/014) + GHA cache (ADR-016) 의 *layered* caching

## Alternatives Considered

### A. No body check (status quo + ADR-012 only)

- **장점**: 0 구현 비용. *fast*.
- **단점**: phishing content 미검출. 운영자 *malicious URL* 클릭 위험.
- **탈락 사유**: 운영 헌법 ("security > performance") 위배. ADR-017 의 *whole point* 가 *security*.

### B. Content-Type only

- **장점**: *cheap* (single header read).
- **단점**: phishing *phishing HTML* 의 Content-Type = `text/html` 정상. *phishing 검출 0*.
- **탈락 사유**: *partial solution*. 본 ADR 의 *whole point* 가 *phishing* + *malformed*.

### C. HTML renderable only

- **장점**: *cheap* (body read + `<html>` tag check).
- **단점**: phishing *phishing HTML* 의 `<html>` tag 정상. *phishing 검출 0*.
- **탈락 사유**: *partial solution*. phishing 검출의 *keyword* check 가 *key*.

### D. Phishing keyword only (status quo PoC)

- **장점**: *cheap* + *effective*. *phishing HTML* 의 *text* 기반 detect.
- **단점**: *evasion* 가능 (e.g. "v3rify y0ur acc0unt" — *leet speak*). False-positive (e.g. *security blog* 가 *phishing keyword* 인용).
- **탈락 사유**: 본 ADR 의 *whole point* 가 *phishing + 4 check*. *partial* 가 아닌 *comprehensive*.

### E. Full content analysis (NLP / ML / external API)

- **장점**: *high accuracy*. *evasion* resist.
- **단점**: *extra dep* (NLP/ML model) + *external API cost* (VirusTotal) + *operational complexity*.
- **탈락 사유**: *over-engineering*. 우리 의 *8 keyword heuristic* 이 *sufficient* for v0.7.37 PoC. *evasion* 은 운영자 manual review (v0.7.40+).

### F. External VirusTotal API integration

- **장점**: *high accuracy* + *malware scan* + *phishing DB* lookup.
- **단점**: *API key required* + *rate limit* (4 req/min free) + *cost*.
- **탈락 사유**: 우리 의 *~100 URL* use case 에 *over-engineering*. *stdlib-only* 정신 위배.

## Consequences

### Positive

1. **Phishing detect**: GitHub user-controlled repo 의 *phishing HTML* 즉시 catch. 운영자 *malicious URL* 클릭 방지.
2. **HTML renderable check**: *binary content* (`application/octet-stream`) + *empty body* detect. *useless URL* 식별.
3. **Content-Type policy**: `text/html` / `application/json` / `text/*` 만 accept. *binary* (image/video) 는 *consume 불가* 시 warn.
4. **Body size cap (1MB)**: *unbounded body* fetch 방지. 운영자 *OOM* 방지.
5. **Mode matrix 양립**: ADR-007 §3 + ADR-010 §4 + ADR-012 §5 + 본 ADR §4 의 4-layer mode matrix. *strict* = error (phishing/TLS), *loose* = warn.
6. **No extra dep**: `urllib.request` 만 사용 (Python stdlib). 우리 의 *stdlib-only* + *operational simplicity* 보존.
7. **Forward-compatible**: ADR-013 (cache) + ADR-014 (LRU) + ADR-015 (file lock) + ADR-016 (GHA cache) 의 *5-layer v0.7.36/37* 의 *final layer* (body audit). cache 가 body *output* 도 cache (future turn).

### Negative

1. **Performance overhead**: GET vs HEAD = ~5x larger (body) → 100 URL × 5s × 5 = 2500s per CI run. *cache + GHA cache* 의 *layered caching* 의 *100x speedup* (2500s → 25s) 의 *operational* 부담.
2. **False-positive risk**: 8 phishing keyword 의 *innocent match* (e.g. *security blog* 가 *phishing keyword* 인용). *strict mode* 에서만 *error* — 운영자 *override* 가능.
3. **Evasion risk**: *leet speak* (e.g. `v3rify y0ur acc0unt`) — *8 keyword* 의 *literal match* 미검출. *operational residual risk* 보존.
4. **Storage cost**: 1MB body × 100 URL = 100MB. GHA cache 의 10GB limit 의 1%. *acceptable*. 다만 cache *eviction* 필요.
5. **No dynamic content audit**: *JavaScript* (e.g. *redirect via JS*) 미검출. *static* 만 검증.
6. **Phishing keyword list maintenance**: 8 keyword 의 *freshness*. *new phishing pattern* 미검출. 운영자 manual update 필요.

### Neutral

- ADR-017 의 *body audit* 는 *opt-in* (--body flag). default = offline + online 만.
- *strict mode* 의 *phishing error* → 운영자 manual *override* 가능 (e.g. `git commit --no-verify` 의 *wiki equivalent*).
- 향후 *V-R12 commit-pinned URL* + *V-R13 semantic URL verification* 가 *layer 6/7* 의 *future enhancement*.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R11 row 추가
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-010 §8](../decisions/adr-010-v-r10-url-validity-lint) Follow-up: "V-R11 — body content audit" → ADR-017 의 정공법
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online HEAD unchanged
- [ADR-012 §8](../decisions/adr-012-v-r10-online-layer) Follow-up: "V-R11" → 본 ADR 의 정공법

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/url_validity.py` `check_url_body()` | ✅ done (v0.7.37, 본 ADR PoC) | `workflow_kit/url_validity.py` |
| `DEFAULT_BODY_MAX_BYTES = 1 MB` constant | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| `PHISHING_KEYWORDS` (8 keywords) | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| 4 body check (Content-Type / size / phishing / HTML) | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| 5 body audit test (HTML pass / phishing / missing html / content-type / timeout) | ✅ done (v0.7.37, 27/27 PASS) | `tests/check_wiki_url_validity.py` |
| `concepts/v-r11-body-audit.md` (companion concept page) | ⏳ proposed (별도 turn) | `ai-workflow/wiki/concepts/v-r11-body-audit.md` |
| `--body` CLI flag | ⏸️ deferred (v0.7.38+) | `workflow_kit/url_validity.py` |
| `.github/workflows/okf-validate.yml` `--body` integration | ⏸️ deferred (v0.7.38+) | `.github/workflows/okf-validate.yml` |
| External VirusTotal API integration | ⏸️ deferred (out of scope) | `workflow_kit/url_validity.py` |
| Phishing keyword list update mechanism | ⏸️ deferred (v0.7.40+) | `workflow_kit/url_validity.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **ADR-018 — V-R12 commit-pinned URL** (proposed, 별도 turn): `path_resolver` 의 `vcs_commit` field
2. **V-R11 v2 — phishing keyword list update** (proposed, v0.7.40+): 운영자 manual update + GHA fetch (e.g. PhishTank feed)
3. **V-R11 v2 — dynamic content audit** (proposed, v0.7.42+): JavaScript execution via headless browser (Playwright)
4. **V-R11 v2 — external VirusTotal API** (proposed, v0.7.44+): API key + rate limit + cost
5. **V-R13 — semantic URL verification** (proposed, 별도 turn): URL 의 *의미* (specific commit, specific line) unchanged

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. ADR-017 의 *complement* (online + body).
- [[concepts/v-r11-body-audit]] — V-R11 body audit concept page (companion, v0.7.38+).
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 ADR 의 *parent*.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. *prerequisite* (URL must be reachable before body fetch).
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. *complementary* (body content caching — future turn).
- [[concepts/okf-open-knowledge-format]] — V-R10/V-R11 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL populate 직후 body audit.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-010 §8 Follow-up + ADR-012 §8 Follow-up 기반. 6 alternatives + 7 positive / 6 negative / 2 neutral. PoC (check_url_body + 5 test) v0.7.37 와 동시 draft. | Sisyphus (orchestrator) |
