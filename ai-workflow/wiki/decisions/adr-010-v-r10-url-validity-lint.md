---
type: decision
status: accepted
adr_id: ADR-010
decided_at: 2026-06-16
accepted_in: v0.7.35 (release note: workflow-source/releases/Beta-v0.7.35.md)
alternatives_considered: [online-only-head, offline-only-syntax, hybrid-cached, scheduled-ci-only, no-formal-decision]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-006-okf-compat-frontmatter, decisions/adr-008-in-repo-path-to-url, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit, decisions/adr-012-v-r10-online-layer, releases/Beta-v0.7.35]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-010: V-R10 URL validity lint (offline + optional online HEAD)

## Status

**Accepted** (2026-06-16, v0.7.35). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.35 release note 와 동시 accepted. 8 offline check PoC (`workflow_kit/url_validity.py`, 6/6 PASS) 가 우리 wiki lint suite 의 한 row 로 정식 등록. online HEAD layer 는 ADR-012 follow-up.

## Context

ADR-006 (OKF 5-field bridge) 채택으로 wiki 의 `resource` field 와 `last_ingested_from` URL 이 OKF spec 의 *canonical URI for the underlying asset* 의미로 emit 된다. ADR-008 (v0.7.34 채택) 로 in-repo path → GitHub blob URL 자동 resolve 까지 동작. 그러나:

- **URL stale 가능**: GitHub 의 repo move, branch rename, file delete 시 URL 404
- **URL syntax 오류 가능**: 운영자 manual 입력 시 오타 (`http://` vs `https://`, trailing slash 등)
- **Security 검증 부재**: phishing URL, malicious host, internal IP 등 위험 URL 미검출
- **V-T1 과 같은 drift**: frontmatter 의 URL 과 body 의 cross-link URL 의 일관성 미검증

**현재 상황 (2026-06-16):**

- ADR-006 + ADR-008 채택. wiki 의 80% page 가 OKF `resource` URL 자동 채움.
- 우리 wiki 의 `last_ingested_from` 가 URL 인 경우 (e.g. ADR-006 의 primary source) — **stale URL 가능**.
- `concepts/okf-open-knowledge-format.md` 의 §12 follow-up 에서 *"V-R10 (URL validity) — runtime HEAD 요청, stale URL detect"* 명시.

**왜 지금:** v0.7.34 release 시 `docs/samples/okf-bundle-2026-06-16/` 의 5 page 모두 ADR-008 의 자동 resolve 로 `resource` URL 이 emit. 운영자가 sample 을 browse 시 **stale URL 가능** — 본 ADR 의 lint 가 catch.

## Decision

**URL validity lint (V-R10) 도입. 2 layer 동작: (a) offline syntax + (b) optional online HEAD request. mode flag 로 online layer opt-in.**

**구체적 결정:**

1. **2 layer 분리 (offline / online)**:
   - **offline** (default, 모든 wiki run): syntax 검증 + black/whitelist + security heuristic. *no network call*.
   - **online** (opt-in, `--v-r10-online` flag): runtime HEAD request 로 *stale URL* detect. CI / cron 전용. local dev opt-out.

2. **Offline 검증 항목 (8 check)**:

| # | Check | Severity (strict) | Severity (loose) |
|---|---|---|---|
| 1 | URL scheme — `https://` only (no `http://`, `ftp://`, `file://`) | error | warn |
| 2 | URL host parseable (RFC 3986 compliant) | error | warn |
| 3 | No path traversal (`..` segment reject) | error | warn |
| 4 | No internal/private IP (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `::1`, `fc00::/7`) | error | warn |
| 5 | No localhost (`localhost`, `*.local`) | error | warn |
| 6 | No file:// scheme (no local file references) | error | warn |
| 7 | No credentials in URL (`user:pass@`) | error | warn |
| 8 | GitHub URL form (if host = `github.com`): `/blob/<branch>/<path>` or `/tree/<branch>/<path>` | warn | warn |

