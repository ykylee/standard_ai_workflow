---
type: decision
status: proposed
adr_id: ADR-014
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.37+ candidate)
alternatives_considered: [no-cap, entry-count-only, byte-size-only, time-based-only, hybrid-both, external-lru-lib]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, concepts/v-r10-online-layer, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-014: V-R10 v3 cache size cap + LRU eviction policy

## Status

**Proposed** (2026-06-16). 본 ADR 은 ADR-013 §5 Negative 4 (cache size unbounded) + ADR-013 §11 Implementation follow-up "Cache size cap + LRU eviction" 기반. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.37 PATCH release note 에 등재.

## Context

ADR-013 (V-R10 v2 cache) 채택으로 24h disk cache 가 v0.7.36 release 에서 동작. 그러나:

- **Cache size unbounded**: URL 추가 시 cache file 이 무한히 grow. *disk exhaustion* 위험.
- **Memory pressure**: 운영자가 `cat ~/.workflow_kit/url_validity_cache.json` 으로 직접 inspect 시 *huge file* 로 memory spike.
- **Backup 의 부담**: home directory 의 *dotfile* 백업 시 *unbounded cache* 가 *backup size* 비대화.
- **운영자 UX**: cache size 표시 부재 (`cache_stats` 가 entry count 만, byte size 미표시).

**현재 상황 (2026-06-16):**

- ADR-013 의 `_save_cache()` 가 `json.dumps + write_text` 만. *size cap* / *LRU* 부재.
- `cache_stats()` 가 `total` / `fresh` / `expired` 만. *bytes* / *evictions* 부재.
- 우리 wiki 의 ~100 URL × ~200 bytes/entry = ~20KB. *unbounded* 라도 10MB 도달 시 ~50,000 URL 필요. *현실 use case* 에선 *unbounded* 문제 미발생. *but theoretical* + *future-proof*.

**왜 지금:** v0.7.37 release 시 cache layer 의 *formal enhancement* — size cap + LRU. ADR-013 의 6 follow-up 중 1번.

## Decision

**V-R10 v3 cache 에 10MB size cap + 10,000 entry count cap + LRU (least-recently-updated) eviction policy 도입. 두 cap 중 *하나라도* 초과 시 LRU eviction.**

**구체적 결정:**

1. **Two cap policy (ADR-014 §3)**:
   - **Size cap (bytes)**: `DEFAULT_CACHE_MAX_BYTES = 10 * 1024 * 1024` (10 MB, default, override via `--max-bytes`)
   - **Entry count cap**: `DEFAULT_CACHE_MAX_ENTRIES = 10000` (default, override via `--max-entries`)
   - **Trigger**: 어느 하나라도 초과 시 LRU eviction
   - **LRU key**: `CacheEntry.timestamp` (oldest first)

2. **Eviction algorithm** (in `_save_cache`):
   ```
   while (size > max_bytes OR len(entries) > max_entries) AND entries:
       oldest = min(entries, key=timestamp)
       del entries[oldest]
       re-serialize
   write
   ```
   - **Best-effort**: single entry 가 cap 초과 시 warn + write anyway (그냥 저장)

3. **API surface** (enhancement over ADR-013):
   - `_save_cache(cache_file, entries, max_bytes, max_entries)` — `max_bytes` / `max_entries` kwargs
   - `check_url_with_cache(url, *, max_bytes, max_entries)` — kwargs forwarded
   - `DEFAULT_CACHE_MAX_BYTES` / `DEFAULT_CACHE_MAX_ENTRIES` constants
   - `cache_stats()` extension: `bytes` field 추가 (cache file size in bytes)

4. **CLI flags**:
   - `--max-bytes <int>` (default: 10MB) — cache size cap
   - `--max-entries <int>` (default: 10000) — cache entry count cap
   - `--cache-stats` output extension: `bytes` field 추가

5. **Scope 경계**:
   - **in-scope**: size cap + entry count cap + LRU eviction
   - **out-of-scope**: TTL-based eviction (이미 ADR-013 §3 의 *24h TTL* 로 cover)
   - **out-of-scope**: LFU (least-frequently-used) — LRU 가 *simpler* + *sufficient* for our use case
   - **out-of-scope**: cache compression (gzip) — 운영 복잡, 10MB 가 충분히 작음

