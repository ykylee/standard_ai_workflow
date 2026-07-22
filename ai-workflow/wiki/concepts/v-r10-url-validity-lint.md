---
type: concept
status: draft
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: verified_via_adr-010 (proposed, v0.7.35+ candidate)
contradiction_flags: []
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, decisions/adr-008-in-repo-path-to-url, decisions/adr-010-v-r10-url-validity-lint, concepts/v-t1-title-consistency-lint, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
---

# V-R10 Rule: URL validity (offline 8 check + optional online HEAD)

- 문서 목적: ADR-006 (OKF 5-field bridge) 채택으로 wiki 의 `resource` field 와 `last_ingested_from` URL 이 canonical URI 의미로 emit. ADR-008 (v0.7.34) 의 자동 resolve 가 stale URL 가능. V-R10 lint 가 URL validity 검증 (8 offline + optional online).
- 범위: lint 정의 (offline 8 check + mode matrix) + 6 test + ADR 후보 (ADR-010)
- 최종 수정일: 2026-06-16

## §0 Status Notice  {#s0-status}

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-010 (proposed, v0.7.35+ candidate) 와 동시 promote. 본 release 의 wiki lint suite 에 정식 등록. |
| 2 | rule ID | **V-R10** (URL validity) |
| 3 | 도입 예정 버전 | v0.7.35 (PATCH, ADR-010 채택 시) |
| 4 | 면제 범위 | 없음 (모든 wiki page + 모든 URL) |
| 5 | Lint 심각도 | **mode-conditional** (strict: error / loose: warn) + **layer-conditional** (offline: error, online: opt-in error) |
| 6 | 관련 ADR | ADR-006 (resource field) + ADR-007 (mode matrix) + ADR-008 (URL resolve) + ADR-010 (V-R10 formal) |
| 7 | Lint 위치 | `workflow-source/workflow_kit/url_validity.py` (PoC, 7.7 KB) + `tests/check_wiki_url_validity.py` (5.2 KB, 6 test) |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | Rule ID | **V-R10** |
| 2 | 검증 대상 | wiki frontmatter `resource` / `last_ingested_from` URL + body cross-link URL + OKF bundle URL |
| 3 | 2 layer | (a) offline 8 check (default, no network) + (b) online HEAD (opt-in, `--v-r10-online` flag) |
| 4 | offline 8 check | scheme (https only) / host parseable / no path traversal / no private IP / no localhost / no file:// / no credentials / GitHub URL form |
| 5 | online HEAD | HTTP 200/3xx/4xx/5xx/timeout/TLS error/DNS fail/rate limit |
| 6 | Lint 심각도 | strict = error, loose = warn (ADR-007 §3 mode matrix 통합) |
| 7 | CI integration | GitHub Actions 에서 `--v-r10-online` 자동 활성 + `GITHUB_TOKEN` (rate limit 5000 req/h) |
| 8 | local dev default | online layer opt-out (offline 만 실행) |
| 9 | cache | *out of scope v0.7.35* — follow-up (V-R10 v2) |

## §2 Offline 8 Check  {#s2-offline}

| # | Check | Severity (strict) | Severity (loose) |
|---|---|---|---|
| 1 | **scheme**: `https://` only (no `http://`, `ftp://`, `file://`, `javascript:`) | error | warn |
| 2 | **host parseable**: RFC 3986 compliant, non-empty | error | warn |
| 3 | **path traversal**: `..` segment reject | error | warn |
| 4 | **private IP**: `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`, `fc00::/7` reject | error | warn |
| 5 | **localhost**: `localhost`, `127.0.0.1`, `::1`, `*.local` reject | error | warn |
| 6 | **file scheme**: `file://` reject (no local file refs) | error | warn |
| 7 | **credentials**: `user:pass@host` reject (security) | error | warn |
| 8 | **GitHub URL form**: `/owner/repo` 의 segment 3 = `blob`/`tree`/`raw`/`commits`/`issues`/`pull`/`wiki`/`actions` 중 하나 | warn | warn |

## §3 Online HEAD (Opt-in)  {#s3-online}

`--v-r10-online` flag 명시 시에만 활성. CI 전용.

| # | Check | Behavior |
|---|---|---|
| 1 | HTTP 200 OK | PASS |
| 2 | HTTP 3xx (redirect) | follow 1 hop, recheck |
| 3 | HTTP 404/410 (not found / gone) | FAIL — stale URL |
| 4 | HTTP 5xx (server error) | WARN — transient (retry next run) |
| 5 | Connection timeout (> 10s) | WARN — slow host |
| 6 | TLS error (cert invalid / expired) | FAIL — security risk |
| 7 | DNS resolution failure | FAIL — host does not exist |
| 8 | Rate limit (429) | WARN — back off |

## §4 Mode Matrix (ADR-007 §3)  {#s4-mode-matrix}

| Layer | strict | loose |
|---|---|---|
| offline 8 check | error | warn |
| online HEAD (opt-in) | error (404/410), warn (5xx/timeout) | warn |

## §5 URL Extract Source  {#s5-source}

| Source | Form | Example |
|---|---|---|
| wiki frontmatter `resource` | `https://...` (ADR-006) | `https://github.com/ykylee/.../README.md` |
| wiki frontmatter `last_ingested_from` | URL or in-repo path | `https://...` or `workflow-source/...` |
| wiki body cross-link | `[text](https://...)` | `[GitHub](https://github.com/foo)` |
| OKF bundle frontmatter | `okf_version` 외 | (no URL in v0.1) |
| OKF bundle body | `[text](https://...)` | (OKF spec §5.1 links) |

