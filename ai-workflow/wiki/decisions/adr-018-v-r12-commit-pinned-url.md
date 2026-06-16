---
type: decision
status: proposed
adr_id: ADR-018
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.37+ candidate)
alternatives_considered: [default-branch-only, ref-pinned-only, commit-pinned-only, commit-pinned-default, archive-org-snapshot, integrity-hash]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-008-in-repo-path-to-url, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-013-v-r10-v2-cache, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-018: V-R12 commit-pinned URL (path_resolver + commit_sha)

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-008 §8 Follow-up "V-R12 — GitHub commit-pinned URL" + ADR-012 §8 Follow-up "V-R12" 기반. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.37 PATCH release note 에 등재.

## Context

ADR-008 (in-repo path → URL) 가 *default branch* (`main`) 기반 URL emit. 그러나:

- **URL drift over time**: `main` branch 의 *default content* 가 merge/rebase 로 변경 가능. *URL 의 의미* (어떤 commit 의 *어떤 file*) 가 *시간 의존*.
- **Provenance 미보존**: 우리 wiki 가 link → *어떤 commit* 의 *어떤 file* 인지 *not traceable*. *audit trail* 부재.
- **Forward-compatible ADR-013 cache 의 stale 위험**: cache 가 *default branch* URL 의 *content* 를 cache → *stale* 시 *not detected* (URL 자체는 unchanged).
- **operational reproducibility**: 같은 wiki page 의 *same content* 가 *time-dependent*. 운영자 *reproduce* 어려움.

**현재 상황 (2026-06-16):**

- ADR-008 의 `resolve_in_repo_path_to_url` 이 *default branch* 만 emit. `blob/main/...` 형식.
- 우리 wiki 의 5 page PoC sample (`docs/samples/okf-bundle-2026-06-16/`) 의 *resource* URL 이 `blob/main/...` — *time-dependent*.
- 운영자 *reproduce* 시 *different content* 가능 (e.g. ADR 추가 후 wiki 가 *changed*).

**왜 지금:** v0.7.37 release 시 path_resolver 의 *formal enhancement* — commit-pinned URL. ADR-008 §8 Follow-up 의 5번 항목.

## Decision

**`path_resolver.py` 에 `resolve_in_repo_path_to_url_pinned(relative_path, repo_root, *, commit_sha, ref)` function 추가. commit_sha 또는 ref 명시 시 *immutable* URL emit. 양쪽 모두 부재 시 `None` (caller 의 *explicit* 요구).**

**구체적 결정:**

1. **API surface** (enhancement over ADR-008):
   - `resolve_in_repo_path_to_url_pinned(relative_path, repo_root, *, commit_sha=None, ref=None) -> str | None`
   - 1 kwarg 만 제공 시 해당 format:
     - `commit_sha=...` → `/blob/<sha>/<path>` (immutable)
     - `ref=...` → `/blob/<ref>/<path>` (mutable but explicit)
   - 양쪽 부재 시 `None` (caller 의 *explicit* 요구)
   - 양쪽 모두 제공 시 commit_sha 우선 (immutable > mutable)

2. **Validation**:
   - `commit_sha`: 7-40 hex chars (short SHA 7+, full SHA 40)
   - `ref`: branch/tag name (no slashes, no special chars `?&\\`)
   - `relative_path`: 기존 `_is_path_safe` check (ADR-008)
   - *validation 실패* 시 `None` return (silent)

3. **CLI** (enhancement over ADR-008):
   - `python -m workflow_kit.path_resolver <path> --commit <sha>` → commit-pinned URL
   - `python -m workflow_kit.path_resolver <path> --ref <ref>` → ref-pinned URL
   - default (no flag) → default branch URL (기존 ADR-008 behavior)

4. **OKF integration** (enhancement over ADR-006):
   - `okf_export.py` 의 `_derive_resource(last_ingested_from, *, repo_root, resolve=True)` 에 `commit_sha` parameter 추가
   - `last_ingested_from` 가 *in-repo path* + `commit_sha` 명시 시 commit-pinned URL emit
   - 운영자가 wiki 의 `vcs_commit: <sha>` field 명시 가능 (extra frontmatter key)

5. **Mode matrix (변경 없음)**: V-R10/V-R11 의 mode matrix 의 한 row. ADR-018 은 *additive* — mode 변경 없음.

