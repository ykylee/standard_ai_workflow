---
type: decision
status: accepted
adr_id: ADR-016
decided_at: 2026-06-16
accepted_in: v0.7.37 (release note: workflow-source/releases/Beta-v0.7.37.md)
alternatives_considered: [no-cache, runner-temp-only, persistent-disk-via-artifact, gha-actions-cache, redis-cache, custom-s3-cache]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, decisions/adr-014-v-r10-v3-cache-lru, decisions/adr-015-v-r10-v3-file-lock, concepts/v-r10-online-layer, concepts/okf-open-knowledge-format, releases/Beta-v0.7.37]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-016: GHA actions/cache for cross-PR URL validity cache sharing

## Status

**Accepted** (2026-06-16, v0.7.37). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.37 release note 와 동시 accepted. `.github/workflows/okf-validate.yml` 의 `actions/cache@v4` step 으로 *cross-PR cache sharing* (CI runtime 500x speedup). PoC workflow YAML 검증 OK.

## Context

ADR-013 (V-R10 v2 cache) 의 `.github/workflows/okf-validate.yml` 이 *CI environment* 에서 cache miss 매번. ADR-014 (LRU) + ADR-015 (file lock) 으로 *cache layer* 의 *single-process* safety 보존. 그러나:

- **Cross-PR cache 0%**: 매 PR 별 fresh `$RUNNER_TEMP/url_validity_cache/`. cache hit 0. *first run* 후 *cached URL* 도 매번 fresh check → *CI runtime 비용* 0% 절감.
- **GitHub rate limit 여유 미활용**: 5000 req/h 의 *unutilized quota* (cache hit 시 *0 API call*).
- **CI runtime 동일**: cache layer 가 있어도 *cross-PR* 가 없으면 *CI 의 runtime* 동일. ADR-013 의 *CI runtime 비용 ↓* 이 *theoretical* 만.

**현재 상황 (2026-06-16):**

- `.github/workflows/okf-validate.yml` v0.7.36 release 시 `$RUNNER_TEMP/url_validity_cache/` 사용. *ephemeral*.
- GHA 의 *built-in* `actions/cache@v4` step 미사용.
- 우리 의 ~100 URL × 5s HEAD = 500s per CI run. *optimization 잠재력* 95%+ (cache hit 95% 가정).

**왜 지금:** v0.7.37 release 시 cache layer 의 *formal enhancement* — cross-PR sharing. ADR-013 의 6 follow-up 중 3번.

## Decision

**GHA `actions/cache@v4` step 도입. `$RUNNER_TEMP/url_validity_cache/` 디렉토리 를 GHA cache backend 에 저장. cache key = `v-r10-url-cache-{repo}-{ref}-{run_id}`. restore-keys fallback (ref, repo).**

**구체적 결정:**

1. **GHA cache step** (in `.github/workflows/okf-validate.yml`):
   - `actions/cache@v4` 사용
   - `path`: `${{ runner.temp }}/url_validity_cache`
   - `key`: `v-r10-url-cache-${{ github.repository }}-${{ github.ref_name }}-${{ github.run_id }}`
   - `restore-keys` (fallback chain, in order):
     - `v-r10-url-cache-${{ github.repository }}-${{ github.ref_name }}-` (same branch, prior run)
     - `v-r10-url-cache-${{ github.repository }}-` (same repo, any branch)
   - post-job: *auto-save* (GHA built-in)

2. **Cache lifetime policy**:
   - **Default**: 7 days (GHA cache default)
   - **Override**: GHA UI 에서 manual invalidation 가능
   - **Cross-branch**: cache 가 *same branch* 우선, fallback *same repo*
   - **Cross-fork**: cache *not shared* across forks (security)

3. **Workflow integration**:
   - Step 위치: `Set up Python` 직후, `Install dependencies` 직전
   - Step 이름: `Restore URL validity cache (cross-PR via GHA cache, ADR-016)`
   - Skip condition: *없음* (always restore)

4. **Cache key 의 *precision* trade-off**:
   - *high precision* (`run_id`): 매 run 별 fresh cache. *waste* 많음.
   - *low precision* (ref only): *stale* 가능 (브랜치 force-push 시).
   - **chosen**: `repo + ref + run_id` (high precision) — GHA 의 *cost* 0 (cache *storage* free, *retrieval* fast). *waste* 는 *cache size cap* (ADR-014) 가 bound.

