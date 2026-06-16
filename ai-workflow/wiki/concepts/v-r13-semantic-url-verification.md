---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: verified_via_adr-019 (proposed, v0.7.39+ candidate)
contradiction_flags: []
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-006-okf-compat-frontmatter, decisions/adr-008-in-repo-path-to-url, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-018-v-r12-commit-pinned-url, decisions/adr-019-v-r13-semantic-url-verification, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
---

# V-R13 Semantic URL Verification (ADR-019)

- 문서 목적: V-R10 offline (ADR-010) + V-R10 online (ADR-012) + V-R11 body audit (ADR-017) + V-R12 commit-pinned URL (ADR-018) 의 *semantic* companion. URL 의 *content integrity* + *between-commit content change* verify.
- 범위: 8 semantic check + 2 layer (content hash + commit range) + mode matrix
- 최종 수정일: 2026-06-16

## §0 Status Notice  {#s0-status}

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-019 (proposed, v0.7.39+ candidate) 와 동시 promote. PoC 단계. |
| 2 | rule ID | **V-R13** (Semantic URL verification) |
| 3 | 도입 예정 버전 | v0.7.39 (PATCH, ADR-019 채택 시) |
| 4 | 면제 범위 | 없음 (URL emit 시 default 적용, opt-in flag `--semantic` 로 manual skip) |
| 5 | Lint 심각도 | **mode-conditional** (strict: error for hash/commit/range mismatch / warn for others) + **opt-in** (`--semantic` flag) |
| 6 | 관련 ADR | ADR-010 (offline) + ADR-012 (online, prerequisite) + ADR-013/014/015/016 (cache layer) + ADR-017 (body) + ADR-018 (commit-pinned) + ADR-019 (formal) |
| 7 | Lint 위치 | `workflow-source/workflow_kit/url_validity.py` (PoC, planned) + 5+ new semantic test (planned) |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | Rule ID | **V-R13** |
| 2 | 검증 대상 | URL 의 *semantic* 의미 (commit SHA + content hash + between-commit range) |
| 3 | 2 layer | (a) `?hash=sha256:...` query param (content integrity) + (b) `?range=A..B` query param (between-commit content change) |
| 4 | 8 check | `?hash` presence / hash mismatch / commit mismatch / commit reachability / range changed / orphaned (force-push) / content-type / length-match |
| 5 | Opt-in flag | `--semantic` (default offline only) |
| 6 | CLI flag | `--expected-commit-sha <sha>` / `--expected-content-hash <sha256>` / `--commit-range <A>..<B>` |
| 7 | GitHub API | 2 calls per URL (commit metadata + content). `GITHUB_TOKEN` (5000 req/h) |
| 8 | Lint 심각도 | strict = error (hash/commit/range mismatch) / loose = warn (모두) |

## §2 8 Semantic Check  {#s2-8-check}

