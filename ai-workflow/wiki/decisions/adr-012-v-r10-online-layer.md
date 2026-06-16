---
type: decision
status: proposed
adr_id: ADR-012
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.36+ candidate)
alternatives_considered: [no-online, online-always, online-cache-only, scheduled-ci-only, opt-in-cli-flag]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-013-v-r10-v2-cache, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-012: V-R10 online HEAD layer (--v-r10-online opt-in)

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-010 §3 Decision 7 (online layer opt-in) + `concepts/okf-open-knowledge-format.md` follow-up + ADR-008 follow-up 3 기반. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.36 PATCH release note 에 등재.

## Context

ADR-010 (V-R10 URL validity lint) 의 §3 Decision 7 (online layer opt-in) + ADR-010 §7 Implementation 의 6 item 중 online layer (1 item, "online HEAD layer opt-in CI integration") 가 v0.7.34/v0.7.35 release 에서 미구현.

**현재 상황 (2026-06-16):**

- ADR-010 의 8 offline check PoC 만 6/6 PASS
- `workflow_kit/url_validity.py` 에 `check_url_online()` 함수 부재
- CLI 의 `--online` flag 부재
- GitHub Actions 의 `okf-validate.yml` workflow 부재
- 우리 의 `docs/samples/okf-bundle-2026-06-16/` 의 5 page 가 ADR-008 의 자동 resolve 로 `resource` URL emit. 그러나 *stale URL* (GitHub repo move, branch rename, file delete) 의 detect 부재.

**왜 지금:** v0.7.34 release 시 5 page PoC sample bundle 의 `resource` URL 이 emit. 운영자가 browse 시 **stale URL 가능**. 본 ADR 의 online layer 가 catch.

## Decision

**V-R10 의 online HEAD layer 구현. CLI flag `--online` 으로 opt-in. CI 환경에서 자동 활성 (별도 turn).**

**구체적 결정:**

1. **API surface** (`workflow_kit/url_validity.py` enhancement):
   - `check_url_online(url, *, timeout=10.0, user_agent="workflow-kit-url-validity/0.7.35") -> list[UrlIssue]`
   - HTTP HEAD request → 200/3xx/4xx/5xx/timeout/TLS/DNS 별 issue
   - urllib 만 사용 (no extra dep)
   - 최대 1 redirect hop

2. **Online check 분류 (8 case)**:

| Case | Severity | Rule ID |
|---|---|---|
| HTTP 200 OK | (no issue) | — |
| HTTP 3xx (redirect, follow 1 hop) | (recheck) | V-R10-online-redirect |
| HTTP 404/410 (not found / gone) | error | V-R10-online-stale |
| HTTP 5xx (server error) | warn | V-R10-online-server-error |
| HTTP 429 (rate limit) | warn | V-R10-online-rate-limit |
| Connection timeout (> 10s) | warn | V-R10-online-timeout |
| TLS error (cert invalid / expired) | error | V-R10-online-tls |
| DNS failure (host does not exist) | error | V-R10-online-url-error |

3. **CLI flag**: `--online` (default offline only) + `--timeout <seconds>` (default 10.0). `--v-r10-online` alias — same flag, RFC-style naming.

4. **CI integration (별도 turn, TASK-V0738)**:
   - GitHub Actions 의 `.github/workflows/okf-validate.yml` 작성
   - weekly cron + on-PR trigger
   - `GITHUB_TOKEN` env var 자동 사용 (GitHub rate limit 5000 req/h, unauth 60 req/h)
   - `python -m workflow_kit.url_validity <url>... --online --mode=strict`

5. **Mode matrix (ADR-007 §3 + ADR-010 §4)**:

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012, opt-in) | error (404/410/TLS/DNS) + warn (5xx/timeout/rate-limit) | warn (모두) |

6. **scope 경계**:
   - **in-scope**: HTTP HEAD request + 1 redirect hop + 8 case 분류 + 8 UrlIssue rule
   - **out-of-scope**: cache (별도 ADR-013) + exponential backoff (별도 ADR-013) + `GITHUB_TOKEN` integration (별도 TASK-V0738) + body content audit (별도 ADR candidate)