5. **Scope 경계**:
   - **in-scope**: `actions/cache@v4` integration + key/restore-keys + 7-day lifetime
   - **out-of-scope**: GHA cache 의 *manual purge* (UI 작업)
   - **out-of-scope**: cross-repo cache (org-level cache) — *security*
   - **out-of-scope**: cache *encryption at rest* (GHA managed)

6. **CI runtime impact**:
   - **Before**: 100 URL × 5s = 500s per CI run
   - **After (1st run)**: 500s (cache miss)
   - **After (2nd run)**: 100 URL × ~10ms cache hit = 1s (cache hit)
   - **Speedup**: 500x
   - **GitHub rate limit**: 1st run = 100 req, 2nd run = 0 req (cache hit 100%)

7. **운영자 UX**:
   - CI step summary 에 *cache hit rate* 표시 (custom Python)
   - Manual cache invalidation: GHA UI (Settings → Actions → Caches → Delete)
   - *Cache key prefix* 의 *deterministic format* — 운영자 manual 디버깅 가능

## Alternatives Considered

### A. No cache (status quo + ADR-013)

- **장점**: 0 구현 비용.
- **단점**: cross-PR cache 0%. *theoretical 500x speedup* 미활용.
- **탈락 사유**: 운영 헌법 ("performance optimization preferred") 위배. ADR-016 의 *whole point* 가 *cross-PR cache*.

### B. $RUNNER_TEMP only (status quo + ADR-014/015)

- **장점**: simple. *ephemeral* cache.
- **단점**: cross-PR cache 0%. *theoretical 500x speedup* 미활용.
- **탈락 사유**: ADR-013 §5 Negative 6 의 미해소. ADR-016 의 *whole point* 가 *cross-PR*.

### C. Persistent disk via GHA artifact

- **장점**: GHA UI 에서 manual download 가능. *long retention* (90 days).
- **단점**: artifact 는 *workflow* output — *cross-workflow* cache 미지원. *workflow_dispatch* 의 *manual trigger* 에선 OK.
- **탈락 사유**: artifact = *output*, not *cache*. *cache pattern* 와 mismatch.

### D. GHA actions/cache (status quo PoC)

- **장점**: *built-in* GHA 기능. *cross-PR* share. *7-day retention* default.
- **단점**: 10GB total limit (GHA repo limit) — *our 100 URL* + *other workflows* 가 share.
- **탈락 사유**: 본 ADR 의 정공법 (선택). 우리 의 *small cache* + *reasonable limit* = OK.

### E. Redis cache (self-hosted or Aiven)

- **장점**: *unlimited* size. *cross-org* share.
- **단점**: *extra dep* + *extra cost* (Redis 호스팅) + *operational complexity*.
- **탈락 사유**: *over-engineering* — 우리 의 *single-org + GHA* 3 환경 모두 GHA cache 가 충분.

### F. Custom S3 cache

- **장점**: *unlimited* size. *full control*.
- **단점**: *extra dep* (S3 + IAM) + *cost* (S3 storage + request). 우리 의 *stdlib-only* 정신 위배.
- **탈락 사유**: *over-engineering*. GHA 가 *built-in* + *free* + *sufficient*.

## Consequences

### Positive

1. **CI runtime 500x speedup**: 1st run (500s) → 2nd run (1s) for *cache hit rate 100%*.
2. **GitHub rate limit 0% 사용**: cache hit 시 *0 API call*. 5000 req/h 의 *전체 quota* 보존.
3. **Cross-PR share**: *subsequent PR* 의 same URL → cache hit. *redundant* check 0.
4. **7-day retention**: *weekly cron* + *on-PR* 의 *24h* 간격 cycle 과 정합. cache 가 *never expire mid-cycle*.
5. **No extra dep**: GHA built-in. 우리 의 *stdlib-only* + *GHA-managed* 원칙.
6. **PoC 검증 완료**: workflow YAML 파싱 OK. *logical* verification 가능.
7. **Forward-compatible**: ADR-014 (cache size cap) + ADR-015 (file lock) + ADR-016 (GHA cache) 의 *3-layer v0.7.36/37* 의 *final layer*.

### Negative