| # | Check | Severity (strict) | Severity (loose) | Rule ID |
|---|---|---|---|---|
| 1 | `?hash=sha256:...` query param 존재 | warn (absent) | warn | V-R13-hash-param |
| 2 | content fetch + SHA256 계산 + `?hash` 일치 | **error** (mismatch) | warn | V-R13-hash-mismatch |
| 3 | `vcs_commit` 가 URL 의 commit SHA 와 일치 | **error** (mismatch) | warn | V-R13-commit-mismatch |
| 4 | commit SHA 가 reachable (GitHub API) | **error** (404) | warn | V-R13-commit-404 |
| 5 | commit range (A..B) 의 file content 동일 | **error** (changed) | warn | V-R13-range-changed |
| 6 | branch 가 force-push free (commit SHA 의 *parent* canonical) | **error** (orphaned) | warn | V-R13-orphaned |
| 7 | content type: text/html OR application/json OR text/* (V-R11 reuse) | warn | warn | V-R13-content-type |
| 8 | body length within `?len=<n>` param (if present) | warn | warn | V-R13-length-mismatch |

## §3 Two Layer  {#s3-two-layer}

| Layer | Query param | Purpose | Algorithm |
|---|---|---|---|
| (a) Content hash | `?hash=sha256:<digest>` | *byte-level* content integrity | `GET <url>` → `sha256(body)` → compare with `?hash` |
| (b) Commit range | `?range=<A>..<B>` | *between-commit* content change | `GET <url>` at commit B → `GET <url>` at commit A → diff |

## §4 Mode Matrix (ADR-007 §3 + ADR-019 §5)  {#s4-mode-matrix}

| Layer | strict | loose |
|---|---|---|
| offline 8 check (ADR-010) | error | warn |
| online HEAD (ADR-012) — 404/410/TLS/DNS | **error** | warn |
| body audit (ADR-017) — phishing/TLS | **error** | warn |
| **semantic verify (ADR-019) — hash/commit/range mismatch** | **error** | warn |

## §5 GitHub API Integration  {#s5-github-api}

| API | Use case | Rate limit |
|---|---|---|
| `GET /repos/{owner}/{repo}/commits/{sha}` | commit metadata + reachability | 5000 req/h (authenticated) |
| `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}` | content fetch (SHA256) | 5000 req/h (authenticated) |

우리 의 ~100 URL × 2 API call = ~200 req/cycle. *5000 req/h* 의 4% per CI run. cache (ADR-016) 로 *cross-PR* 절감.

## §6 CLI  {#s6-cli}

```bash
# offline only (default)
python -m workflow_kit.url_validity <url>...

# offline + online + body + semantic
python -m workflow_kit.url_validity <url>... --online --body --semantic

# explicit expected hash + commit + range
python -m workflow_kit.url_validity <url>... --semantic \
  --expected-commit-sha abc1234 \
  --expected-content-hash sha256:... \
  --commit-range v0.7.36..v0.7.37
```

## §7 CI Integration  {#s7-ci}

`.github/workflows/okf-validate.yml` (v0.7.39+ planned) 의 `okf-online-validation` job:

```yaml
- name: V-R10 + V-R11 + V-R13 validation
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    python3 -m workflow_kit.url_validity \
      --mode=strict --online --body --semantic --cache \
      --ttl 86400 --timeout 10 --max-retries 3 \
      <extracted URLs>
```

**Cache strategy (5-layer)**: ADR-013 (24h disk) + ADR-014 (10MB + LRU) + ADR-015 (file lock) + ADR-016 (GHA cross-PR) + ADR-017 (body output cache) + ADR-019 (semantic cache, planned).

## §8 Linter Spec  {#s8-linter}

### §8.1 API

```python
from workflow_kit.url_validity import check_url_semantic

issues = check_url_semantic(
    "https://github.com/foo/bar/blob/abc1234/README.md?hash=sha256:...",
    expected_commit_sha="abc1234",
    expected_content_hash="sha256:...",
    commit_range="v0.7.36..v0.7.37",
    timeout=10.0,
)
```

### §8.2 Test Cases (5+ test, planned)

| # | Test | Expected |
|---|---|---|
| 1 | `test_hash_param_present_pass` | `?hash=sha256:...` + content matches → no issues |
| 2 | `test_hash_mismatch_detected` | `?hash=wrong` + real content → error |
| 3 | `test_commit_sha_mismatch` | `vcs_commit` ≠ URL commit → error |
| 4 | `test_commit_404_handled` | non-existent commit → error (V-R13-commit-404) |
| 5 | `test_range_changed_detected` | between-commit file content changed → error |
| 6 | `test_semantic_opt_in_default_offline` | `--semantic` 미지정 시 *offline only* (V-R13 미수행) |

## §9 Rationale  {#s9-rationale}

### §9.1 Why two-layer (commit + content)?

- **Commit SHA only (V-R12)**: *commit granularity* = 1 commit. *intermediate commit* 변경 시 *immutable URL* 부재. *content drift* 미검출.
- **Content hash only**: *byte-level* 정합성 보장. *between-commit 변경* 시 *URL unchanged* 이지만 *content changed* 가능.
- **Two-layer 합**: commit SHA = *version marker*, content hash = *binary integrity*. *both* 가 보장될 때 *true immutable*.

### §9.2 Why `?hash` query param (not `?v=<n>` versioning)?

- *Standard convention*: GitHub URL 의 *query param* 은 *content 의 *integrity* 의 *stable representation*. *semantic version* (e.g. `?v=2`) 보다 *cryptographic* 으로 *stronger guarantee*.
- *backward-compatible*: 기존 URL 의 *query param 추가* 만 필요. *path* 변경 *0*. *bookmark break* *0*.

### §9.3 Why opt-in (not default)?

- *GitHub API cost*: 2 API call per URL. ~200 req/cycle. CI 의 *default opt-out* 으로 *local dev* 의 *fast* 보장.
- *GHA cache*: *cache hit* 시 *0 API call* — ADR-016 의 *cross-PR cache* 활용.
- *operational* 으로 *semantic verification* 의 *false-positive* (e.g. legitimate typo fix) 시 *override* 가능. *opt-out* 의 *escape hatch* 보존.

## §10 Compliance  {#s10-compliance}

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R13 row 추가
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online HEAD unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged
- [ADR-018 §3](../decisions/adr-018-v-r12-commit-pinned-url) Decision 1-2: commit SHA unchanged. ADR-019 가 *additive*.
- [ADR-019 §3](../decisions/adr-019-v-r13-semantic-url-verification) Decision 1-2: 8 semantic check + 2 layer

## §11 Related  {#s11-related}

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. ADR-019 의 *prerequisite*.
- [[decisions/adr-006-okf-compat-frontmatter]] — ADR-006. `resource` field 의 *integrity* 보장.
- [[decisions/adr-008-in-repo-path-to-url]] — ADR-008. default branch URL. *baseline*.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. V-R10 offline.
- [[decisions/adr-018-v-r12-commit-pinned-url]] — ADR-018. V-R12 commit SHA. *commit* layer.
- [[decisions/adr-019-v-r13-semantic-url-verification]] — ADR-019. 본 page 의 *primary* ADR.
- [[concepts/okf-open-knowledge-format]] — V-R10~V-R13 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 *semantic hash* populate.

## §12 Revision Log  {#s12-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-019 (proposed) 와 동시. 8 semantic check + 2 layer (`?hash` + `?range`) + mode matrix. | Sisyphus (orchestrator) |
