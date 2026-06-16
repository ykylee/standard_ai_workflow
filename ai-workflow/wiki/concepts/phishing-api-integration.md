---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: pending_via_adr-023 (proposed, v0.7.42 draft)
related_pages: [decisions/adr-023-phishing-api-integration, decisions/adr-022-phishing-keyword-feed, decisions/adr-017-v-r11-body-audit, concepts/v-r11-body-audit, concepts/phishing-keyword-feed, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
---

# Phishing API integration — V-R11 v3 auto-update + rate-limit aware (ADR-023, v0.7.42 draft)

## 본 page 의 1차 출처

1. **ADR-023 (phishing API integration, proposed v0.7.42)**: 본 page 와 1:1 매핑. *rule definition* + *implementation 정공법*.
2. **ADR-022 (phishing keyword feed, accepted v0.7.41)**: *external feed* 의 *prerequisite* + *auto-update* 의 *follow-up* 의 *operational* 보강.
3. **ADR-017 (V-R11 body audit, accepted v0.7.37)**: phishing keyword 의 *prerequisite*.
4. **V-R10 (URL validity, ADR-010/012/013/014/015)**: cache 의 *prerequisite* layer.
5. **OKF spec v0.1**: external feed 의 *JSONL format* 의 *operational* 의 *low-friction*.
6. **PhishTank public data feed**: https://data.phishtank.com — *primary API source*.
7. **OpenPhish free feed**: https://openphish.com/feed.txt — *secondary API source*.

## §1. ADR-023 의 *rule definition*

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-023 와 동시 (v0.7.42 draft, 2026-06-16). 본 concept 의 *rule definition* — *code-side* (v0.7.43+ 예정) 의 *formal documentation*. |
| 2 | primary source | PhishTank API (`data.phishtank.com/data/<api_key>/online-valid.json`) — free tier, 5 req/hour, *community-driven verified*. |
| 3 | secondary source | OpenPhish API (`openphish.com/feed.txt`) — free, 1 req/hour, *real-time* update. |
| 4 | tertiary source | VirusTotal API (`virustotal.com/api/v3/urls/...`) — commercial, 4 req/min free, *multi-engine high-confidence*. |
| 5 | multi-source federation | 3 source 의 *union + dedup + cross-source verification* (v0.7.45+). |
| 6 | rate-limit aware | `X-RateLimit-Remaining` + `X-RateLimit-Reset` header respect + exponential backoff (1s/2s/4s) on 429. |
| 7 | cache | 24h TTL (ADR-013 re-use) — *operational* 의 *low-friction* 의 *operational* 보강. |

## §2. 3 vendor 의 *operational matrix*

| Vendor | Tier | Rate limit | Format | Update frequency | Cost |
|---|---|---|---|---|---|
| **PhishTank** | free | 5 req/hour | JSON (online-valid.json) | hourly | $0 |
| **PhishTank** | paid | 100 req/hour | JSON | hourly | subscription |
| **OpenPhish** | free | 1 req/hour | text (one URL per line) | real-time | $0 |
| **OpenPhish** | paid | 10 req/hour | text | real-time | subscription |
| **VirusTotal** | free | 4 req/min | JSON (per-URL) | per-URL | $0 |
| **VirusTotal** | paid | 1000 req/min | JSON | per-URL | subscription |

## §3. *Auto-update* 의 *operational cadence*

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.40)** | ADR-022 bundled + manual external feed | v0.7.40 |
| **2 (DONE — v0.7.41)** | ADR-022 formal acceptance + 11 unit tests | v0.7.41 |
| **3 (DONE — v0.7.42, 본 page)** | ADR-023 + concept page (formal documentation, PoC 단계) | v0.7.42 |
| **4 (v0.7.43+)** | PhishTank + OpenPhish API integration (code-side, *free* sources) | v0.7.43+ |
| **5 (v0.7.44+)** | VirusTotal API integration (commercial, *per-URL* check) | v0.7.44+ |
| **6 (v0.7.45+)** | Multi-source federation (3 source union + dedup + cross-source verification) | v0.7.45+ |
| **7 (v0.7.46+)** | ADR-023 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.46+ |