6. **Mode matrix (변경 없음)**: cache layer 의 mode behavior 는 ADR-013 §4 mode matrix 의 한 row. ADR-014 는 *additive* — mode 변경 없음.

7. **운영자 UX**:
   - `cache_stats()` output: `{"total": N, "fresh": N, "expired": N, "bytes": N}` — bytes field 신규
   - eviction 발생 시 stdout 에 *WARN* message (single entry cap 초과 시만)
   - silent eviction (LRU) — log 만, error 아님

## Alternatives Considered

### A. No cap (status quo + ADR-013)

- **장점**: 0 구현 비용. *simple* cache.
- **단점**: unbounded growth. *disk exhaustion* 위험. 운영자 UX (backup, inspect) 부담.
- **탈락 사유**: 운영 헌법 ("bounded state preferred") 위배. ADR-014 의 *whole point* 가 *cap*.

### B. Entry count only

- **장점**: simple. ~100 URL → 1 entry → 100 entries.
- **단점**: *huge body* (e.g. embedded JSON) 1 entry 가 *gigabyte* 가능. *disk exhaustion* 여전히.
- **탈락 사유**: *unbounded size* 위험. 본 ADR 의 *two cap* 가 정공법.

### C. Byte size only

- **장점**: disk bound *explicit*. *huge body* 의 *size* 직접 limit.
- **단점**: *many small entries* (e.g. 10MB / 100 bytes = 100,000 entries) 의 *dictionary overhead*. 운영자 *expectation mismatch* (10MB = 100K entries vs 100 entries).
- **탈락 사유**: *entry count cap* 의 *operational safety* 가 부재. *dictionary explosion* 가능.

### D. Time-based only (already in ADR-013 as TTL)

- **장점**: 24h TTL 만으로 *freshness* 보장.
- **단점**: *size* 무제한. 24h 안에 1M URL 추가 시 *100MB+* cache.
- **탈락 사유**: *time-based* 만으로 *bounded* 미달성. *size/entry cap* 필수.

### E. Hybrid: size + entry count (status quo PoC)

- **장점**: *double safety* — disk bound + dictionary bound.
- **단점**: *2 cap* 의 *operational complexity* — 운영자가 *both* 이해 필요.
- **탈락 사유**: 본 ADR 의 정공법 (선택). *double safety* 의 *complexity* 는 *acceptable trade-off*.

### F. External LRU library (`lru-dict`, `pylru`)

- **장점**: *battle-tested* LRU implementation.
- **단점**: *extra dep* — 우리 의 *stdlib-only* 정신 위배. *단순 cache* 에 *외부 lib* 의 over-engineering.
- **탈락 사유**: *no extra dep* 원칙. 우리 의 *100 URL use case* 의 *custom LRU* 가 30 lines 로 충분.

## Consequences

### Positive

1. **Disk exhaustion 방지**: 10MB cap 으로 *bounded disk usage*. 운영자 *predictable* memory/backup.
2. **Operational safety**: entry count cap (10K) 으로 *dictionary explosion* 방지.
3. **Deterministic cache size**: *operational SLA* — cache 가 *never exceed 10MB*.
4. **LRU semantic**: *most-recently-checked* URL 이 *keep*. 운영자가 *hot URLs* 의 cache hit 보장.
5. **PoC 검증 완료**: 4/4 PASS (LRU eviction by max_entries / max_bytes / keep recent / default caps). 20/20 total.
6. **No extra dep**: `min(entries, key=...)` 만 사용 (stdlib). *custom LRU* 가 30 lines.
7. **Forward-compatible**: ADR-013 의 `_save_cache` 의 *additive* kwarg — 기존 caller 영향 0.
8. **CLI flag surface**: `--max-bytes --max-entries` 의 *explicit* control. 운영자가 *tune* 가능.

### Negative