## §6 Example  {#s6-example}

### §6.1 PASS — clean https URL

```python
issues = check_url("https://github.com/ykylee/standard_ai_workflow/blob/main/README.md")
# All 8 offline check pass (https / github.com / /blob/branch/ form)
```

### §6.2 FAIL — http:// (scheme reject)

```python
issues = check_url("http://example.com/spec.md")
# → [UrlIssue(rule='V-R10-scheme', severity='error',
#             message="scheme 'http' not allowed (only https://)")]
```

### §6.3 FAIL — private IP

```python
issues = check_url("https://192.168.1.1/spec.md")
# → [UrlIssue(rule='V-R10-private-ip', severity='error',
#             message="private/internal IP '192.168.1.1' not allowed")]
```

## §7 Linter Spec  {#s7-linter}

### §7.1 Location

- Module: `workflow-source/workflow_kit/url_validity.py` (PoC, 7.7 KB / ~200 lines)
- Test: `workflow-source/tests/check_wiki_url_validity.py` (5.2 KB, 6 test, 6/6 PASS)

### §7.2 API

```python
from workflow_kit.url_validity import check_url, UrlIssue

issues = check_url("https://example.com/spec.md")
# Returns list[UrlIssue]; empty list = all checks pass
```

### §7.3 CLI

```bash
python -m workflow_kit.url_validity <url>...                    # default strict
python -m workflow_kit.url_validity <url>... --mode=loose        # loose (warn)
# (online layer: --v-r10-online flag — 별도 turn, v0.7.36+)
```

### §7.4 Test Cases (6 test, 6/6 PASS)

| # | Test | Expected |
|---|---|---|
| 1 | `test_url_https_only_accept` | `https://` PASS, `http://` reject (scheme error) |
| 2 | `test_url_scheme_reject` | `ftp://`, `file://`, `javascript:` reject (scheme error) |
| 3 | `test_url_localhost_reject` | `localhost`, `127.0.0.1`, `::1` reject (localhost or private-ip error) |
| 4 | `test_url_private_ip_reject` | `10/8`, `192.168/16`, `172.16/12`, `fc00::/7` reject (private-ip error) |
| 5 | `test_url_credentials_reject` | `user:pass@host` reject (credentials error) |
| 6 | `test_url_path_traversal_reject` | `..` segment reject (traversal error) |

## §8 Rationale  {#s8-rationale}

### §8.1 Why 2 layer (offline + online)?

- **offline**: deterministic, no network, fast. local dev + CI 양립. 8 check 가 80% common case cover.
- **online**: stale URL 의 *진짜* catch. CI 에서만 활성 (cost). 24h cache 는 v0.7.36 follow-up.
- **trade-off**: local dev 의 *offline* 환경에서 stale URL 미검출 가능. → online layer 의 *CI-only* opt-in 으로 mitigation.

### §8.2 Why strict default?

- 우리 wiki 의 운영 헌법 (R-1~R-9) 가 strict governance. URL validity 도 strict default.
- loose mode 는 ADR-007 §3 의 OKF consumer mode (외부 bundle). 우리 wiki 운영은 strict.

### §8.3 Why GitHub URL form (warn only)?

- ADR-008 의 GitHub URL 자동 resolve 가 `/blob/<branch>/<path>` 또는 `/tree/<branch>/<path>` form. 그 외 segment (`/issues/`, `/pull/`, `/wiki/`, `/actions/`) 도 valid GitHub URL 이지만 *content* 가 다름 — warn level.
- strict mode 의 *error* 가 아닌 *warn* — 다른 GitHub URL 도 가능 (의도적 wiki link).

## §9 Compliance  {#s9-compliance}

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-006 §3](../decisions/adr-006-okf-compat-frontmatter) Decision 1: `resource` field 채움. V-R10 가 채워진 URL 의 validity 검증
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 row 추가. strict = error, loose = warn
- [ADR-008 §3](../decisions/adr-008-in-repo-path-to-url) Decision 1-2: in-repo path → GitHub URL. V-R10 가 resolved URL 의 stale URL detect
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `resource` field 의 *canonical URI* semantic 보존

## §10 Related  {#s10-related}

- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 trigger. §12.1 follow-up 3.
- [[decisions/adr-006-okf-compat-frontmatter]] — `resource` field emit. V-R10 검증 대상.
- [[decisions/adr-007-okf-consumer-mode]] — mode matrix 의 V-R10 row 정의.
- [[decisions/adr-008-in-repo-path-to-url]] — in-repo path → URL. V-R10 이 stale URL detect.
- [[decisions/adr-010-v-r10-url-validity-lint]] — V-R10 의 formal adoption.
- [[concepts/v-t1-title-consistency-lint]] — V-T1 (title ↔ H1) 와 V-R10 (URL validity) 는 별개 lint. V-T1 의 URL 검증은 *out of scope*. R-7 (semantic conflict) 와 양립.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL 자동 populate. V-R10 가 populate 직후 verify.

## §11 Revision Log  {#s11-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-010 (proposed) 와 동시. 6 offline test + mode matrix + CLI spec. | Sisyphus (orchestrator) |
