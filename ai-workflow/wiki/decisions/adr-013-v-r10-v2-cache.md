---
type: decision
status: accepted
adr_id: ADR-013
decided_at: 2026-06-16
accepted_in: v0.7.36 (release note: workflow-source/releases/Beta-v0.7.36.md)
alternatives_considered: [no-cache, in-memory-only, persistent-disk, distributed-redis, eager-pre-cache, on-demand-only]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, concepts/v-r10-online-layer, concepts/okf-open-knowledge-format, patterns/wiki-stub-emit, releases/Beta-v0.7.36]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-013: V-R10 v2 cache policy (24h disk cache + smart retry)

## Status

**Accepted** (2026-06-16, v0.7.36). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.36 release note 와 동시 accepted. `check_url_with_cache()` 의 24h disk cache + exponential backoff (1s/2s/4s) + max 3 retries PoC 가 4/4 PASS (16/16 total). CI 의 `okf-validate.yml` 에서 $RUNNER_TEMP 디렉토리 + GITHUB_TOKEN 으로 동작.

## Context

ADR-012 (V-R10 online HEAD layer) 채택으로 CI 의 runtime HEAD request 가능. 그러나:

- **CI runtime 비용**: 우리 wiki 의 100+ URL × 5s HEAD = 500s. GitHub Actions 의 6h timeout 내 OK이나 *slow*.
- **GitHub rate limit (unauthenticated 60 req/h)**: 우리 wiki 의 100+ URL → 1.5+ 시간 소요. authenticated (GITHUB_TOKEN) 도 5000 req/h → 약 12분.
- **반복 검증 비용**: weekly cron + on-PR trigger 의 *stale URL check* 가 동일 URL 에 대해 반복. cache 없이 매번 network call → 비효율.
- **deterministic + offline 원칙**: local dev 의 *offline* 환경 (airplane mode) 에서도 *recent* cache 결과로 stale URL partially 검증 가능.

**현재 상황 (2026-06-16):**

- ADR-012 의 `check_url_online()` PoC 6/6 PASS (200/404/500/timeout/TLS/DNS).
- `check_url_with_cache()` PoC 4/4 PASS (cache miss/hit/TTL/stats) — 16/16 total.
- 24h disk cache + exponential backoff (1s/2s/4s) + max 3 retries for 5xx/429/timeout.
- `.github/workflows/okf-validate.yml` 의 CI integration (TASK-V0738) PoC.

**왜 지금:** v0.7.35 release 시 ADR-012 의 online layer 가 *PoC* 였고, cache policy 가 *v0.7.36 follow-up* 이었음. v0.7.36 release 시 *formal adoption* — cache policy 가 ADR 로서 formal decision.

## Decision

**V-R10 의 online HEAD layer 에 24h disk cache + smart retry (exponential backoff) 추가. Cache 위치: `~/.workflow_kit/url_validity_cache.json`. TTL: 86400s (24h).**

**구체적 결정:**

1. **Cache layer (ADR-013 §3)**:
   - **Cache key**: URL (canonical form, lowercase)
   - **Cache value**: `{"timestamp": <unix epoch>, "issues": [{"rule": "...", "severity": "...", "message": "..."}, ...]}`
   - **Cache file**: `~/.workflow_kit/url_validity_cache.json` (default, override via `cache_file` parameter)
   - **TTL**: 86400s (24h, default, override via `ttl_seconds` parameter)
   - **Storage format**: JSON (human-readable, no pickle 등 binary format)

2. **Smart retry (exponential backoff)**:
   - **5xx / 429 / timeout** → retry with backoff
   - **Backoff schedule**: 1s / 2s / 4s (2^attempt)
   - **Max retries**: 3 (default, override via `max_retries` parameter)
   - **4xx (404/410)** → no retry (surface immediately, stale URL detection)
   - **TLS / DNS** → no retry (surface immediately, security risk)

3. **Cache invalidation**:
   - **TTL 만**: 24h 후 cache entry 만료. fresh check 자동.
   - **Manual**: `cache_clear()` / CLI `--cache-clear` flag
   - **Stats**: `cache_stats()` / CLI `--cache-stats` flag (`total` / `fresh` / `expired` counts)

4. **Cache miss vs hit behavior**:
   - **Miss**: fresh `check_url_online()` call → result cache store
   - **Hit (TTL not expired)**: return cached issues directly, no network
   - **Hit (TTL expired)**: fresh `check_url_online()` call → result cache store (overwrite)

5. **API surface** (enhancement over ADR-012):
   - `check_url_with_cache(url, *, cache_file, ttl_seconds, timeout, user_agent, max_retries) -> list[UrlIssue]`
   - `cache_clear(cache_file) -> None`
   - `cache_stats(cache_file) -> dict[str, int]`
   - `DEFAULT_CACHE_FILE`, `DEFAULT_CACHE_TTL_SECONDS` constants