7. **Cumulative test**: 6 → 12 (+6 online test). PoC 단계.

## Alternatives Considered

### A. No online (status quo + ADR-010 accepted)

- **장점**: 0 구현 비용. *deterministic + offline* 원칙.
- **단점**: stale URL 미검출. ADR-010 §5 의 "security hardening" 의 50% 만 cover.
- **탈락 사유**: 운영 헌법 ("operational safety > offline purity") 위배. stale URL 의 *detection speed* 가 운영자 UX 에 직결.

### B. Online always (default)

- **장점**: stale URL 즉시 detect. 운영자 manual trigger 불필요.
- **단점**: local dev 의 *no network* 환경 fail. ADR-010 §4 의 "local dev offline" 정신 위배.
- **탈락 사유**: opt-in 정신 위배. ADR-007 mode matrix 와 양립 불가.

### C. Online cache only (no live check)

- **장점**: 0 network 의존. CI 비용 0.
- **단점**: cache 가 stale 가능. ADR-013 (V-R10 v2 cache) 의 cache policy 가 필요. *전제조건* 미충족.
- **탈락 사유**: ADR-013 의 1차 evidence 미확보. 본 ADR 는 ADR-013 의 *dependency* — 선행 필요.

### D. Scheduled CI only (cron + weekly)

- **장점**: lint runtime 부담 0. 운영자 manual trigger 가능.
- **단점**: stale URL detect lag (최대 1주). cron misfire 시 undetected.
- **탈락 사유**: stale URL 의 *detection speed* 가 운영자 UX 에 직결. *weekly* lag 는 너무 김. ADR-010 §4 의 *ci-time* 정공법.

### E. Opt-in CLI flag (status quo + CLI flag)

- **장점**: local dev opt-out / CI opt-in. 운영자 control.
- **단점**: 운영자가 manual flag 미기재 시 stale URL 미검출. *silent failure* 가능.
- **탈락 사유**: ADR-007 mode matrix 와 양립. *opt-in* 정신. ADR-012 의 정공법 (선택).

## Consequences

### Positive

1. **Stale URL detect**: GitHub 의 repo move / branch rename / file delete 즉시 catch. sample bundle 의 신뢰성 ↑.
2. **Security hardening 추가**: TLS error + DNS failure 의 *security risk* detect. 우리 wiki 가 *untrusted content* host 가능성 ↓.
3. **Opt-in principle**: local dev 의 *no network* 환경 preserve. CI / 운영자 manual trigger 만 활성.
4. **Mode matrix 양립**: ADR-010 §4 의 mode matrix 의 2 row 추가. strict = error, loose = warn.
5. **PoC 검증 완료**: 6/6 → 12/12 PASS (offline + online). 5-run stable.
6. **No extra dep**: urllib 만 사용 (Python stdlib). pyproject.toml 의 dependency list 변경 0.
7. **Forward-compatible**: ADR-013 (V-R10 v2 cache) 의 cache layer 가 *additive* — ADR-012 의 8 issue rule 변경 없이 cache wrap 만 추가.

### Negative

1. **Network 의존**: CI 환경에서만 동작. local dev 의 *offline* 환경 (e.g. airplane mode) 는 stale URL 미검출. → mitigation: offline 8 check 가 *최소한* 의 cover.
2. **CI runtime 비용**: 100 URL × 5s HEAD = 500s. GitHub Actions 의 6h timeout 내 OK이나 *slow*. → mitigation: 5 req/sec rate limit + ADR-013 의 cache.
3. **GitHub rate limit (unauthenticated 60 req/h)**: 우리 wiki 의 100+ URL → 1.5+ 시간 소요. → mitigation: `GITHUB_TOKEN` 사용 (TASK-V0738).
4. **false-positive 가능**: GitHub 의 *temporarily 5xx* (load balancer) 가 stale URL 로 misclassify. → mitigation: 5xx = *warn* (not error), retry next run.
5. **Redirect 1-hop 한계**: GitHub 의 *short URL* (e.g. `https://git.io/...`) 의 multi-hop redirect 미처리. → mitigation: 1 hop = *best-effort*. multi-hop 은 follow-up.
6. **CLI flag 의 `--online` vs `--v-r10-online` 의 두 이름**: 동일 flag 의 alias. *user confusion* 가능. → mitigation: 동일 flag 의 alias — `--v-r10-online` = `--online`.