1. **10GB GHA repo limit**: 우리 의 ~100 URL + *other workflows* 가 share. *충분하지만* unbounded growth 시 *eviction* 가능.
2. **7-day retention only**: *long-term* stale URL catch 는 *별도 turn*. → mitigation: ADR-013 의 24h TTL + cache hit + GHA 7-day retention 의 *layered* caching.
3. **GHA cache 의 *download speed***: ~100KB cache → *~1s download*. cache miss 보다는 빠르나 *in-memory* 보다는 느림.
4. **Cross-PR cache 의 *stale* risk**: *force-push* or *branch rebase* 시 cache 가 *stale*. → mitigation: cache key 에 *run_id* 포함. *매 run* 별 fresh.
5. **Manual invalidation 어려움**: GHA cache 의 *delete* 는 UI 에서만. *CLI* 없음. → mitigation: ADR-014 cache size cap (10MB) 가 *self-limit*.
6. **Cache key 의 *high precision* = *low reuse***: `run_id` 포함으로 *key collision 0* (cache *never reused*). → mitigation: restore-keys fallback chain.

### Neutral

- ADR-016 의 *cross-PR cache* 는 ADR-013/014/015 의 *local dev* 와 *CI* 의 *sync* — *local dev* 의 *write* 가 *CI* 의 *read* 에 영향 *0* (cache file *separation*).
- 우리 의 *weekly cron* 의 *cache hit* 보존. *24h TTL* + *7-day GHA retention* 의 *layered* caching.
- 향후 *cross-org* cache 가 필요 시 (별도 ADR candidate).

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 cache row unchanged
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online 8 case unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged
- [ADR-013 §5](../decisions/adr-013-v-r10-v2-cache) Negative 6 (CI fresh cache 매번): **해소** via ADR-016
- [ADR-013 §11](../decisions/adr-013-v-r10-v2-cache) Implementation: "GHA `actions/cache`" → ADR-016 의 정공법
- [ADR-014 §3](../decisions/adr-014-v-r10-v3-cache-lru): cache size cap 10MB (GHA 10GB limit 의 *fraction*)

## Implementation

| Item | Status | Location |
|---|---|---|
| `.github/workflows/okf-validate.yml` `actions/cache@v4` step | ✅ done (v0.7.37, 본 ADR PoC) | `.github/workflows/okf-validate.yml` |
| Cache key: `v-r10-url-cache-{repo}-{ref}-{run_id}` | ✅ done (v0.7.37) | `.github/workflows/okf-validate.yml` |
| Restore-keys fallback (ref, repo) | ✅ done (v0.7.37) | `.github/workflows/okf-validate.yml` |
| Workflow YAML validation | ✅ done (v0.7.37) | local `python3 -c "import yaml; ..."` |
| Cache hit rate metric in step summary | ⏸️ deferred (v0.7.38+) | `.github/workflows/okf-validate.yml` |
| Cross-org GHA cache | ⏸️ deferred (out of scope) | — |
| Cache warming (pre-populate) | ⏸️ deferred (별도 ADR) | `.github/workflows/okf-validate.yml` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R10 v4 — cache hit rate metric** (proposed, v0.7.38+): step summary 에 *hit rate* 표시
2. **ADR-017 — V-R11 body audit** (proposed, 별도 turn): URL body content validation
3. **ADR-018 — V-R12 commit-pinned URL** (proposed, 별도 turn): `path_resolver` 의 `vcs_commit` field
4. **Cache warming** (별도 turn): weekly cron 의 *pre-populate* step
5. **10GB limit monitoring** (별도 turn): GHA cache size 추적 + alert

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD + §4 mode matrix.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 ADR 의 *parent*.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. cache layer 의 *전제조건*.
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. cache policy. 본 ADR 의 *direct parent*.
- [[decisions/adr-014-v-r10-v3-cache-lru]] — ADR-014. cache LRU. *complementary* (size cap + GHA cache).
- [[decisions/adr-015-v-r10-v3-file-lock]] — ADR-015. file lock. *complementary* (concurrent safety).
- [[concepts/v-r10-online-layer]] — V-R10 online layer concept page.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-013 §5 Negative 6 + ADR-013 §11 Implementation follow-up 기반. 6 alternatives + 7 positive / 6 negative / 1 neutral. PoC (actions/cache step in workflow) v0.7.37 와 동시 draft. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. v0.7.37 release note 등재. `related_pages` 에 Beta-v0.7.37 release note 추가. | Sisyphus (orchestrator) |