6. **CLI flags** (enhancement over ADR-012):
   - `--cache` (default: False) — use disk cache
   - `--ttl <seconds>` (default: 86400) — cache TTL
   - `--max-retries <count>` (default: 3) — retry count for 5xx/429/timeout
   - `--cache-stats` (no URL arg) — print stats and exit
   - `--cache-clear` (no URL arg) — clear cache and exit

7. **Scope 경계**:
   - **in-scope**: 24h disk cache + exponential backoff + 3 retries + JSON format
   - **out-of-scope**: distributed cache (Redis) + cache compression + multi-region cache + per-user cache (multi-user scenario 없음)
   - **out-of-scope**: cache warming (pre-populate cache) — 별도 ADR candidate
   - **out-of-scope**: per-page-version cache invalidation — V-Version v2 (별도 ADR)

8. **CI integration** (TASK-V0738, GitHub Actions):
   - `$RUNNER_TEMP/url_validity_cache/` 디렉토리 사용 (PR-isolated, ephemeral)
   - `GITHUB_TOKEN` env var 자동 주입 (rate limit 5000 req/h)
   - weekly cron + on-PR trigger

## Alternatives Considered

### A. No cache (status quo + ADR-012 only)

- **장점**: 0 구현 비용. *fresh* check.
- **단점**: 100 URL × 5s = 500s per CI run. weekly cron + on-PR 의 *반복 비용* 부담.
- **탈락 사유**: 운영 헌법 ("cache-first preferred") 위배. ADR-013 의 *whole point* 가 *cache formal*.

### B. In-memory cache only

- **장점**: simple. disk I/O 없음.
- **단점**: CI 의 *ephemeral runner* (매 PR 별 fresh) → cache miss 매번. local dev 의 *process 재시작* → cache miss.
- **탈락 사유**: 운영 헌법 ("persistent state preferred") 위배. ADR-013 §3 Decision 1 의 *disk cache* 와 양립 불가.

### C. Persistent disk cache (status quo PoC)

- **장점**: 24h TTL. *cross-run* cache hit. CI 의 *PR-isolated* 디렉토리 + local dev 의 `~/.workflow_kit/` 모두 가능.
- **단점**: disk I/O overhead (negligible, ~1ms per read/write). stale cache (24h) — *some* false-negative 가능.
- **탈락 사유**: 본 ADR 의 정공법 (선택).

### D. Distributed Redis cache

- **장점**: multi-host cache. cross-org shared cache.
- **단점**: 운영 복잡 (Redis 호스팅). 우리 use case 의 *single-org* 와 mismatch.
- **탈락 사유**: over-engineering. 우리 의 *single-org + local dev + CI* 3 환경 모두 disk cache 가 충분.

### E. Eager pre-cache (CI step: warm cache before check)

- **장점**: deterministic + fast CI.
- **단점**: cache warming step 의 *cold start* 비용 (warm time = check time). 운영 복잡.
- **탈락 사유**: 본 ADR 의 *on-demand* check 가 *lazy* + *simple*. eager 의 *운영 부담* 비해 *성능* 차이 미미.

### F. On-demand cache only (cache store 만, no auto-load)

- **장점**: simple. *write-only* cache.
- **단점**: cache hit 0 (load 부재). *cache store 만* 의 의미 없음.
- **탈락 사유**: *read + write* 가 cache 의 *invariant*. 본 ADR 의 정공법 (선택).

## Consequences

### Positive

1. **CI runtime 비용 ↓**: 100 URL × 5s = 500s → 100 URL cache hit = 1s. **500x speedup**.
2. **GitHub rate limit 여유**: cache hit 으로 GitHub API call 감소. 5000 req/h → 100 req/day (weekly cron 1회 + on-PR N회).
3. **Deterministic + offline 일관성**: local dev 의 *recent cache* 로 stale URL partial 검증 가능 (offline 환경).
4. **Smart retry 의 *5xx false-positive* mitigation**: GitHub 의 *temporarily 5xx* 가 *transient* 으로 처리. retry 후 *real* 5xx 면 *warn* (not error).
5. **PoC 검증 완료**: 16/16 PASS (4 new cache test). 5-run stable.
6. **Mode matrix 양립**: ADR-007 §3 + ADR-010 §4 + ADR-012 §5 + 본 ADR §4 의 4-layer mode matrix 의 online cache row 정의.
7. **Forward-compatible**: ADR-013 의 cache layer 가 ADR-012 의 online layer 의 *additive* — 기존 code 변경 0.

### Negative