3. **Online 검증 항목 (HEAD request)**:

| # | Check | Behavior |
|---|---|---|
| 1 | HTTP status 200 OK | PASS |
| 2 | HTTP status 3xx (redirect) | follow 1 hop, recheck |
| 3 | HTTP status 404/410 (not found / gone) | FAIL — stale URL |
| 4 | HTTP status 5xx (server error) | WARN — transient (retry next run) |
| 5 | Connection timeout (> 10s) | WARN — slow host |
| 6 | TLS error (cert invalid / expired) | FAIL — security risk |
| 7 | DNS resolution failure | FAIL — host does not exist |
| 8 | Rate limit (429) | WARN — back off |

4. **Mode matrix (ADR-007 §3 mode matrix 통합)**:

| Layer | strict | loose |
|---|---|---|
| offline 8 check | error | warn |
| online HEAD (opt-in) | error (404/410), warn (5xx/timeout) | warn |

5. **Scope — 어디서 URL extract?**:
   - **wiki frontmatter**: `resource` (ADR-006 OKF field) + `last_ingested_from`
   - **wiki body**: `[[path/to/page#anchor]]` 의 in-wiki cross-link (R-4 anchor schema)
   - **external link**: body 의 `[text](https://...)` form
   - **OKF bundle**: `docs/samples/*/index.md` 의 frontmatter + body
   - **in scope**: 우리 wiki + OKF sample bundle
   - **out of scope**: 외부 OKF bundle (ADR-007 의 loose mode + ADR-011 의 version detect)

6. **Online layer 의 운영 policy**:
   - local dev: default opt-out (--v-r10-online flag 미지정 시 skip)
   - CI (GitHub Actions): default opt-in (`--v-r10-online` 자동 활성)
   - rate limit: 5 req/sec, 100 req/min (defensive)
   - cache: 24h (URL → status code) local cache
   - timeout: 10s per URL

7. **도구 surface**: `workflow_kit/url_validity.py` (신규) + `tests/check_wiki_url_validity.py` (offline 8 check 5+ test). online layer 는 별도 turn (CI integration).

8. **Mode matrix 의 한 row 로 V-R10 추가** (ADR-007 §3):

| Lint | strict | loose |
|---|---|---|
| V-1, V-4, V-R9, V-T1, OKF §4.1 hard (기존) | (변경 없음) | (변경 없음) |
| **V-R10 offline** | **error** | **warn** |
| V-R10 online (opt-in) | error (404/410), warn (5xx/timeout) | warn |

9. **scope 경계**:
   - **in-scope**: 8 offline check + online HEAD
   - **out-of-scope**: URL body content (HTML) 검증 — 별도 lint. URL 의 *semantic* 의미 (e.g. GitHub 의 specific commit SHA) — ADR candidate.
   - **out-of-scope**: full body content audit (broken anchor, dead link destination) — V-T1 의 *future turn*.

## Alternatives Considered

### A. Online-only (HEAD request 필수)

- **장점**: stale URL 즉시 detect. syntax + security 검증도 network 응답으로 cover.
- **단점**: local dev 의 *no network* 환경 fail. CI 비용 (URL 100+ × HEAD 5s = 500s). offline 시 *blind*.
- **탈락 사유**: 운영 헌법 ("offline-deterministic preferred") 위배. ADR-008 의 *deterministic + offline* 원칙과 양립 불가.

### B. Offline-only (syntax 만)

- **장점**: 0 network 의존. local + CI 동일. 빠른 lint.
- **단점**: stale URL 미검출. GitHub repo move 시 catch 못함.
- **탈락 사유**: ADR 의 *partial solution* — *stale URL* 가 가장 흔한 fail 케이스. online layer 가 이를 cover. *hybrid* 가 정공법.

### C. Hybrid + persistent cache (online 결과 disk cache)

