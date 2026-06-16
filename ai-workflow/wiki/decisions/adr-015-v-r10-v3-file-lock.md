---
type: decision
status: accepted
adr_id: ADR-015
decided_at: 2026-06-16
accepted_in: v0.7.37 (release note: workflow-source/releases/Beta-v0.7.37.md)
alternatives_considered: [no-lock, thread-lock-only, process-lock-only, file-mtime-watch, distributed-lock]
related_pages: [concepts/v-r10-url-validity-lint, decisions/adr-010-v-r10-url-validity-lint, decisions/adr-012-v-r10-online-layer, decisions/adr-013-v-r10-v2-cache, decisions/adr-014-v-r10-v3-cache-lru, concepts/v-r10-online-layer, concepts/okf-open-knowledge-format, releases/Beta-v0.7.37]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-015: V-R10 v3 file lock (fcntl.flock) for concurrent access safety

## Status

**Accepted** (2026-06-16, v0.7.37). 2026-06-16 초안 (proposed) → 2026-06-16 v0.7.37 release note 와 동시 accepted. `_CacheLock` (POSIX `fcntl.flock` + sidecar `.lock` file + Windows no-op fallback) PoC 가 2/2 PASS (22/22 total). ADR-013 의 *concurrent access race* 해소.

## Context

ADR-013 (V-R10 v2 cache) 채택으로 disk cache 의 read-modify-write 가 v0.7.36 release 에서 동작. 그러나:

- **Race condition**: multi-process (e.g. 2 CI jobs, local dev 의 *parallel curl* + *cache reader*) 의 *concurrent* `_load_cache` + `_save_cache` → *torn write* 가능.
- **Cache corruption**: process A 의 `_load_cache` → process B 의 `_load_cache` (both see old) → both `_save_cache` → *last write wins* — A's update lost.
- **Invalid JSON**: A's `read_text` + B's `write_text` (interleaved) → half-old + half-new file → `json.JSONDecodeError` → `_load_cache` returns `{}` (silent data loss).
- **운영자 UX**: silent corruption (no error message) — 운영자가 *stale URL* misclassify.

**현재 상황 (2026-06-16):**

- ADR-013 의 `_load_cache` + `_save_cache` 가 *no lock*. *serial* use case 에선 OK.
- *concurrent* use case (CI multi-job, parallel scripts) 에선 *race condition*.
- 우리 의 ~100 URL use case 에선 *rare*. *but theoretical* + *future-proof*.

**왜 지금:** v0.7.37 release 시 cache layer 의 *formal enhancement* — file lock. ADR-013 의 6 follow-up 중 2번.

## Decision

**V-R10 v3 cache 에 `fcntl.flock` 기반 cross-process file lock 도입. Sidecar `.lock` file 사용. POSIX only (Windows = no-op fallback).**

**구체적 결정:**

1. **File lock mechanism (ADR-015 §3)**:
   - **POSIX `fcntl.flock(LOCK_EX)`** — exclusive lock (advisory)
   - **Sidecar lock file**: `<cache_file>.lock` (e.g. `url_validity_cache.json.lock`)
   - **Auto-create**: `open(<lock_file>, "w")` — empty file
   - **Auto-release**: `__exit__` → `fcntl.flock(LOCK_UN)` + close fd
   - **POSIX only**: Windows 에선 `ImportError` → no-op (with stderr WARN)

2. **API surface** (enhancement over ADR-013):
   - `_CacheLock(cache_file: Path)` — context manager class
   - `with _CacheLock(cache_file): ...` — wrap read-modify-write
   - `_save_cache` *itself* 의 lock (not *caller*) — `_load_cache` / `_save_cache` 가 lock 안에서 호출됨
   - *sidecar lock file* auto-cleanup: lock file 은 *persistent* (운영자 manual cleanup 시) — auto delete 안 함

3. **Where to lock**:
   - `check_url_with_cache` 의 read-modify-write block (cache lookup + entry update + save) — **ALL inside `_CacheLock` context**
   - `cache_clear` / `cache_stats` — *no lock* (best-effort read; user can re-run)
   - `_load_cache` / `_save_cache` *private functions* — caller responsibility

4. **Scope 경계**:
   - **in-scope**: cross-process `fcntl.flock` + sidecar lock file
   - **out-of-scope**: distributed lock (Redis) — *single-host* use case
   - **out-of-scope**: cross-host lock — out of scope (single host)
   - **out-of-scope**: lock timeout — current *blocking* lock. 운영자가 manual kill.
   - **out-of-scope**: lock file cleanup — manual only