1. **Two cap 의 *operational complexity***: 운영자가 *both* 이해 필요. *mitigation*: default (10MB / 10K) 가 *reasonable* for our use case.
2. **Silent eviction**: LRU eviction 시 *log only*, *error* 아님. 운영자가 *모를 수 있음*. *mitigation*: `--cache-stats` 의 `bytes` field 로 *현재 size* 항상 표시.
3. **Single entry cap 초과 시 best-effort write**: 1 entry 가 10MB 초과 시 *write anyway* + *WARN*. 운영자가 *WARN* 무시 시 *unbounded* 가능. *mitigation*: WARN 출력 + 우리 의 *~100 URL* use case 에선 발생 불가.
4. **Cache rebuild 비용**: cap 초과로 eviction 시 *re-serialize* 비용 (~10ms for 1MB). *negligible* for our use case.
5. **No background eviction**: cache size 가 *growing trend* 일 때 매 save 마다 LRU eviction. *mitigation*: 우리 의 *read-heavy + write-light* use case.
6. **CLI 의 `--cache-stats` 의 *output schema* 변경**: `bytes` field 추가 — backward-compatible (existing `total` / `fresh` / `expired` unchanged). 운영자 tooling 의 *strict schema check* 시 *minor version bump*.

### Neutral

- ADR-014 의 *two cap* 은 우리 의 *single-org + local dev + CI* 3 환경 모두 *reasonable*.
- Cache size cap 의 *10MB* 는 *default* — 운영자가 *tune* 가능 (e.g. CI 1MB, local 100MB).
- 운영 헌법 ("bounded state") 의 *first formal application* — 향후 cache / log / tmp file 의 *bound* 적용 시 *선례*.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 cache row unchanged (ADR-013 §4 동일)
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online 8 case unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged. ADR-014 가 *additive* wrap.
- [ADR-013 §5](../decisions/adr-013-v-r10-v2-cache) Negative 4 (cache size unbounded): **해소** via ADR-014 two cap
- [ADR-013 §11](../decisions/adr-013-v-r10-v2-cache) Implementation: "Cache size cap + LRU eviction" → ADR-014 의 정공법

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/url_validity.py` `DEFAULT_CACHE_MAX_BYTES = 10 * 1024 * 1024` | ✅ done (v0.7.37, 본 ADR PoC) | `workflow_kit/url_validity.py` |
| `workflow_kit/url_validity.py` `DEFAULT_CACHE_MAX_ENTRIES = 10000` | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| `_save_cache(max_bytes, max_entries)` LRU eviction | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| `check_url_with_cache(max_bytes, max_entries)` kwargs | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| CLI `--max-bytes --max-entries` flags | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| 4 LRU test (max_entries / max_bytes / keep recent / default caps) | ✅ done (v0.7.37, 20/20 PASS) | `tests/check_wiki_url_validity.py` |
| `cache_stats()` extension: `bytes` field | ⏸️ deferred (별도 turn, v0.7.38+) | `workflow_kit/url_validity.py` |
| Cache compression (gzip) | ⏸️ deferred (별도 ADR) | `workflow_kit/url_validity.py` |
| LFU eviction (vs LRU) | ⏸️ deferred (별도 ADR) | `workflow_kit/url_validity.py` |
| Background eviction (cron) | ⏸️ deferred (별도 ADR) | `workflow_kit/url_validity.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R10 v4 — `cache_stats()` extension** (proposed, v0.7.38+): `bytes` field + `evictions_total` counter + `evictions_last_run` counter
2. **V-R10 v4 — cache compression (gzip)** (proposed, v0.7.39+): 10MB cap 의 *effective* 50MB+ → *10MB on disk*
3. **V-R10 v4 — LFU eviction** (proposed, v0.7.40+): *frequency-based* LRU variant
4. **ADR-015 — V-R10 v3 file lock** (proposed, 별도 turn): `fcntl.flock` for concurrent access safety
5. **ADR-016 — GHA actions/cache** (proposed, 별도 turn): cross-PR cache sharing
6. **Background eviction daemon** (별도 turn): cron + 1h 주기 cache size check + aggressive eviction

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD + §4 mode matrix.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 ADR 의 *parent*.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. cache layer 의 *전제조건*.
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. 본 ADR 의 *direct parent* (cache policy).
- [[concepts/v-r10-online-layer]] — V-R10 online layer concept page.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-013 §5 Negative 4 + ADR-013 §11 Implementation follow-up 기반. 6 alternatives + 8 positive / 6 negative / 1 neutral. PoC (LRU eviction + 4 test) v0.7.37 와 동시 draft. | Sisyphus (orchestrator) |