- **장점**: online 결과 24h cache → CI 비용 절감. stale URL detect.
- **단점**: cache invalidation 정책 (repo move 시 cache stale 가능). 24h 시간 결정.
- **탈락 사유**: 본 ADR 의 online layer 가 *default opt-in* — cache 필요성 낮음. → 본 ADR 의 online layer 는 *stateless* + 매 run fresh request. cache 는 *follow-up* (V-R10 v2).

### D. Scheduled CI only (cron + weekly)

- **장점**: lint runtime 부담 0. 운영자 manual trigger 가능.
- **단점**: stale URL detect lag (최대 1주). cron misfire 시 undetected.
- **탈락 사유**: stale URL 의 *detection speed* 가 운영자 UX 에 직결. *weekly* lag 는 너무 김.

### E. No formal decision (ad-hoc)

- **장점**: 0 의사결정 비용. *as needed* verify.
- **단점**: URL drift 누적. OKF sample 의 `resource` URL 의 신뢰성 *ad-hoc* 의존.
- **탈락 사유**: ADR-006/008 의 *formal producer* 와 양립 불가. *formal consumer* (ADR-007) 의 lint matrix 의 한 row 미정의.

## Consequences

### Positive

1. **Stale URL detect**: ADR-008 의 자동 resolve 가 stale URL 도 *valid URL* 로 emit 가능. V-R10 online 이 catch. sample bundle 의 신뢰성 ↑.
2. **Security hardening**: 8 offline check 가 malicious URL (phishing, internal IP, file://) detect. 우리 wiki 가 *untrusted content* host 가능성 ↓.
3. **Cross-layer consistency**: frontmatter URL ↔ body cross-link URL 의 V-R10 단일 lint. 운영자 *single source of lint* 보장.
4. **ADR-007 mode matrix 완성**: 8 lint × 2 mode table 의 8 row 중 V-R10 row 가 본 ADR 로 canonical. *canonical reference* 완성.
5. **CI integration 단순**: `--v-r10-online` flag 로 GitHub Actions 에서 자동 활성. local dev opt-out. 운영자 UX 단순.
6. **Lint ROI 높음**: offline 8 check 는 cheap (regex + IP parse). online 1 URL = 1 HTTP HEAD. cumulative test 의 high-value addition.
7. **Forward-compatible**: URL validity check 의 future extension (body content audit, semantic verification) 가 본 ADR 의 extension 으로 가능.

### Negative

1. **online layer 의 network 의존**: CI 환경에서만 동작. local dev 의 *offline* 환경 (e.g. airplane mode) 는 stale URL 미검출. → mitigation: offline 8 check 가 *최소한* 의 cover.
2. **CI runtime 비용**: 100 URL × 5s HEAD = 500s. GitHub Actions 의 6h timeout 내 OK이나 *slow*. → mitigation: 5 req/sec rate limit + future cache (V-R10 v2).
3. **GitHub rate limit (unauthenticated 60 req/h)**: 우리 wiki 의 100+ URL → 1.5+ 시간 소요. → mitigation: GitHub Actions 의 `GITHUB_TOKEN` 사용 (5000 req/h authenticated).
4. **false-positive 가능**: GitHub 의 *temporarily 5xx* (load balancer) 가 stale URL 로 misclassify. → mitigation: 5xx = *warn* (not error), retry next run.
5. **Cumulative lint cost**: 5 lint → 7 lint. `run_all_checks.py` 의 runtime ~30% 증가. → negligible.
6. **online layer 의 `--v-r10-online` opt-in default**: CI 에서만 자동 활성. local dev 가 *stale URL* 미검출 가능. → trade-off (offline-deterministic vs always-online).

### Neutral

- V-R10 PoC (v0.7.35) 의 5+ test 가 offline 8 check 만 cover. online layer 는 follow-up.
- V-R10 concept page 의 §1 TL;DR / §2 Rule / §3 Mode Matrix 가 본 ADR 의 §3 Decision 1-9 와 1:1 매핑.
- 운영자 manual URL 입력 시 offline 8 check 가 즉시 reject. *ad-hoc verify* 부담 감소.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-006 §3](../decisions/adr-006-okf-compat-frontmatter) Decision 1: `resource` field 채움. V-R10 가 채워진 URL 의 validity 검증
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 row 추가. strict = error, loose = warn
- [ADR-008 §3](../decisions/adr-008-in-repo-path-to-url) Decision 1-2: in-repo path → GitHub blob URL 자동 resolve. V-R10 가 resolved URL 의 validity 검증
- [concepts/okf-open-knowledge-format.md §12.1 follow-up 3](../concepts/okf-open-knowledge-format.md): *V-R10 (URL validity) — runtime HEAD 요청, stale URL detect* 해소

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/v-r10-url-validity-lint.md` (신규) | ⏳ proposed (본 ADR 채택 후) | `ai-workflow/wiki/concepts/v-r10-url-validity-lint.md` |
| `workflow_kit/url_validity.py` (offline 8 check, ~120 lines) | ⏳ proposed | `workflow-source/workflow_kit/url_validity.py` |
| `tests/check_wiki_url_validity.py` (5+ test, offline 만) | ⏳ proposed | `workflow-source/tests/check_wiki_url_validity.py` |
| `tests/run_all_checks.py` integration | ⏳ proposed (auto-discover via glob) | (no code change) |
| `--v-r10-online` CLI flag + online HEAD layer | ⏳ proposed (별도 turn, v0.7.36+) | `workflow_kit/url_validity.py` |
| GitHub Actions CI integration (--v-r10-online 자동 활성) | ⏳ proposed | `.github/workflows/ci.yml` |
| `GITHUB_TOKEN` 사용 (rate limit 5000 req/h) | ⏳ proposed | `workflow_kit/url_validity.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R10 v2 — online cache + smart retry**: 24h disk cache + exponential backoff + 5xx retry. CI 비용 ↓.
2. **V-R11 — body content audit**: URL 의 *body* 가 valid (HTML renderable, no phishing content) 검증. 본 ADR 의 out-of-scope.
3. **V-R12 — GitHub commit-pinned URL**: ADR-008 의 commit-pinned URL variant. `vcs_commit` extra frontmatter key.
4. **V-R13 — semantic URL verification**: URL 의 *의미* (specific commit, specific line, specific page section) 가 unchanged 인지 verify. *anti-link-rot* 의 정공법.
5. **GitHub Actions workflow 통합**: `.github/workflows/ci.yml` 에 `python -m workflow_kit.url_validity --v-r10-online` step 추가. cron schedule (weekly).
6. **OKF consumer mode 와 V-R10 통합**: ADR-007 의 loose mode 가 외부 OKF bundle import 시 V-R10 offline 만 (online opt-out). OKF spec §9 의 5 MUST NOT 와 양립.

## Related

- [[concepts/v-r10-url-validity-lint]] (proposed) — V-R10 rule definition. §1 TL;DR / §2 Rule / §3 Mode Matrix 가 본 ADR 와 1:1.
- [[decisions/adr-006-okf-compat-frontmatter]] — ADR-006 §3 Decision 1 의 `resource` field 가 V-R10 의 검증 대상.
- [[decisions/adr-008-in-repo-path-to-url]] — ADR-008 §3 의 자동 resolve 가 stale URL 가능. V-R10 이 cover.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source. §12.1 follow-up 3 (*V-R10 — runtime HEAD 요청, stale URL detect*) 가 본 ADR 의 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL 자동 populate. V-R10 가 populate 직후 verify.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. `concepts/okf-open-knowledge-format.md` §12.1 follow-up 3 + ADR-008 follow-up 3 기반. 8 offline check + 8 online check + 9 implementation item + 6 follow-up. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. v0.7.35 release note 등재. `related_pages` 에 ADR-012 (online layer) + Beta-v0.7.35 추가. | Sisyphus (orchestrator) |