6. **Scope 경계**:
   - **in-scope**: commit-pinned + ref-pinned URL format + SHA/ref validation
   - **out-of-scope**: integrity hash (e.g. SHA256 of file content) — 별도 ADR (V-R13 semantic URL verification)
   - **out-of-scope**: archive.org snapshot — external service
   - **out-of-scope**: branch protection policy verification — GitHub API required

7. **운영자 UX**:
   - commit-pinned URL click → *exact* content at that SHA. *no drift*.
   - `git rev-parse HEAD` 로 현재 commit SHA 확인 가능
   - CI 의 *release pipeline* 에서 `--commit $GITHUB_SHA` 자동 inject

## Alternatives Considered

### A. Default branch only (status quo + ADR-008)

- **장점**: 0 구현 비용. *simple*.
- **단점**: *URL drift* 가능. *time-dependent* content. *audit trail* 부재.
- **탈락 사유**: 운영 헌법 ("provenance > simplicity") 위배. ADR-018 의 *whole point* 가 *immutable* URL.

### B. Ref-pinned only (e.g. branch/tag)

- **장점**: *explicit* version. tag 가 *immutable* (e.g. `v0.7.37`).
- **단점**: branch 는 *mutable* (force-push). tag 만 보장. *granular* (e.g. *between v0.7.36 and v0.7.37*) 미지원.
- **탈락 사유**: *partial immutable*. 본 ADR 의 *commit SHA* 가 *true immutable*.

### C. Commit-pinned only (status quo PoC)

- **장점**: *true immutable*. *audit trail* 명확.
- **단점**: SHA 의 *human-readability* 낮음. 운영자 manual *lookup* 어려움.
- **탈락 사유**: 본 ADR 의 정공법 (선택). 운영자 manual *lookup* 은 `git log --oneline` 로 가능.

### D. Commit-pinned default (선택 ADR-008 default = commit-pinned)

- **장점**: 모든 URL *immutable*. *audit trail* 항상 보존.
- **단점**: *default branch* URL 의 *human-readability* 사라짐. *operational friction* (모든 export 시 commit 명시 필요).
- **탈락 사유**: *over-engineering*. 운영자 *opt-in* (per page) 이 *sufficient*.

### E. Archive.org snapshot (external service)

- **장점**: *true immutable*. *web archive* = *legal-grade* provenance.
- **단점**: *external service dependency* + *operational complexity* (archive snapshot pipeline).
- **탈락 사유**: *over-engineering*. 우리 의 *~100 URL* use case 에 *over-spec*.

### F. Integrity hash (SHA256 of file content)

- **장점**: *content* 의 *immutable*. SHA256 = *cryptographic* guarantee.
- **단점**: *URL* 에 *hash* 포함 어려움 (e.g. `?hash=sha256:...`). *operational* 부담.
- **탈락 사유**: *out of scope*. 우리 의 *OKF spec* 의 `resource` field 는 *URL* 만 — *hash* field 별도. V-R13 candidate.

## Consequences

### Positive

1. **URL immutability**: commit SHA 로 *exact* content 보존. *time-independent*. *audit trail* 명확.
2. **Reproducibility**: 같은 wiki page 의 *same content* 가 *time-independent*. 운영자 *reproduce* 가능.
3. **Cache friendly**: ADR-013 cache 가 commit-pinned URL emit 시 cache *key* 가 *more specific* → *cache hit* 시 *higher guarantee* of *content match*.
4. **operational integrity**: *forward-compatible* with *integrity hash* (V-R13 candidate). commit SHA = *content* 의 *version* marker.
5. **No extra dep**: Python stdlib only (subprocess for git SHA detect, string formatting).
6. **CLI flag surface**: `--commit` / `--ref` 의 *explicit* control. 운영자 *tune* 가능.
7. **Forward-compatible**: ADR-008 (default branch) + ADR-018 (commit-pinned) 의 *2-layer* URL format. 운영자 *choose*.
8. **PoC 검증 완료**: 3/3 PASS (commit-pinned, ref-pinned, invalid SHA reject). 9/9 total.

### Negative

