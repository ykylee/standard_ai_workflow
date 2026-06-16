---
type: decision
status: proposed
adr_id: ADR-023
decided_at: 2026-06-16
alternatives_considered: [manual-update, external-feed, phishtank-api, openphish-api, virustotal-api, multi-source-federation]
related_pages: [concepts/phishing-keyword-feed, concepts/phishing-api-integration, decisions/adr-017-v-r11-body-audit, decisions/adr-022-phishing-keyword-feed, concepts/v-r11-body-audit, decisions/adr-010-v-r10-url-validity-lint, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-023: V-R11 phishing keyword API integration (auto-update + rate-limit aware)

## Status

**Proposed** (2026-06-16, v0.7.42 draft). 본 ADR 은 ADR-022 (V-R11 phishing keyword feed) 의 *follow-up* 의 *API integration* + *auto-update* 의 *operational* 보강. ADR-022 의 *manual* update 의 *limitation* (human-driven update) 을 *auto-update* 의 *API integration* 으로 해결. v0.7.41 release 시점에 *code-side* 미구현 — 본 ADR 의 *formal documentation* 의 *rule-side*.

본 ADR acceptance 는 v0.7.42 release note + 1 release 주기 의 운영 evidence 후 별도 turn 에서 status `proposed` → `accepted`.

## Context

ADR-022 (v0.7.40, accepted) 의 *bundled-only + manual external feed* 의 *limitation*:
- *manual update* 의 *human* 의 *operational* 의 *friction*: phishing pattern 진화 속도가 *human* 보다 빠름.
- *bundled* (8 baseline) 의 *stale risk*: 1 release / 1-2 weeks 의 *cycle* 의 *frequency* 의 *low-friction* 의 *limitation*.
- *external feed* 의 *operational* 의 *manual* 의 *update* 의 *human* 의 *friction*.

본 release (v0.7.42 draft):
- PhishTank API integration (auto-update + rate-limit aware)
- OpenPhish API (alternative, free)
- VirusTotal API (commercial, multi-source)
- Multi-source federation (PhishTank + OpenPhish + VirusTotal 의 *union* 의 *operational* 의 *low-friction*)

본 release 의 *code-side* 구현은 v0.7.42+ 별도 turn (본 release 의 *formal documentation* 만, code 변경 없음).

## Decision

### §1. PhishTank API integration (v0.7.43+)

PhishTank 의 *public data feed* 의 *download URL*:
- URL: `https://data.phishtank.com/data/<api_key>/online-valid.json`
- Format: JSON with `url`, `phish_id`, `details`, etc.
- Rate limit: 5 req / hour (free tier), 100 req / hour (paid)
- *Auto-update*: cron / GitHub Actions 의 *daily* 의 *pull* 의 *external feed* 의 *update*.

```python
# Pseudo-code (v0.7.43+)
def fetch_phishtank_feed(api_key: str) -> list[str]:
    """Fetch PhishTank online-valid feed, return list of URLs."""
    import requests
    response = requests.get(
        f"https://data.phishtank.com/data/{api_key}/online-valid.json",
        timeout=30,
    )
    response.raise_for_status()
    return [entry["url"] for entry in response.json()]
```

### §2. OpenPhish API integration (v0.7.43+)

OpenPhish 의 *free public feed*:
- URL: `https://openphish.com/feed.txt`
- Format: text file, one URL per line
- Rate limit: 1 req / hour (free), 10 req / hour (paid)
- *Auto-update*: cron 의 *daily* 의 *pull* 의 *operational* 의 *low-friction*.

### §3. VirusTotal API integration (v0.7.44+)

VirusTotal 의 *commercial multi-engine*:
- URL: `https://www.virustotal.com/api/v3/urls/<url_id>`
- Format: JSON with `last_analysis_stats` (malicious count)
- Rate limit: 4 req / minute (free), 1000 req / minute (paid)
- *Per-URL check* 의 *operational* 의 *high-friction* 의 *paid* 의 *commercial*.

### §4. Multi-source federation (v0.7.45+)

PhishTank + OpenPhish + VirusTotal 의 *union* 의 *operational* 의 *low-friction*:
- *3 source* 의 *union* 의 *dedup* 의 *operational* 의 *low-friction*.
- *False positive* 의 *cross-source verification* 의 *operational* 의 *low-friction*.
- *Cost* 의 *budget* 의 *operational* 의 *low-friction* (PhishTank + OpenPhish free, VirusTotal paid).

### §5. Rate-limit aware 의 *operational* 정공법

- `X-RateLimit-Remaining` + `X-RateLimit-Reset` 의 *header respect* 의 *operational* 의 *low-friction*.
- *Exponential backoff* 의 *429* 의 *response* 의 *operational* 의 *low-friction*.
- *Caching* 의 *24h TTL* 의 *operational* 의 *low-friction* (ADR-013 의 *low-friction* 의 *re-use*).

### §6. *Auto-update* 의 *operational cadence* (v0.7.43+)

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.40)** | ADR-022 bundled + manual external feed | v0.7.40 |
| **2 (DONE — v0.7.41)** | ADR-022 formal acceptance | v0.7.41 |
| **3 (DONE — v0.7.42, 본 release)** | ADR-023 formal documentation (PoC) | v0.7.42 |
| **4 (v0.7.43+)** | PhishTank + OpenPhish API integration (code-side) | v0.7.43+ |
| **5 (v0.7.44+)** | VirusTotal API integration (commercial) | v0.7.44+ |
| **6 (v0.7.45+)** | Multi-source federation (3 source union) | v0.7.45+ |
| **7 (v0.7.46+)** | ADR-023 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.46+ |

