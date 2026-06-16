---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: pending_via_adr-020 (proposed, v0.7.39 PoC)
related_pages: [concepts/v-r13-semantic-url-verification, decisions/adr-019-v-r13-semantic-url-verification, decisions/adr-020-v-r13-implementation, decisions/adr-018-v-r12-commit-pinned-url, decisions/adr-010-v-r10-url-validity-lint, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
---

# V-R13 implementation — `check_url_semantic()` PoC (v0.7.39)

## 본 page 의 1차 출처

1. **ADR-019 (V-R13 semantic URL verification, accepted v0.7.38)**: 8 check + 2 layer convention. 본 page 는 ADR-019 의 *convention* 의 *executable implementation* PoC 설명.
2. **ADR-020 (V-R13 implementation, proposed v0.7.39)**: 본 page 와 1:1 매핑. ADR-020 의 *implementation 정공법* 의 *rule* 차원 설명.
3. **OKF spec v0.1** (GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): per-bundle manifest 의 `integrity_hash` field.
4. **V-R10 (URL validity, ADR-010/012/014/015)**: 본 V-R13 의 *prerequisite* (offline 8 check + online 8 case + cache + lock).
5. **V-R11 (body audit, ADR-017)**: 본 V-R13 의 check 3 (content_type) 의 *prerequisite* (V-R11 위임).
6. **V-R12 (commit-pinned URL, ADR-018)**: 본 V-R13 의 layer 0 (path) 의 *prerequisite* (`<sha>` 의 commit SHA pinning).

## §1. ADR-019 convention 의 executable PoC

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-020 (PoC 단계) 와 동시 promote (v0.7.39 PoC, 2026-06-16). 본 concept 의 *PoC implementation* 의 *rule definition* — *convention* 의 *runtime enforcement* 의 *operational 정공법*. |
| 2 | PoC scope | 6 of 8 check 의 executable + 2 of 8 check 의 stub (WARN return). 2 layer (path + `?hash=` + `?range=`) 의 query param parsing. |
| 3 | carrier | per-page `?hash=sha256:...` 의 URL-form emission (V-R12 layer 1) + per-bundle `okf-bundle.yaml` 의 `integrity_hash` 의 manifest-form. |
| 4 | upstream | ADR-019 (convention) + ADR-018 (commit SHA pinning) + ADR-017 (body audit) + ADR-011 (OKF version). |
| 5 | downstream | external OKF bundle consumer 의 *machine-readable verification* 의 *automated enforcement* 차원. |

## §2. 8 semantic check 의 executable status (v0.7.39 PoC)

| # | Check | Status (v0.7.39) | Implementation |
|---|---|---|---|
| 1 | `commit_sha_pinned` | **executable** | parse `https://github.com/<org>/<repo>/blob/<sha>/<path>` 의 `<sha>` (7-40 hex). path_resolver 위임. |
| 2 | `content_hash_pinned` | **executable** | parse `?hash=sha256:<64hex>` 의 query param. SHA256 형식 validate. |
| 3 | `content_type` | **stub (WARN)** | V-R11 위임 (HEAD + Content-Type check). ADR-020 PoC 의 *not-implemented* WARN. |
| 4 | `size_limit` | **executable (opt-in)** | HEAD `Content-Length` ≤ 10MB (configurable). `--perform-head` flag. |
| 5 | `author` | **stub (WARN)** | GitHub API 위임 (commits endpoint, rate-limited). |
| 6 | `last_modified` | **executable (opt-in)** | HEAD `Last-Modified` header. |
| 7 | `freshness` | **executable (opt-in)** | derived: now - last_modified ≤ 7 days (configurable). |
| 8 | `range_valid` | **executable** | parse `?range=<sha1>..<sha2>` 의 query param. 두 SHA 의 7-40 hex + chronological (sha1 < sha2) validate. |

## §3. 2 layer 의 query param parsing

```
URL form:
  https://github.com/<org>/<repo>/blob/<sha>/<path>?hash=sha256:<64hex>&range=<sha1>..<sha2>
```

- **layer 0 (path)**: `<sha>` is the commit SHA from URL path (ADR-018 carrier)
- **layer 1 (query)**: `?hash=sha256:<64hex>` is the byte-level integrity hash
- **layer 2 (query)**: `?range=<sha1>..<sha2>` is the commit range (sha1 < sha2, chronological)

본 PoC 의 parse-only (no fetch):
- `parse_semantic_url(url: str) -> SemanticUrlParts`
- `validate_semantic_url(parts: SemanticUrlParts) -> list[UrlIssue]`
- `check_url_semantic(url: str, *, perform_head: bool = False) -> list[UrlIssue]`

## §4. V-R12 layer 1 의 URL-form carrier

`okf_export.py` 의 per-page `?hash=sha256:...` emission:

- wiki page 의 body bytes (deterministic order) 의 SHA256 → `?hash=sha256:<hex>` 의 query param
- 예: `https://github.com/org/repo/blob/v0.7.38/concepts/v-r13-implementation.md?hash=sha256:abc...`
- layer 1 carrier 의 *machine-readable* verification

본 emission 의 *per-page* 의 *asymmetric* carrier (per-bundle `okf-bundle.yaml` 는 *all-page* aggregate, per-page `?hash=` 는 *single-page* byte-level).

## §5. mode matrix (v0.7.39 PoC)

| mode | 8 check | HEAD | cache | cost |
|---|---|---|---|---|
| **fast** (default) | 1, 2, 8 (parse-only) | no | 0 | low (no network) |
| **medium** | 1, 2, 4, 6, 7, 8 | `--perform-head` | TTL=24h | medium (1 HEAD per URL) |
| **strict** | 1, 2, 3, 4, 5, 6, 7, 8 (3, 5 stub WARN) | yes | TTL=24h | high (HEAD + GitHub API) |

본 PoC (v0.7.39) 의 default = **fast** mode. `--perform-head` flag 로 medium. strict mode 는 v0.7.40+ (check 3, 5 의 executable 후).

## §6. PoC 의 *gradual rollout* 정공법

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.38)** | ADR-019 convention formal acceptance. 8 check + 2 layer 의 *convention* 명시. `okf-bundle.yaml` per-bundle manifest. | v0.7.38 |
| **2 (DONE — v0.7.39 PoC, 본 page)** | `check_url_semantic()` PoC. 6/8 check executable. `parse_semantic_url()` + `validate_semantic_url()`. Per-page `?hash=` emission. | v0.7.39 |
| **3 (v0.7.40+)** | 2/8 check (3, 5) executable. LFU cache. PhishTank feed. SHA256 in URL (layer 1 + layer 2). | v0.7.40+ |
| **4 (v0.7.41+)** | ADR-020 formal acceptance (PoC 운영 evidence 후). | v0.7.41+ |

