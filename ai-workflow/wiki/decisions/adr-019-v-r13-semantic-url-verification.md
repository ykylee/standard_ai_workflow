---
type: decision
status: proposed
adr_id: ADR-019
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.39+ candidate)
alternatives_considered: [no-verification, content-hash-only, git-blame-verify, external-web-archive, manual-review]
related_pages: [concepts/v-r13-semantic-url-verification, decisions/adr-006-okf-compat-frontmatter, decisions/adr-008-in-repo-path-to-url, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-018-v-r12-commit-pinned-url, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-019: V-R13 semantic URL verification (commit SHA + content hash)

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-018 §5 Negative 5 (Granularity 미지원) + ADR-012 §8 Follow-up "V-R13 semantic URL verification" 기반. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.39 PATCH release note 에 등재.

## Context

ADR-018 (V-R12 commit-pinned URL) 의 *commit SHA granularity* 가 1 commit. *between commit A and B* 의 *semantic content* 변경 미검출. 또한:

- **Content hash (SHA256) 부재**: URL 의 *URL form* 만 보장. *body content* (file bytes) 의 *integrity* 미검증.
- **Stale content drift**: commit A 와 commit B 사이 의 *intermediate commit* 의 content 변경 시 *URL unchanged* 이지만 *content changed* 가능.
- **Link-rot resistance 약함**: GitHub 의 *file move* / *branch rename* 시 *content path* 변경 → *commit SHA URL 도 변경* → *bookmark break*.
- **operational reproducibility**: 동일 wiki page 의 *same URL* 이 *time-dependent* (branch force-push) 또는 *content-dependent* (intermediate commit 변경) 가능.

**현재 상황 (2026-06-16):**

- ADR-018 의 `resolve_in_repo_path_to_url_pinned()` 가 *commit SHA* 만 보장. *content integrity* 미보장.
- 우리 의 wiki → wiki 의 100+ URL 중 *semantic content* 변경 시 *detect* 부재.
- *out-of-band* 으로 운영자가 manual compare 가능하나 *automated* 미지원.

**왜 지금:** v0.7.39 release 시 V-R10 v3 follow-up + V-R11 v2 + V-R12 v2 의 *cumulative* enhancement. ADR-019 가 *V-R13 layer* 의 *semantic verification* 정공법.

## Decision

**V-R13 semantic URL verification 도입. 두 layer: (a) `vcs_commit` 의 `?hash=sha256:...` query param (content integrity) + (b) `vcs_commit_range` 의 "A..B" form (between-commit content change detect). opt-in (default offline only).**

**구체적 결정:**

1. **API surface** (new in `workflow_kit/path_resolver.py` + `url_validity.py`):
   - `resolve_in_repo_path_to_url_pinned(relative_path, repo_root, *, commit_sha, ref, content_hash=None, commit_range=None)` — 확장
   - `check_url_semantic(url, *, expected_commit_sha=None, expected_content_hash=None) -> list[UrlIssue]` — 신규
   - 2 layer: (a) `?hash=sha256:...` query param (content integrity), (b) `?range=A..B` query param (between-commit content change)

2. **8 semantic check (ADR-019 §3)**:

| # | Check | Severity (strict) | Severity (loose) | Rule |
|---|---|---|---|---|
| 1 | URL 의 `?hash=sha256:...` query param 존재 | warn (if absent) | warn | V-R13-hash-param |
| 2 | content fetch + SHA256 계산 + `?hash` 와 일치 | error (mismatch) | warn | V-R13-hash-mismatch |
| 3 | `vcs_commit` 가 URL 의 commit SHA 와 일치 (commit SHA pinned URL 의 경우) | error (mismatch) | warn | V-R13-commit-mismatch |
| 4 | commit SHA 가 reachable (GitHub API) | error (404) | warn | V-R13-commit-404 |
| 5 | commit range (A..B) 의 file content 동일 (between commits) | error (changed) | warn | V-R13-range-changed |
| 6 | branch 가 force-push free (commit SHA 의 *parent* 가 canonical) | error (orphaned) | warn | V-R13-orphaned |
| 7 | content type: text/html OR application/json OR text/* (V-R11 reuse) | warn | warn | V-R13-content-type |
| 8 | body length within `?len=<n>` param (if present) | warn | warn | V-R13-length-mismatch |

3. **GitHub API integration**:
   - `GET /repos/{owner}/{repo}/commits/{sha}` — commit metadata (reachability check)
   - `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}` — content fetch (SHA256)
   - `GITHUB_TOKEN` env var 자동 사용 (rate limit 5000 req/h)
   - *no ref to commit conversion* — pinned commit SHA 만 사용 (mutable branch X)

4. **CLI** (enhancement over V-R12):
   - `--semantic` (default offline only)
   - `--expected-commit-sha <sha>` — URL 의 commit SHA 검증
   - `--expected-content-hash <sha256>` — URL 의 content hash 검증
   - `--commit-range <A>..<B>` — between-commit 비교
   - `--semantic-mode=strict|loose` (default strict, ADR-007 mode matrix 통합)

5. **Mode matrix (ADR-007 §3 + ADR-019 §4)**:

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012) — 404/410/TLS/DNS | **error** | warn |
| body audit (ADR-017) — phishing/TLS | **error** | warn |
| **semantic verify (ADR-019) — hash/commit/range mismatch** | **error** | warn |

6. **Scope 경계**:
   - **in-scope**: 8 semantic check + GitHub API integration + `?hash` / `?range` query param parsing
   - **out-of-scope**: git-blame (file author/date verification) — 별도 ADR
   - **out-of-scope**: external web archive (archive.org snapshot) — 별도 ADR
   - **out-of-scope**: full content *semantic* verification (e.g. *title* 일치, *section count* 일치) — 별도 ADR (semantic *content*, not *binary*)

7. **CI integration (TASK-V0738 follow-up)**:
   - `.github/workflows/okf-validate.yml` 의 `--semantic` flag 자동 활성
   - GHA cache (ADR-016) 의 `actions/cache@v4` 활용
   - `GITHUB_TOKEN` (5000 req/h) + 우리 의 ~100 URL → ~1.2% of hourly limit

## Alternatives Considered

### A. No verification (status quo + ADR-018)

- **장점**: 0 구현 비용. *simple*.
- **단점**: content integrity 부재. *intermediate commit* 변경 시 *detect 0*. *link-rot* 미검출.
- **탈락 사유**: 운영 헌법 ("semantic verification > simple") 위배. ADR-019 의 *whole point* 가 *semantic*.

### B. Content hash only (SHA256, no commit SHA)

- **장점**: *simple*. SHA256 mismatch 로 *content drift* detect.
- **단점**: *commit SHA granularity* 미지원. *between-commit* 변경 시 *immutable* URL 부재. *bookmark break* 가능.
- **탈락 사유**: *partial solution*. 본 ADR 의 *two-layer* 가 *comprehensive*.

### C. Git-blame verify (file author/date)

- **장점**: *semantic* + *provenance*. *author* + *date* 의 *semantic* 의미 보존.
- **단점**: *extra dep* (git CLI) + *complex* (commit history walk). *binary content* 아닌 *content change* detect.
- **탈락 사유**: *over-engineering* + *scope creep* — 우리 의 *~100 URL* use case 에 *binary content* 가 *sufficient*.

### D. External web archive (archive.org snapshot)

- **장점**: *true immutable* + *legal-grade* provenance.
- **단점**: *external service dependency* + *operational complexity* (archive snapshot pipeline).
- **탈락 사유**: *over-engineering*. ADR-019 의 *two-layer* 가 *operational sufficient*.

### E. Manual review (운영자 manual compare)

- **장점**: 0 구현 비용. *human judgment*.
- **단점**: *non-automated*. *operational burden*. *not scalable* to ~100 URL.
- **탈락 사유**: 운영 헌법 ("automation > manual") 위배. *scale* 미지원.

## Consequences

### Positive

1. **Content integrity**: SHA256 hash 로 *byte-level* content 보장. *intermediate commit* 변경 시 즉시 detect.
2. **Immutability 강화**: commit SHA + content hash 의 *two-layer* 가 *single-layer* 보다 *stronger guarantee*.
3. **Link-rot resistance**: `?range=A..B` 가 *between-commit content change* detect. *intermediate commit* 의 *file move* / *branch rename* 시 *content preserved* 검증.
4. **operational reproducibility**: *semantic* + *binary* content 모두 보장. 운영자 *reproduce* 가능.
5. **Mode matrix 양립**: ADR-007 §3 + 본 ADR §5 의 *4-layer* mode matrix. *strict* = error (hash/commit/range), *loose* = warn.
6. **No extra dep**: GitHub REST API (public) + urllib. *stdlib-only* + *no extra dep*.
7. **Forward-compatible**: V-R10 (offline) + V-R12 (online) + V-R11 (body) + V-R13 (semantic) 의 *4-layer* 의 *final layer* 완성.

### Negative

1. **GitHub API cost**: ~100 URL × 2 API call (commit metadata + content) = ~200 req/cycle. *5000 req/h* (authenticated) 의 4% per CI run. *cache* (ADR-016) 로 *cross-PR* 절감.
2. **`?hash` query param 비표준**: GitHub blob URL 의 *query param* 미공식. *format drift* 가능. *GitHub 의 향후 변경* 에 *영향* 가능.
3. **False-positive risk**: content 가 *legitimate change* (e.g. typo fix) 시 `?hash` 가 *changed* → 운영자 *override* 필요.
4. **Commit range (A..B) 의 *semantic* 의미**: file content 가 *changed* (e.g. whitespace) 면 `?range=...` 가 *fail*. 운영자 *whitelist* 필요.
5. **Backward-compatible**: ADR-012/018 의 *immutable URL* 보존. 본 ADR 의 *opt-in* 으로 *additional layer*. *migration* 부담 없음.
6. **GitHub API rate limit (unauthenticated 60 req/h)**: local dev 의 *no token* 시 *slow*. *GITHUB_TOKEN* 권장.

### Neutral

- ADR-019 의 *two-layer* (commit + content) 는 *orthogonal* — *commit-only* 또는 *content-only* 선택 가능. *default* = *both*.
- *out-of-scope* (git-blame, archive.org) 는 *future* ADR candidate.
- *operational* 으로 *content change 의 semantic* (e.g. *whitespace*) 미검출. *binary* 만.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R13 row 추가
- [ADR-008 §3](../decisions/adr-008-in-repo-path-to-url) Decision 1-2: default branch URL unchanged
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online HEAD unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged. ADR-019 의 *content hash* 가 *cache* 와 *interact*.
- [ADR-018 §3](../decisions/adr-018-v-r12-commit-pinned-url) Decision 1-2: commit SHA unchanged. ADR-019 의 *two-layer* 가 ADR-018 의 *additive*.
- [ADR-018 §5](../decisions/adr-018-v-r12-commit-pinned-url) Negative 5 (Granularity 미지원): **해소** via `?range=A..B`
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `resource` field 의 *canonical URI + integrity* 보장

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/path_resolver.py` `content_hash` + `commit_range` kwargs | ⏳ proposed (v0.7.39+) | `workflow_kit/path_resolver.py` |
| `workflow_kit/url_validity.py` `check_url_semantic()` | ⏳ proposed | `workflow_kit/url_validity.py` |
| 8 semantic check (hash / commit / range / etc.) | ⏳ proposed | `workflow_kit/url_validity.py` |
| `?hash=sha256:...` + `?range=A..B` query param parsing | ⏳ proposed | `workflow_kit/url_validity.py` |
| GitHub API integration (commit metadata + content) | ⏳ proposed | `workflow_kit/url_validity.py` |
| CLI `--semantic --expected-commit-sha --expected-content-hash --commit-range` flags | ⏳ proposed | `workflow_kit/url_validity.py` |
| `concepts/v-r13-semantic-url-verification.md` (companion concept page) | ⏳ proposed (companion) | `ai-workflow/wiki/concepts/v-r13-semantic-url-verification.md` |
| 5+ semantic test (mocked HTTP) | ⏳ proposed | `tests/check_wiki_url_validity.py` |
| CI integration (`.github/workflows/okf-validate.yml` `--semantic`) | ⏳ proposed | `.github/workflows/okf-validate.yml` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R13 v2 — git-blame verify** (proposed, v0.7.40+): file author/date verification
2. **V-R13 v2 — external web archive** (proposed, v0.7.42+): archive.org snapshot integration
3. **V-R13 v2 — `?range=A..B` semantic interpretation** (proposed, v0.7.41+): whitespace ignore / line-count threshold
4. **V-R14 — full content semantic verification** (proposed, v0.7.43+): title / section count / heading hierarchy
5. **V-R13 v2 — `GITHUB_TOKEN` cache** (proposed, v0.7.40+): token-scoped cache

## Related

- [[concepts/v-r13-semantic-url-verification]] — V-R13 rule definition. §1 TL;DR / §2 8 check / §3 mode matrix.
- [[decisions/adr-006-okf-compat-frontmatter]] — ADR-006. `resource` field 의 *integrity* 보장.
- [[decisions/adr-008-in-repo-path-to-url]] — ADR-008. default branch URL. 본 ADR 의 *immutable URL* 의 *baseline*.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. V-R10 offline. *semantic* 의 *prerequisite*.
- [[decisions/adr-018-v-r12-commit-pinned-url]] — ADR-018. V-R12 commit SHA. 본 ADR 의 *commit* layer.
- [[concepts/okf-open-knowledge-format]] — V-R10~V-R13 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 *semantic hash* populate.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-018 §5 Negative 5 + ADR-012 §8 Follow-up 기반. 5 alternatives + 7 positive / 6 negative / 2 neutral. 8 semantic check + 2 layer (`?hash` + `?range`) 정공법. | Sisyphus (orchestrator) |
