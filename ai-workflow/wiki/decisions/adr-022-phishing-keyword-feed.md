---
type: decision
status: proposed
adr_id: ADR-022
decided_at: 2026-06-16
alternatives_considered: [bundled-only, external-feed, vendor-api, manual-list, no-keyword-check]
related_pages: [concepts/phishing-keyword-feed, decisions/adr-017-v-r11-body-audit, concepts/v-r11-body-audit, decisions/adr-010-v-r10-url-validity-lint, concepts/v-r10-url-validity-lint, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-022: V-R11 phishing keyword feed (external feed + bundled fallback)

## Status

**Proposed** (2026-06-16, v0.7.40 formal ADR). 본 ADR 은 ADR-017 (V-R11 body audit) 의 *phishing keyword source* 의 *follow-up*. v0.7.37 의 *bundled-only* 의 limitation (stale keyword list) 을 *external feed* (PhishTank-style) 으로 보강. v0.7.39 release 시점에 *code-side* 구현 완료 (phishing_keywords module + 11 tests). 본 ADR 은 그 *code-side* 의 *formal documentation* 의 *rule-side*.

본 ADR acceptance 는 v0.7.40 release note + 1 release 주기 의 운영 evidence 후 별도 turn 에서 status `proposed` → `accepted`.

## Context

ADR-017 (v0.7.37, accepted) 의 *bundled-only* 의 *limitation*:
- 8 bundled keyword 의 *stale risk*: phishing pattern 진화 속도가 *bundled release cycle* (1 release / 1-2 weeks) 보다 빠름.
- *Vendor API 의 rate limit* + *cost* 의 *operational* 의 *low-friction* 의 *bundled baseline* 의 *operational* 보강.
- *External JSONL feed* 의 *offline-friendly* 의 *operational* 의 *low-friction* 의 *manual update* 의 *operational* 의 *low-friction* 의 *fallback*.

본 release (v0.7.39 PoC, v0.7.40 formal):
- `phishing_keywords` module 신규 (4.9 KB)
- `BUNDLED_KEYWORDS` (8 baseline extracted from url_validity)
- `load_phishing_keywords(custom, external_feed)` fallback chain (custom > external > bundled, case-insensitive dedup)
- `_load_external_feed()` JSONL parser (malformed lines skipped, missing file = silent fallback)
- `phishing_feed_update_status()` diagnostic
- 11 tests

본 release (v0.7.40 formal):
- 본 ADR formal documentation
- concept page formalization
- 운영 evidence (v0.7.40 의 1 release 주기 = 1 turn) 후 formal acceptance

## Decision

### §1. fallback chain 의 3 layer

```
+---------------------+
|       custom        |   <-- user-provided Iterable (priority 1)
+---------------------+
              |
              v
+---------------------+
|   external_feed     |   <-- JSONL file (Path, priority 2)
+---------------------+
              |
              v
+---------------------+
| BUNDLED_KEYWORDS    |   <-- 8 baseline (priority 3, fallback)
+---------------------+
```

### §2. dedup 의 *operational* 정공법

- case-insensitive (lowercase) dedup
- first-occurrence order preserved
- `custom` 의 keyword 가 `external`/`bundled` 와 중복 시 `custom` 우선 (first-occurrence)
- `external` 의 keyword 가 `bundled` 와 중복 시 `external` 우선

```python
seen: set[str] = set()
out: list[str] = []
for kw in custom or ():
    kw = kw.strip().lower()
    if kw and kw not in seen:
        seen.add(kw)
        out.append(kw)
for kw in _load_external_feed(external_feed) if external_feed else []:
    kw = kw.strip().lower()
    if kw and kw not in seen:
        seen.add(kw)
        out.append(kw)
for kw in BUNDLED_KEYWORDS:
    kw = kw.strip().lower()
    if kw and kw not in seen:
        seen.add(kw)
        out.append(kw)
return tuple(out)
```

### §3. external feed 의 *silent fallback* 정공법

- file not found: 빈 list return → bundled 만 사용
- file read error (OSError): silent → bundled 만 사용
- malformed JSONL line (json.JSONDecodeError): skip (다음 line 진행)
- missing `keyword` field: skip
- empty `keyword` (whitespace only): skip

*operational* 의 *crash-free* 의 *low-friction* — external feed 의 *partial corruption* 의 *operational* 의 *bundled-only* 의 *graceful degradation*.

### §4. *auto-update* 의 *out of scope* (v0.7.40+)

- external feed 의 *auto-download* (e.g. 매일 PhishTank API 에서 pull) 의 *operational* 의 *low-friction* 의 *out of scope*.
- *manual* update (사용자가 file 을 update + bundle 후 commit) 의 *operational* 의 *low-friction* 의 *default*.
- v0.7.41+ ADR-022 follow-up: PhishTank API integration + rate-limit aware.

## Alternatives Considered

### A1. bundled-only (status quo)
v0.7.37 의 8 bundled keyword. 장점: simplest, 0 external dependency. 단점: *stale risk* — phishing pattern 진화 속도가 *bundled release* 보다 빠름. **rejected** — ADR-017 의 *bundled* 의 *limitation* 의 *follow-up* 의 *low-friction* 의 *external feed* 보강.

### A2. external-feed (chosen)
JSONL file. 장점: *manual update* 의 *operational* 의 *low-friction* + *bundled fallback* 의 *operational* 의 *crash-free*. 단점: *manual update* 의 *operational* 의 *frequency* 의 *human* 의 *operational* 의 *low-friction* 의 *friction*. **chosen** — *operational* 의 *low-friction* 의 *manual* 의 *bundled fallback* 의 *low-friction* 의 *composite*.

### A3. vendor-api
PhishTank API / OpenPhish API / VirusTotal API. 장점: *auto-update* 의 *operational* 의 *low-friction* 의 *automatic* 의 *operational* 의 *operational*. 단점: rate limit + auth + cost + network dependency. **rejected** — v0.7.40 의 *operational* 의 *low-friction* 의 *manual* 의 *out of scope* 의 *future* (v0.7.41+).

### A4. manual-list
user 가 list 를 *hardcode* (e.g. `MY_KEYWORDS = ["foo", "bar"]`). 장점: simplest. 단점: *bundled* 의 *version sync* 의 *operational* 의 *manual* 의 *friction*. **rejected** — `custom=` argument 의 *parameter* 의 *low-friction* 의 *simpler*.

### A5. no-keyword-check
phishing keyword check 자체를 제거. 장점: 0 implementation. 단점: V-R11 의 *phishing detection* 의 *core function* 의 *loss*. **rejected** — V-R11 의 *phishing detection* 의 *core* 의 *low-friction* 의 *operational* 보강.

## Positive Consequences

- 1 신규 module (`phishing_keywords`, 4.9 KB) 의 *operational* 의 *low-friction* 의 *extensibility*.
- 3-layer fallback chain (custom > external > bundled) 의 *operational* 의 *priority* 의 *transparent*.
- case-insensitive dedup 의 *operational* 의 *low-friction* 의 *deterministic*.
- silent fallback (missing/malformed file) 의 *operational* 의 *crash-free* 의 *low-friction*.
- 11 tests 의 *operational* 의 *coverage* 의 *operational* 의 *low-friction*.

## Negative Consequences

- *external feed file* 의 *operational* 의 *manual* 의 *update* 의 *human* 의 *operational* 의 *friction* — v0.7.41+ 의 *auto-update* 의 *out of scope*.
- *bundled* 의 *8 baseline* 의 *operational* 의 *stale risk* — *fallback* 의 *operational* 의 *low-friction* 의 *primary* 의 *external* 의 *operational* 의 *low-friction*.
- *case-insensitive* dedup 의 *operational* 의 *display case* 의 *first-occurrence* 의 *original case* 의 *operational* 보존 (e.g. "Verify Your Account" 가 먼저 오면 "verify your account" 으로 lowercased 후 dedup).

## Neutral Consequences

- *module name* `phishing_keywords` (snake_case, no `v_r11_` prefix) — *operational* 의 *low-friction* 의 *simple* 의 *default*.
- *JSONL format* (one keyword per line) — *operational* 의 *machine-readable* 의 *low-friction* 의 *default*.
- *no CLI flag* — Python API 만 (`check_url_body` 의 `phishing_keywords=` parameter, v0.7.41+). *operational* 의 *low-friction* 의 *boring* default.

## Compliance

- ADR-017 (V-R11 body audit) — phishing keyword 의 *prerequisite* + *follow-up* 의 *operational* 보강
- ADR-006 (OKF frontmatter) — `phishing_keywords` 의 *machine-readable* 의 *JSONL* format 의 *operational* 정합
- ADR-008 (in-repo path) — external feed 의 *in-repo* path 의 *operational* 의 *low-friction*
- V-R10 (URL validity) — phishing keyword 의 *URL validity* 의 *prerequisite*

## Follow-up

1. **v0.7.40**: ADR-022 formal acceptance (운영 evidence 후)
2. **v0.7.41+**: PhishTank API integration + rate-limit aware (v0.7.41+)
3. **v0.7.41+**: external feed 의 *auto-update* mechanism (cron + version-pinned)
4. **v0.7.41+**: per-source metric (phishing_detections_custom / external / bundled)
5. **v0.7.42+**: dynamic content audit (Playwright) + phishing detection 의 *real-time* 의 *operational* 보강

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-017 (bundled) 의 *external feed* follow-up. v0.7.39 PoC 의 *formal documentation*. 5 alternatives + 4 positive / 2 negative / 1 neutral. 3-layer fallback chain (custom > external > bundled) + case-insensitive dedup + silent fallback. | Sisyphus (orchestrator) |