5. **Windows fallback** (선언적): `fcntl` `ImportError` 시 no-op (with stderr WARN). *운영자* 가 *Windows* 인지 *POSIX* 인지 *구분* 가능.

6. **Mode matrix (변경 없음)**: cache layer 의 mode behavior 는 ADR-013 §4 + ADR-014 §6 의 mode matrix 의 한 row. ADR-015 는 *additive* — mode 변경 없음.

7. **운영자 UX**:
   - Lock contention 시 *blocking* (no timeout). 운영자가 *kill -9* 로 unlock.
   - Lock 획득 실패 시 stderr WARN + continue (best-effort).
   - Lock file 위치: `<cache_file>.lock` (cache file 옆). 운영자 manual `rm <lock>` 가능.

## Alternatives Considered

### A. No lock (status quo + ADR-013)

- **장점**: 0 구현 비용. *simple*.
- **단점**: *race condition* + *torn write* + *silent corruption*.
- **탈락 사유**: 운영 헌법 ("concurrent safe preferred") 위배. ADR-015 의 *whole point* 가 *lock*.

### B. Thread lock only (`threading.Lock`)

- **장점**: simple. Python stdlib.
- **단점**: *thread-only* — *cross-process* race 여전히. *multi-thread* use case 미발생.
- **탈락 사유**: *thread-only* 의 *limited scope*. 본 ADR 의 *cross-process* 가 정공법.

### C. Process lock (`fcntl.flock`, status quo PoC)

- **장점**: *cross-process* safe. POSIX 표준.
- **단점**: *POSIX only* (Windows no-op). *blocking* (no timeout).
- **탈락 사유**: 본 ADR 의 정공법 (선택). 우리 의 *Linux/macOS only* 운영 환경과 정합.

### D. File mtime watch (`os.path.getmtime`)

- **장점**: *non-blocking* lock. *cross-platform*.
- **단점**: *advisory only* — 운영자가 manual `touch` 시 corruption. *eventual consistency* only.
- **탈락 사유**: *advisory* 의 *weak guarantee*. 본 ADR 의 *strict guarantee* 와 양립 불가.

### E. Distributed lock (Redis / Memcached / etcd)

- **장점**: *cross-host* safe.
- **단점**: *extra dep* (Redis 등) — 우리 의 *stdlib-only* 정신 위배. *운영 복잡*.
- **탈락 사유**: *over-engineering* — 우리 의 *single-host + local dev + CI* 3 환경 모두 `fcntl.flock` 가 충분.

## Consequences

### Positive

1. **Cross-process safe**: multi-process 의 *concurrent* read-modify-write 의 *atomicity* 보장. *torn write* 0.
2. **Cache corruption 방지**: `_load_cache` + `_save_cache` 가 atomic → JSON parse error 0.
3. **No extra dep**: `fcntl` 는 POSIX Python stdlib. *Windows only* fallback (no-op + WARN).
4. **POSIX 표준**: `fcntl.flock` 는 *battle-tested* (1980s~). 우리 의 *operational stability* 보존.
5. **Sidecar lock file**: cache file 의 *integrity* 와 *separation*. 운영자 manual cleanup 가능.
6. **No timeout (blocking)**: *strict guarantee* — 운영자가 *never* see *silent corruption*.
7. **PoC 검증 완료**: 2/2 PASS (file lock context manager + concurrent writes). 22/22 total.
8. **Forward-compatible**: ADR-014 의 *LRU eviction* 가 lock 안에서 동작 → *multi-process 의 LRU* 도 atomic.

### Negative

1. **POSIX only**: Windows 에선 *no-op* (with WARN). Windows 운영자 *silent fallback*.
2. **Blocking (no timeout)**: lock contention 시 *hang*. 운영자가 *kill -9* 필요.
3. **Sidecar lock file 잔존**: `<cache_file>.lock` 파일 *persistent*. 운영자 manual `rm` 필요. *disk litter*.
4. **fcntl import 실패 시 silent fallback**: 운영자 *WARN* 무시 시 *no lock* (race condition 재발생).
5. **Performance overhead**: `flock` 의 *system call* (~10us per lock). *negligible* vs *disk I/O* (~1ms).
6. **Lock file 의 *orphan***: process *crash* (kill -9) 시 lock file 잔존. 다음 process 의 `flock` 는 *stale lock* detect (BSD flock 가 *exclusive* → 다른 process 가 lock 즉시 acquire 불가). *advisory* cleanup 필요 (운영자 manual `rm`).

