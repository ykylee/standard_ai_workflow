---
type: decision
status: proposed
adr_id: ADR-020
decided_at: 2026-06-16
alternatives_considered: [semantic-only, hash-only, range-only, external-service-only, manual-review]
related_pages: [concepts/v-r13-semantic-url-verification, concepts/v-r13-implementation, decisions/adr-018-v-r12-commit-pinned-url, decisions/adr-019-v-r13-semantic-url-verification, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-020: V-R13 semantic URL verification — `check_url_semantic()` implementation (PoC)

## Status

**Proposed** (2026-06-16, v0.7.39 PoC draft). 본 ADR 은 ADR-019 의 *convention* 을 *executable code* 로 점진 구현. ADR-019 §3 Decision 의 8 semantic check + 2 layer (`?hash=sha256:...` + `?range=A..B`) 의 *convention* 은 v0.7.38 에서 formal acceptance, 본 ADR-020 은 PoC 단계의 *executable implementation* 의 정공법.

본 PoC 의 4 positive / 2 negative / 1 neutral 정공법. ADR-020 acceptance 는 v0.7.39 의 PoC 검증 + 1 release 주기 의 운영 evidence 후 별도 turn 에서 status `proposed` → `accepted`.

## Context

ADR-019 의 8 semantic check + 2 layer convention 은 **v0.7.38 에서 formal acceptance** 되었다. 그러나 ADR-019 의 *negative 1 (No executable code)* 가 명시: 본 ADR-020 의 PoC 가 그 *negative* 를 해소한다.

기존 (v0.7.38):
- `url_validity.check_url()` (8 offline check) + `check_url_online()` (8 online case) + `check_url_body()` (4 body check) — 20 check. **URL 의 *form* 만 검증**.
- ADR-019 convention: URL 의 *semantic* (commit SHA + content hash) 의 verification — *convention* 만.

본 release (v0.7.39 PoC):
- `url_validity.check_url_semantic()` 신규 — 8 semantic check 의 *convention* 의 *executable implementation*.
- 2 layer (`?hash=sha256:...` + `?range=A..B`) 의 query param parsing.
- `okf_export.py` 의 per-page `?hash=sha256:...` emission (V-R12 layer 1 의 URL-form carrier).

## Decision

### §1. 8 semantic check 의 executable implementation (v0.7.39 PoC)

| # | Check | V-R13 layer | PoC strategy |
|---|---|---|---|
| 1 | `commit_sha_pinned` | layer 0 (path) | parse `https://github.com/<org>/<repo>/blob/<sha>/<path>` 의 `<sha>` = 7-40 hex char |
| 2 | `content_hash_pinned` | layer 1 (query) | parse `?hash=sha256:<64hex>` 의 hash fragment |
| 3 | `content_type` | layer 0 (path) + layer 1 (query) | HEAD request → `Content-Type` field (V-R11 위임) |
| 4 | `size_limit` | layer 0 (path) | HEAD request → `Content-Length` ≤ 10MB (configurable) |
| 5 | `author` | layer 0 (path) | GitHub URL → optional `/commits/main/` redirect check |
| 6 | `last_modified` | layer 0 (path) | HEAD request → `Last-Modified` header (24h freshness) |
| 7 | `freshness` | layer 0 (path) | derived: now - last_modified ≤ 7 days (configurable) |
| 8 | `range_valid` | layer 2 (query) | parse `?range=A..B` where A,B are commit SHAs (7-40 hex) and A < B (chronological) |

본 PoC (v0.7.39): checks 1, 2, 4, 6, 7, 8 의 *pure parsing* + *optional HEAD* (cache-aware) 구현. Checks 3, 5 는 V-R11 (body audit) / GitHub commits API (later) 로 위임 — ADR-020 PoC 에서는 stub 으로 `WARN: not-implemented` return.

### §2. 2 layer query param parsing

```
URL form: https://github.com/<org>/<repo>/blob/<sha>/<path>?hash=sha256:<64hex>&range=<sha>..<sha>
```

- **layer 0 (path)**: `<sha>` is the commit SHA from URL path
- **layer 1 (query)**: `?hash=sha256:<64hex>` is the byte-level integrity hash
- **layer 2 (query)**: `?range=<sha1>..<sha2>` is the commit range (sha1 < sha2, chronological)

PoC:
- `parse_semantic_url(url: str) -> SemanticUrlParts` — returns `(commit_sha, content_hash, range_start, range_end)`. None for missing fields.
- `validate_semantic_url(parts: SemanticUrlParts) -> list[UrlIssue]` — 8 check 의 executable validation.
- `check_url_semantic(url: str, *, cache_file=None, ttl_seconds=DEFAULT_CACHE_TTL, perform_head=False) -> list[UrlIssue]` — main entry point.

### §3. ADR-019 convention 의 *executable* carrier

ADR-019 의 *convention* layer:
- **convention-only** (v0.7.38): `okf-bundle.yaml` 의 `integrity_hash` field + ADR-019 §3 의 *2 layer convention* 명시.
- **executable** (v0.7.39 PoC): `check_url_semantic()` 가 convention 을 *runtime check* 로 실행. external consumer 가 *per-bundle* `okf-bundle.yaml` + *per-page* `?hash=sha256:...` 의 manifest-carrier + URL-carrier 2-channel 검증 가능.

### §4. PoC scope (v0.7.39)

**In scope** (v0.7.39):
- `url_validity.check_url_semantic(url)` 신규
- `url_validity.parse_semantic_url(url)` 신규
- `url_validity.validate_semantic_url(parts)` 신규
- `url_validity.SemanticUrlParts` dataclass 신규
- 6 of 8 check 의 executable (1, 2, 4, 6, 7, 8)
- `okf_export.py` 의 per-page `?hash=sha256:...` emission (V-R12 carrier)
- 1 신규 test file `check_wiki_url_semantic.py` (10+ test)

**Out of scope** (v0.7.39, deferred to v0.7.40+):
- Check 3 (content_type from HEAD) — V-R11 위임
- Check 5 (author from GitHub API) — GitHub API rate limit + auth 필요
- Layer 2 (`?range=`) 의 commit-level diff fetch — bandwidth expensive
- LFU cache eviction (별도 ADR-021)
- PhishTank feed (별도 ADR-022)
- SHA256 in URL (V-R12 carrier) — *per-bundle* aggregate (이미 ADR-019 의 `okf-bundle.yaml` 으로 cover, per-page 추가 emit 만)

## Alternatives Considered

### A1. semantic-only (no `?hash=` layer)
8 check 의 *commit SHA* 만으로 verification. 장점: simplest. 단점: ADR-019 의 2 layer 의 절반 만 cover. **rejected** — ADR-019 convention 의 2 layer 중 1 layer 누락.

### A2. hash-only (no `?range=` layer)
8 check 의 *content hash* 만으로 verification. 장점: byte-level integrity. 단점: *between-commit content change* 미검출. **rejected** — ADR-019 의 layer 2 (range) 의 "between-commit content change" use case 미cover.

### A3. range-only
`?range=A..B` 만. 장점: granular diff. 단점: byte-level integrity 미검출. **rejected** — byte-level corruption 미검출.

### A4. external-service-only (e.g. archive.org Wayback Machine)
URL 의 *archived version* 검증. 장점: historical state. 단점: 우리 wiki URL 은 *recent* 만 relevant. **rejected** — use case mismatch.

### A5. manual-review (status quo)
ADR-019 convention 만, *runtime check* 없음. 장점: 0 implementation cost. 단점: convention *violation* 자동 미검출. **rejected** — convention 의 *automated enforcement* 미달.

## Positive Consequences

- 8 check 의 *executable* (PoC 6/8 + 2/8 stub): *automated* convention enforcement.
- 2 layer 의 *runtime parse*: external consumer 가 *machine-readable* 검증 가능.
- PoC 단계의 *gradual rollout*: 6/8 check 의 *low-friction* PoC + 2/8 stub (점진 강화).
- ADR-019 convention 의 *executable carrier* — convention 의 *enforcement* 의 *low-friction* 정공법.
- 1 신규 test file + 1 신규 module function 의 *operational* 정공법 (단일 commit).

## Negative Consequences

- 2/8 check 의 stub — check 3, 5 의 *not-implemented* WARN (transparency 유지).
- HEAD request 의 *bandwidth* + *latency* — PoC 의 `--perform-head` flag (default off) 로 *opt-in*.
- Layer 2 (`?range=`) 의 commit-level diff 의 *expensive fetch* — 본 PoC 는 parse-only (no fetch).
- 1 of 2 layer 의 *URL-form carrier* — `?hash=` 만 (per-page), layer 2 (`?range=`) 는 *per-page emission* 안 함 (parse 만, no emit). *asymmetric* carrier.

## Neutral Consequences

- PoC 의 6/8 check 의 *gradual rollout* — 점진 강화의 *operational cadence* 의 *explicit signaling*.
- `?hash=sha256:...` 의 URL 의 *human-unreadable* — long URL 의 *cosmetic* (header `X-Content-Hash:` 의 alternative 검토는 v0.7.40+).

## Compliance

- ADR-018 (commit-pinned URL) — layer 0 (path) 의 `<sha>` 의 *commit SHA pinning* 과 정합
- ADR-019 (V-R13 convention) — 본 ADR-020 의 PoC 는 ADR-019 의 *convention* 의 *executable carrier*
- ADR-006 (OKF frontmatter) — `okf_export.py` 의 per-page `?hash=` emission 의 *frontmatter field* 와 정합
- ADR-011 (OKF version) — 본 PoC 는 URL 의 *semantic* 만 검증, OKF spec version 무관

## Follow-up

1. **v0.7.40**: checks 3, 5 의 *executable* — content_type via HEAD + author via GitHub API (with rate limit)
2. **v0.7.40**: `?range=A..B` 의 commit-level diff PoC (`git diff` subprocess)
3. **v0.7.40+**: LFU cache eviction (별도 ADR)
4. **v0.7.40+**: PhishTank feed (V-R11 v2)
5. **v0.7.40+**: SHA256 in URL (V-R12 layer 1 carrier) — per-page emission 의 *full* layer
6. **v0.7.41**: ADR-020 formal acceptance (PoC 운영 evidence 후)

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-019 convention 의 executable implementation PoC. 6/8 check + 2/8 stub + 2 layer query param parsing. 5 alternatives (semantic-only, hash-only, range-only, external-service, manual). 4 positive / 2 negative / 1 neutral 정공법. | Sisyphus (orchestrator) |