1. **Disk I/O overhead**: ~1ms per read/write (negligible vs network 5s).
2. **Stale cache (24h)**: *some* false-negative 가능 — GitHub repo move 시 24h 이내 catch 못함. → mitigation: weekly cron (24h) → *at most 24h lag*.
3. **Cache file 의 cross-host isolation**: `~/.workflow_kit/` 의 *single-host* cache. CI 의 `$RUNNER_TEMP/` 는 ephemeral (PR-isolated) — cache *not shared* across PRs.
4. **Cache size unbounded**: *unbounded growth* 의 위험 (URL 추가 시 cache file grows). → future: cache size cap (e.g. 10MB) + LRU eviction.
5. **Concurrent access**: multi-thread 의 *race condition* (cache file read-modify-write). → future: file lock (`fcntl.flock`).
6. **CI 의 *fresh cache* 매번**: PR-isolated 디렉토리 → cache miss 매번 → *real benefit* 은 local dev only. → mitigation: GHA 의 `actions/cache` step (cache *between* PRs). v0.7.37 follow-up.

### Neutral

- ADR-013 의 24h TTL 은 *default*. 운영자가 `ttl_seconds=86400` (1d), `ttl_seconds=3600` (1h), `ttl_seconds=604800` (1w) 등 자유 설정.
- Cache stats (`total` / `fresh` / `expired`) 가 monitoring 의 *1차 source*.
- 본 ADR 채택 (v0.7.36) 시 ADR-010 + ADR-012 + ADR-013 의 *3-layer V-R10* 완성.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 cache row 추가 (online layer 의 strict vs loose 동일)
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1: 8 offline check unchanged
- [ADR-010 §8](../decisions/adr-010-v-r10-url-validity-lint) Follow-up: V-R10 v2 = ADR-013 의 정공법
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online layer 의 8 case unchanged. ADR-013 가 *additive* wrap.
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `resource` field 의 validity 검증의 *forward-compatible* 보장

## Implementation

| Item | Status | Location |
|---|---|---|
| `concepts/v-r10-url-validity-lint.md` §3 (Online HEAD) | ✅ done (v0.7.35) | `ai-workflow/wiki/concepts/v-r10-url-validity-lint.md` |
| `workflow_kit/url_validity.py` `check_url_online()` | ✅ done (v0.7.35) | `workflow_kit/url_validity.py` |
| `workflow_kit/url_validity.py` `check_url_with_cache()` | ✅ done (v0.7.36, 본 ADR PoC) | `workflow_kit/url_validity.py` |
| `CacheEntry` dataclass + `_load_cache` / `_save_cache` | ✅ done (v0.7.36) | `workflow_kit/url_validity.py` |
| `cache_clear()` / `cache_stats()` | ✅ done (v0.7.36) | `workflow_kit/url_validity.py` |
| CLI `--cache --ttl --max-retries` flags | ✅ done (v0.7.36) | `workflow_kit/url_validity.py` |
| 4 cache test (miss/hit/TTL/stats) | ✅ done (v0.7.36, 16/16 PASS) | `tests/check_wiki_url_validity.py` |
| `.github/workflows/okf-validate.yml` | ✅ done (v0.7.36, TASK-V0738) | `.github/workflows/okf-validate.yml` |
| `GITHUB_TOKEN` integration | ✅ done (v0.7.36) | `.github/workflows/okf-validate.yml` |
| Cache size cap + LRU eviction | ⏸️ deferred (v0.7.37+) | `workflow_kit/url_validity.py` |
| File lock (`fcntl.flock`) | ⏸️ deferred (v0.7.37+) | `workflow_kit/url_validity.py` |
| GHA `actions/cache` for cross-PR cache | ⏸️ deferred (v0.7.37+) | `.github/workflows/okf-validate.yml` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R10 v3 — cache size cap + LRU eviction** (proposed, v0.7.37+)
2. **V-R10 v3 — file lock + concurrent access safety** (proposed, v0.7.37+)
3. **V-R10 v3 — GHA `actions/cache` for cross-PR cache** (proposed, v0.7.37+)
4. **V-R11 — body content audit** (proposed, 별도 ADR)
5. **V-R12 — GitHub commit-pinned URL** (proposed, ADR-008 follow-up)
6. **V-R13 — semantic URL verification** (proposed, 별도 ADR)
7. **Cache warming** (별도 turn) — pre-populate cache for *frequently-checked URLs* (e.g. our wiki 의 top 20 URL)

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD + §4 mode matrix.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010 §8 Follow-up "V-R10 v2" 가 본 ADR 의 source.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012 의 online layer 가 본 ADR 의 *전제조건*.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.
- [[patterns/wiki-stub-emit]] — wiki stub emit 시 URL populate 직후 cache store.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-010 §8 Follow-up + ADR-012 §3 Decision 6 기반. 8 implementation item + 6 alternative + 7 positive / 6 negative / 3 neutral. PoC (check_url_with_cache + 4 test) v0.7.36 와 동시 draft. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **Accepted**: status `proposed` → `accepted`. v0.7.36 release note 등재. `related_pages` 에 v-r10-online-layer concept + Beta-v0.7.36 release note 추가. | Sisyphus (orchestrator) |