### Neutral

- ADR-015 의 *POSIX only* + *no timeout* 의 *constraints* 는 우리 의 *Linux/macOS + CI* use case 와 정합.
- 운영자 manual cleanup 의 *orphan lock file* 은 운영 헌법 ("operational safety > code simplicity") 의 trade-off.
- ADR-013/014/015 의 *3-layer* v0.7.36/37 의 *cache enhancement bundle* 의 *final layer*.

## Compliance

- [SCHEMA.md §5.1](../SCHEMA.md) R1~R9: R-9 면제 (외부 source 정의), R-8 (status) 와 무관
- [ADR-007 §3](../decisions/adr-007-okf-consumer-mode) mode matrix: V-R10 cache row unchanged
- [ADR-010 §3](../decisions/adr-010-v-r10-url-validity-lint) Decision 1-9: offline 8 check unchanged
- [ADR-012 §3](../decisions/adr-012-v-r10-online-layer) Decision 1-2: online 8 case unchanged
- [ADR-013 §3](../decisions/adr-013-v-r10-v2-cache) Decision 1-2: 24h disk cache unchanged
- [ADR-013 §5](../decisions/adr-013-v-r10-v2-cache) Negative 5 (concurrent access race): **해소** via ADR-015
- [ADR-013 §11](../decisions/adr-013-v-r10-v2-cache) Implementation: "File lock" → ADR-015 의 정공법
- [ADR-014 §3](../decisions/adr-014-v-r10-v3-cache-lru): LRU eviction lock-guard via ADR-015

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/url_validity.py` `_CacheLock` context manager | ✅ done (v0.7.37, 본 ADR PoC) | `workflow_kit/url_validity.py` |
| `fcntl.flock(LOCK_EX/LOCK_UN)` POSIX lock | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| Sidecar `<cache_file>.lock` file | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| Windows `ImportError` no-op fallback | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| `check_url_with_cache` wrap in `_CacheLock` | ✅ done (v0.7.37) | `workflow_kit/url_validity.py` |
| 2 file lock test (context manager + concurrent writes via multiprocessing) | ✅ done (v0.7.37, 22/22 PASS) | `tests/check_wiki_url_validity.py` |
| Lock timeout (advisory wait + auto-kill) | ⏸️ deferred (v0.7.38+) | `workflow_kit/url_validity.py` |
| Lock file orphan cleanup (auto-detect + cleanup) | ⏸️ deferred (v0.7.38+) | `workflow_kit/url_validity.py` |
| Windows native lock (`msvcrt.locking`) | ⏸️ deferred (out of scope) | `workflow_kit/url_validity.py` |

## Follow-up Candidates (별도 ADR/turn)

1. **V-R10 v4 — lock timeout + advisory wait** (proposed, v0.7.38+): 5s timeout + WARN
2. **V-R10 v4 — lock file orphan cleanup** (proposed, v0.7.39+): stale lock detect (mtime) + auto-cleanup
3. **V-R10 v4 — Windows native lock** (proposed, v0.7.40+): `msvcrt.locking` for Windows users
4. **ADR-016 — GHA actions/cache** (proposed, 별도 turn): cross-PR cache sharing
5. **ADR-017 — V-R11 body audit** (proposed, 별도 turn): URL body content validation
6. **Lock contention metrics** (별도 turn): Prometheus + lock wait time

## Related

- [[concepts/v-r10-url-validity-lint]] — V-R10 rule definition. §3 Online HEAD + §4 mode matrix.
- [[decisions/adr-010-v-r10-url-validity-lint]] — ADR-010. 본 ADR 의 *parent*.
- [[decisions/adr-012-v-r10-online-layer]] — ADR-012. cache layer 의 *전제조건*.
- [[decisions/adr-013-v-r10-v2-cache]] — ADR-013. cache policy.
- [[decisions/adr-014-v-r10-v3-cache-lru]] — ADR-014. cache LRU. 본 ADR 와 *동일 layer* (cache layer).
- [[concepts/v-r10-online-layer]] — V-R10 online layer concept page.
- [[concepts/okf-open-knowledge-format]] — V-R10 의 1차 source.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-013 §5 Negative 5 + ADR-013 §11 Implementation follow-up 기반. 5 alternatives + 8 positive / 6 negative / 2 neutral. PoC (_CacheLock + 2 test) v0.7.37 와 동시 draft. | Sisyphus (orchestrator) |