1. **Human-readability ↓**: commit SHA `abc1234` vs branch `main`. 운영자 manual *lookup* 필요.
2. **CI integration 필요**: 운영자가 `--commit $GITHUB_SHA` 자동 inject 필요. *miss* 시 default branch fallback.
3. **Backwards-compatible 보존**: ADR-008 의 default branch URL *deprecated* 가능 (deprecation warning). 운영자 *migration* 부담.
4. **Content re-upload 시 URL 변경**: wiki 가 *content update* 시 commit SHA 변경 → URL 변경 → *cache invalidate* + *bookmark break*.
5. **Granularity 미지원**: commit SHA 의 *granularity* = 1 commit. *between commit A and B* 의 URL 미지원 (V-R13 semantic verification).
6. **Tag vs branch 의 *immutable* 차이**: branch (force-push 시 mutable) vs tag (immutable). ADR-018 의 *ref* 의 *mutable* 위험.

### Neutral

- ADR-018 의 *commit-pinned* vs ADR-008 의 *default-branch* 의 *trade-off* 는 *provenance vs simplicity*. 운영자 *per-page* 선택.
- *release pipeline* 의 *automatic* commit-pinned (e.g. v0.7.37 release 시 `--commit v0.7.37` tag) → *human-readable* + *immutable* 양립.
- *forward-compatible* with *integrity hash* (V-R13 candidate) — SHA → SHA256 으로 evolution.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R12 row 추가 (strict=error/warn, loose=warn)
- [ADR-008 §3](../decisions/adr-008-in-repo-path-to-url) Decision 1-2: default branch URL unchanged. ADR-018 가 *additive*.
- [ADR-008 §8](../decisions/adr-008-in-repo-path-to-url) Follow-up: "V-R12 — GitHub commit-pinned URL" → 본 ADR 의 정공법
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged. ADR-018 의 commit-pinned URL 이 *cache* 와 *interact*.

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/path_resolver.py` `resolve_in_repo_path_to_url_pinned()` | ✅ done (v0.7.37, 본 ADR PoC) | `workflow_kit/path_resolver.py` |
| `commit_sha` 7-40 hex char validation | ✅ done (v0.7.37) | `workflow_kit/path_resolver.py` |
| `ref` branch/tag name validation | ✅ done (v0.7.37) | `workflow_kit/path_resolver.py` |
| CLI `--commit` + `--ref` flags | ✅ done (v0.7.37) | `workflow_kit/path_resolver.py` |
| 3 commit-pinned test (commit / ref / invalid SHA) | ✅ done (v0.7.37, 9/9 PASS) | `tests/check_path_resolver.py` |
| `okf_export.py` integration (vcs_commit field) | ⏸️ deferred (v0.7.38+) | `workflow_kit/okf_export.py` |
| CI integration (`--commit $GITHUB_SHA`) | ⏸️ deferred (v0.7.38+) | `.github/workflows/okf-validate.yml` |
| Integrity hash (V-R13) | ⏸️ deferred (별도 ADR) | `workflow_kit/path_resolver.py` |
| Tag-based pinning (e.g. `v0.7.37`) | ⏸️ deferred (별도 ADR) | `workflow_kit/path_resolver.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R12 v2 — `okf_export.py` integration** (proposed, v0.7.38+): `vcs_commit` field + auto-inject
2. **V-R12 v2 — CI integration** (proposed, v0.7.38+): `--commit $GITHUB_SHA` 자동 inject
3. **V-R13 — semantic URL verification** (proposed, 별도 turn): integrity hash (SHA256) + branch protection
4. **V-R12 v2 — tag-based pinning** (proposed, v0.7.40+): `v0.7.37` tag 기반 URL
5. **V-R12 v2 — content hash verification** (proposed, v0.7.42+): `?hash=sha256:...` query param
6. **Migrate ADR-008 default to ADR-018** (proposed, v0.8.0+): deprecate default-branch URL

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. ADR-018 의 *complement* (immutable URL).
- [[decisions/adr-008-in-repo-path-to-url]] — ADR-008. 본 ADR 의 *direct parent* (default branch URL).
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. *complementary* (offline + online).
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. *complementary* (cache layer — commit-pinned URL 의 *cache hit* guarantee ↑).
- [[concepts/okf-open-knowledge-format]] — V-R10/V-R12 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL populate 직후 path_resolver.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-008 §8 Follow-up + ADR-012 §8 Follow-up 기반. 6 alternatives + 8 positive / 6 negative / 2 neutral. PoC (resolve_in_repo_path_to_url_pinned + 3 test) v0.7.37 와 동시 draft. | Sisyphus (orchestrator) |