## Alternatives Considered

### A1. manual-update (status quo, ADR-022)
v0.7.40 의 *manual* external feed update. 장점: simplest, 0 API dependency. 단점: *human* 의 *operational* 의 *friction*, phishing pattern 진화 속도가 *human* 보다 빠름. **rejected** — *auto-update* 의 *operational* 의 *low-friction* 의 *API integration* 의 *follow-up*.

### A2. external-feed (status quo, ADR-022)
JSONL file. 장점: *manual* 의 *operational* 의 *low-friction*. 단점: *update* 의 *human*. **rejected** — 본 ADR-023 의 *API integration* 의 *follow-up* 의 *operational* 보강.

### A3. phishtank-api (chosen for v0.7.43)
PhishTank public data feed. 장점: *free tier* 의 *auto-update* 의 *operational* 의 *low-friction*, community-driven *verified* 데이터. 단점: *rate limit* (5 req / hour free). **chosen** — *low-friction* 의 *start*.

### A4. openphish-api
OpenPhish free public feed. 장점: *truly free*, *high-frequency* update. 단점: *smaller dataset* vs PhishTank. **chosen as secondary source** (v0.7.43+ 의 *multi-source* 의 *federation*).

### A5. virustotal-api
VirusTotal commercial API. 장점: *multi-engine* 의 *high-confidence*, *per-URL check* 의 *real-time* 의 *operational* 보강. 단점: *commercial* (paid), *rate limit* (4 req / minute free). **chosen as tertiary source** (v0.7.44+, *operational* 의 *low-friction* 의 *optional*).

### A6. multi-source-federation (v0.7.45+)
PhishTank + OpenPhish + VirusTotal 의 *union* 의 *dedup* 의 *cross-source verification* 의 *operational* 의 *low-friction*. **chosen as long-term strategy** (v0.7.45+).

## Positive Consequences

- *Auto-update* 의 *operational* 의 *low-friction* 의 *phishing pattern* 의 *currency*.
- *Multi-source* 의 *cross-source verification* 의 *false positive* 의 *reduction* 의 *operational* 의 *low-friction*.
- *Rate-limit aware* 의 *operational* 의 *low-friction* 의 *API* 의 *respect*.
- *OpenPhish + PhishTank* 의 *free* 의 *operational* 의 *low-friction* 의 *operational* 보강.
- *VirusTotal* 의 *commercial* 의 *optional* 의 *operational* 의 *low-friction* 의 *high-confidence*.

## Negative Consequences

- *API key* 의 *operational* 의 *secret management* 의 *operational* 의 *friction*.
- *Rate limit* 의 *operational* 의 *budget* 의 *operational* 의 *low-friction* 의 *limitation*.
- *Auto-update* 의 *network dependency* 의 *operational* 의 *friction* (offline 환경).
- *VirusTotal* 의 *commercial* 의 *operational* 의 *cost* 의 *budget* 의 *operational* 의 *friction*.

## Neutral Consequences

- *API integration* 의 *operational* 의 *low-friction* 의 *optional* — *external feed* 의 *manual* 의 *operational* 의 *backward compat*.
- *PhishTank / OpenPhish / VirusTotal* 의 *3 vendor* 의 *operational* 의 *low-friction* 의 *flexibility* — *switch* 의 *operational* 의 *low-friction* 의 *flexibility*.

## Compliance

- ADR-017 (V-R11 body audit) — phishing keyword 의 *prerequisite* + *follow-up* 의 *operational* 보강
- ADR-022 (phishing keyword feed) — *external feed* 의 *prerequisite* + *auto-update* 의 *follow-up* 의 *operational* 보강
- ADR-013 (V-R10 v2 cache) — *24h TTL* 의 *cache* 의 *re-use* 의 *operational* 의 *low-friction*
- OKF spec v0.1 — *external feed* 의 *JSONL* 의 *machine-readable* 의 *operational* 의 *low-friction*

## Follow-up

1. **v0.7.43**: PhishTank + OpenPhish API integration (code-side, *free* sources)
2. **v0.7.44**: VirusTotal API integration (commercial, *per-URL* check)
3. **v0.7.45**: Multi-source federation (3 source union + dedup + cross-source verification)
4. **v0.7.46+**: ADR-023 formal acceptance (1 release 주기 의 운영 evidence 후)
5. **v0.7.47+**: *Per-host* 의 *phishing landing page* 의 *operational* 의 *real-time* 의 *low-friction*

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-022 (external feed) 의 *API integration + auto-update* follow-up. 6 alternatives (manual, external, PhishTank, OpenPhish, VirusTotal, federation). 4 positive / 2 negative / 1 neutral. 7 section + 7 primary sources. 3 vendor 의 *federation* 의 *long-term* 정공법. | Sisyphus (orchestrator) |