## §7. PoC 의 *operational rigor*

- 1 신규 module function (`check_url_semantic`) + 1 신규 dataclass (`SemanticUrlParts`) + 2 신규 helper (`parse_semantic_url`, `validate_semantic_url`) + 1 신규 test file (10+ test).
- HEAD request 의 *opt-in* (`--perform-head` flag) — bandwidth 의 *low-friction* 의 *low-friction* 의 *operational* 정공법.
- stub 의 *transparency* — check 3, 5 의 *not-implemented* WARN return (silent fail 의 *anti-pattern* 회피).

## §8. Compliance

- ADR-018 (commit-pinned URL): layer 0 의 `<sha>` 와 정합
- ADR-019 (V-R13 convention): 본 page 는 ADR-019 convention 의 *executable implementation*
- ADR-006 (OKF frontmatter): per-page `?hash=` emission 의 *frontmatter field* 와 정합
- ADR-010 (V-R10 offline): URL form 의 8 check 의 *prerequisite*
- ADR-012 (V-R10 online): HEAD + body 의 *prerequisite* (V-R11 위임)
- ADR-017 (V-R11 body): check 3 (content_type) 의 *prerequisite*
- ADR-011 (OKF version): URL 의 *semantic* 만 검증, OKF spec version 무관

## §9. Follow-up 후보 (v0.7.40+)

1. **v0.7.40**: check 3, 5 의 executable — HEAD + GitHub API (`X-RateLimit-Remaining` aware)
2. **v0.7.40**: `?range=A..B` 의 commit-level diff PoC (`git diff` subprocess)
3. **v0.7.40+**: ADR-021 LFU cache eviction (별도 ADR)
4. **v0.7.40+**: ADR-022 PhishTank feed (V-R11 v2)
5. **v0.7.40+**: SHA256 in URL (V-R12 layer 1 full emission + layer 2 emission)
6. **v0.7.41**: ADR-020 formal acceptance (PoC 운영 evidence 후)

## §10. Related

- [decisions/adr-019-v-r13-semantic-url-verification.md](../decisions/adr-019-v-r13-semantic-url-verification.md) — convention 의 formal acceptance
- [decisions/adr-020-v-r13-implementation.md](../decisions/adr-020-v-r13-implementation.md) — implementation 정공법 (PoC 단계)
- [concepts/v-r13-semantic-url-verification.md](../concepts/v-r13-semantic-url-verification.md) — convention 의 rule definition
- [decisions/adr-018-v-r12-commit-pinned-url.md](../decisions/adr-018-v-r12-commit-pinned-url.md) — layer 0 의 *prerequisite*
- [decisions/adr-017-v-r11-body-audit.md](../decisions/adr-017-v-r11-body-audit.md) — check 3 의 *prerequisite*
- [decisions/adr-010-v-r10-url-validity-lint.md](../decisions/adr-010-v-r10-url-validity-lint.md) — V-R10 offline 의 *prerequisite*

## §11. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-020 (proposed) 와 동시. 8 check 의 PoC status (6 executable + 2 stub) + 2 layer parsing + mode matrix (fast/medium/strict) + gradual rollout (Phase 1-4). 11 section + 1차 출처 6 종 (ADR-018/019/020 + V-R10 + V-R11 + V-R12). | Sisyphus (orchestrator) |