## §4. Rate-limit aware 의 *operational* 정공법

```python
# Pseudo-code (v0.7.43+)
def fetch_with_rate_limit(url: str, max_retries: int = 3) -> dict:
    """Fetch URL with rate-limit awareness + exponential backoff."""
    import requests, time
    for attempt in range(max_retries):
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limited — check headers
            remaining = response.headers.get("X-RateLimit-Remaining", "?")
            reset_at = response.headers.get("X-RateLimit-Reset", "?")
            if remaining == "0":
                wait = int(reset_at) - time.time()
                time.sleep(max(0, wait))
            else:
                time.sleep(2 ** attempt)  # exponential backoff
        else:
            response.raise_for_status()
    raise RuntimeError(f"max retries ({max_retries}) exceeded for {url}")
```

## §5. Multi-source federation 의 *operational* 정공법 (v0.7.45+)

```python
# Pseudo-code (v0.7.45+)
def fetch_federated_phishing_urls() -> list[str]:
    """Fetch + dedup URLs from PhishTank + OpenPhish + VirusTotal."""
    urls: set[str] = set()
    urls.update(fetch_phishtank_feed())        # v0.7.43+
    urls.update(fetch_openphish_feed())         # v0.7.43+
    urls.update(fetch_virustotal_feed())       # v0.7.44+
    return sorted(urls)  # deterministic order
```

- *3 source* 의 *union* 의 *dedup* 의 *operational* 의 *low-friction*.
- *False positive* 의 *cross-source verification* — 2+ source 의 *appearance* 의 *high-confidence*.
- *Cost* 의 *budget* — PhishTank + OpenPhish free, VirusTotal paid (optional).

## §6. *operational rigor*

- *deterministic* sort: `sorted(urls)` for reproducible cache keys.
- *crash-free*: 429 backoff, 5xx retry, network timeout.
- *machine-readable*: JSON / text format 의 *operational* 의 *low-friction* 의 *edit*.
- *secret management*: API key via env var (`PHISHTANK_API_KEY`).
- *audit-friendly*: fetch timestamp + source attribution in cache file.

## §7. Compliance

- ADR-017 (V-R11 body audit) — phishing keyword 의 *prerequisite* + *follow-up* 의 *operational* 보강
- ADR-022 (phishing keyword feed) — *external feed* 의 *prerequisite* + *auto-update* 의 *follow-up*
- ADR-013 (V-R10 v2 cache) — *24h TTL* 의 *cache* 의 *re-use*
- OKF spec v0.1 — *external feed* 의 *JSONL* format 의 *operational* 의 *low-friction*

## §8. Follow-up 후보 (v0.7.43+)

1. **v0.7.43**: PhishTank + OpenPhish API integration (code-side, *free* sources)
2. **v0.7.44**: VirusTotal API integration (commercial, *per-URL* check)
3. **v0.7.45**: Multi-source federation (3 source union + dedup + cross-source verification)
4. **v0.7.46+**: ADR-023 formal acceptance (1 release 주기 의 운영 evidence 후)
5. **v0.7.47+**: *Per-host* 의 *phishing landing page* 의 *operational* 의 *real-time* 의 *low-friction*

## §9. Related

- [decisions/adr-023-phishing-api-integration.md](../decisions/adr-023-phishing-api-integration.md) — 본 concept 의 *formal documentation*
- [decisions/adr-022-phishing-keyword-feed.md](../decisions/adr-022-phishing-keyword-feed.md) — *external feed* 의 *prerequisite*
- [decisions/adr-017-v-r11-body-audit.md](../decisions/adr-017-v-r11-body-audit.md) — V-R11 의 *prerequisite*

## §10. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-023 (proposed) 와 동시. 10 section + 7 primary sources. 3 vendor 의 *operational matrix* + rate-limit aware + multi-source federation (long-term). 7 phase 의 *gradual rollout*. | Sisyphus (orchestrator) |