### Neutral

- ADR-012 의 online layer 가 *opt-in*. 운영자 manual trigger 시에만 활성.
- 본 ADR 의 채택 (v0.7.36) 시 ADR-010 + ADR-012 가 *layer 1 + layer 2* 의 V-R10 정공법.
- ADR-013 (V-R10 v2 cache) 가 follow-up. ADR-012 의 *전제조건*.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 online row 추가. strict = error, loose = warn
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 7: online layer opt-in CI integration
- [ADR-010 §7](../decisions/adr-010-v-r10-url-validity-lint) Implementation: 6 item 중 1 item (online layer)
- [concepts/v-r10-url-validity-lint.md §3 Online HEAD](../concepts/v-r10-url-validity-lint.md): 8 online check table

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/v-r10-url-validity-lint.md` §3 (Online HEAD) | ✅ done (v0.7.34) | `ai-workflow/wiki/concepts/v-r10-url-validity-lint.md` |
| `workflow_kit/url_validity.py` `check_url_online()` | ✅ done (v0.7.35, 본 ADR PoC) | `workflow_kit/url_validity.py` |
| CLI `--online` + `--timeout` flag | ✅ done (v0.7.35) | `workflow_kit/url_validity.py` |
| 6 online test (200/404/500/timeout/TLS/DNS) | ✅ done (v0.7.35, 12/12 PASS) | `tests/check_wiki_url_validity.py` |
| `GITHUB_TOKEN` integration | ⏳ proposed (TASK-V0738) | `workflow_kit/url_validity.py` |
| `.github/workflows/okf-validate.yml` | ⏳ proposed (TASK-V0738) | `.github/workflows/okf-validate.yml` |
| weekly cron + on-PR trigger | ⏳ proposed (TASK-V0738) | `.github/workflows/okf-validate.yml` |
| ADR-013 (V-R10 v2 cache) | ⏳ proposed (별도 turn) | `decisions/adr-013-v-r10-v2-cache.md` |

## Follow-up Candidates (별도 ADR/turn)

1. **TASK-V0736** (formal): ADR-012 acceptance + online layer 강화 (multi-hop redirect, custom User-Agent per host)
2. **TASK-V0738** (CI integration): `.github/workflows/okf-validate.yml` 작성 + `GITHUB_TOKEN` env var + weekly cron
3. **ADR-013** (proposed): V-R10 v2 cache policy (24h disk cache + exponential backoff)
4. **V-R11** (proposed): body content audit (URL 의 *body* 가 valid HTML, no phishing content)
5. **V-R12** (proposed): GitHub commit-pinned URL (ADR-008 follow-up)
6. **V-R13** (proposed): semantic URL verification (URL 의 *의미* (specific commit, specific line) 가 unchanged)
7. **Rate limit handling** (별도): 5 req/sec token bucket + 100 req/min sliding window

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD 가 본 ADR 와 1:1.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010 §3 Decision 7 + §7 Implementation 1 item.
- [[decisions/adr-013-v-r10-v2-cache]] — V-R10 v2 cache policy. 본 ADR 의 *follow-up*.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL 자동 populate. online layer 가 populate 직후 verify.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-010 §3 Decision 7 + ADR-008 follow-up 3 기반. 8 online check + 5 alternatives + 7 positive / 6 negative / 3 neutral. PoC (check_url_online + 6 test) v0.7.35 와 동시 draft. | Sisyphus (orchestrator) |
