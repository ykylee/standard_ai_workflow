---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: pending_via_adr-022 (proposed, v0.7.40 formal)
related_pages: [decisions/adr-022-phishing-keyword-feed, decisions/adr-017-v-r11-body-audit, concepts/v-r11-body-audit, decisions/adr-006-okf-compat-frontmatter, concepts/okf-open-knowledge-format]
created: 2026-06-16
updated: 2026-06-16
---

# Phishing keyword feed — V-R11 v2 fallback chain (custom > external > bundled)

## 본 page 의 1차 출처

1. **ADR-022 (phishing keyword feed, proposed v0.7.40)**: 본 page 와 1:1 매핑. *rule definition* + *implementation 정공법*.
2. **ADR-017 (V-R11 body audit, accepted v0.7.37)**: 본 concept 의 *prerequisite* + *follow-up* 의 *operational* 보강.
3. **V-R10 (URL validity, ADR-010/012/013/014/015)**: URL 의 *phishing landing page* 의 *prerequisite* layer.
4. **ADR-006 (OKF frontmatter)**: external feed 의 *JSONL format* 의 *operational* 정합.
5. **OKF spec v0.1** (GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): external feed 의 *machine-readable* 의 *low-friction* 의 *operational* 보강.

## §1. ADR-022 의 *rule definition*

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-022 와 동시 promote (v0.7.40 formal documentation, 2026-06-16). 본 concept 의 *rule definition* — *code-side* (v0.7.39 PoC) 의 *formal documentation*. |
| 2 | module | `workflow_kit.phishing_keywords` (4.9 KB). |
| 3 | BUNDLED_KEYWORDS | 8 baseline (extracted from url_validity.PHISHING_KEYWORDS v0.7.37+). |
| 4 | fallback chain | `custom > external > bundled` (priority order). |
| 5 | dedup | case-insensitive (lowercase) + first-occurrence order preserved. |
| 6 | silent fallback | file not found / OSError / malformed JSONL line → silent skip (bundled-only). |

## §2. 3-layer fallback chain 의 *operational* 정공법

```
+---------------------+
|       custom        |   <-- user-provided Iterable (priority 1)
| load_phishing_      |
| keywords(custom=)   |
+---------------------+
              |
              v
+---------------------+
|   external_feed     |   <-- JSONL file (Path, priority 2)
| load_phishing_      |
| keywords(external_  |
| feed=Path("feed"))  |
+---------------------+
              |
              v
+---------------------+
| BUNDLED_KEYWORDS    |   <-- 8 baseline (priority 3, fallback)
| bundled_keywords()  |
+---------------------+
```

| Layer | Source | Format | Update mechanism |
|---|---|---|---|
| custom | `custom` argument (Iterable[str]) | Python list / tuple / generator | *per-call* 의 *caller-controlled* |
| external | `external_feed` argument (Path) | JSONL (one keyword per line) | *manual* — file update + bundle + commit (v0.7.41+ auto) |
| bundled | `BUNDLED_KEYWORDS` (module constant) | Python tuple | *release cycle* (1 release / 1-2 weeks) |

## §3. external feed 의 *JSONL format* 의 *operational* 정공법

```jsonl
{"keyword": "verify your account", "source": "phishtank", "added_at": "2026-06-16"}
{"keyword": "click here immediately", "source": "openphish", "added_at": "2026-06-15"}
{"keyword": "your custom new pattern", "source": "internal-q3-2026", "added_at": "2026-06-14"}
```

- 한 줄에 한 keyword (`{"keyword": "...", ...}`)
- *required* field: `keyword` (string, non-empty)
- *optional* field: `source` / `added_at` (ignored by parser)
- malformed line: skip (다음 line 진행)
- missing `keyword` field: skip
- empty `keyword` (whitespace only): skip

## §4. case-insensitive dedup 의 *operational* 정공법

```python
# Pseudo-code
seen: set[str] = set()
out: list[str] = []
for layer in [custom, external, bundled]:
    for kw in layer:
        kw = kw.strip().lower()  # case-insensitive
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
return tuple(out)
```

- *first-occurrence* order preserved (custom > external > bundled)
- *case* 는 *first-occurrence* 의 *original* 보존 (display 용)
- *lowercase* 비교 의 *deterministic* 의 *low-friction*

## §5. silent fallback 의 *operational rigor*

| Error | Behavior |
|---|---|
| `external_feed=None` | skip layer → custom + bundled 만 |
| `external_feed` not found | silent (OSError caught) → custom + bundled 만 |
| `external_feed` read error (permission, disk) | silent (OSError caught) → custom + bundled 만 |
| JSONL line parse error | skip (json.JSONDecodeError caught) → 다음 line 진행 |
| JSONL `keyword` field missing | skip (string check) → 다음 line 진행 |
| JSONL `keyword` field empty | skip (whitespace check) → 다음 line 진행 |
| custom = `[]` (empty) | skip layer → external + bundled 만 |

*operational* 의 *crash-free* 의 *low-friction* 의 *graceful degradation* — external feed 의 *partial corruption* 의 *bundled-only* 의 *operational* 의 *low-friction*.

## §6. *gradual rollout* 의 *operational cadence*

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.37)** | ADR-017 (V-R11 body audit). 8 bundled keyword 의 *rule definition* + *code-side*. | v0.7.37 |
| **2 (DONE — v0.7.39 PoC)** | `phishing_keywords` module 신규 + 3-layer fallback chain + 11 tests. *code-side* 의 *operational* 보강. | v0.7.39 |
| **3 (DONE — v0.7.40 formal, 본 page)** | ADR-022 (proposed) + 본 concept page (proposed). 5 alternatives + 4 positive / 2 negative / 1 neutral. *formal documentation* 의 *code-side* 의 *rule-side* 정합. | v0.7.40 |
| **4 (v0.7.40+, 별도 turn)** | ADR-022 formal acceptance (1 release 주기 의 운영 evidence 후). | v0.7.40+ |
| **5 (v0.7.41+)** | PhishTank API integration + rate-limit aware + auto-update. | v0.7.41+ |

## §7. *operational rigor*

- *deterministic* dedup: lowercase + first-occurrence order.
- *transparent* layered: 3 priority layer 의 *explicit* 순서.
- *crash-free*: file not found / malformed / OSError 의 *silent fallback* 의 *operational* 의 *bundled-only* 보강.
- *machine-readable*: JSONL format 의 *external feed* 의 *low-friction* 의 *operational* 의 *edit* 의 *operational* 보강.
- *no CLI flag* (v0.7.40) — Python API 만. *operational* 의 *low-friction* 의 *boring* default.

## §8. Compliance

- ADR-017 (V-R11 body audit) — phishing keyword 의 *prerequisite* + *follow-up* 의 *operational* 보강
- ADR-006 (OKF frontmatter) — `phishing_keywords` 의 *machine-readable* 의 *JSONL* format 의 *operational* 정합
- ADR-008 (in-repo path) — external feed 의 *in-repo* path 의 *operational* 의 *low-friction*

## §9. Follow-up 후보 (v0.7.41+)

1. **v0.7.41**: PhishTank API integration + rate-limit aware (`X-RateLimit-Remaining` header respect)
2. **v0.7.41**: external feed 의 *auto-update* (cron + version-pinned `feed_v0.1.jsonl`)
3. **v0.7.41**: per-source metric — `phishing_detections_custom / external / bundled` 분리
4. **v0.7.41**: `check_url_body` 의 `phishing_keywords=` parameter wiring
5. **v0.7.42+**: dynamic content audit (Playwright) + phishing detection 의 *real-time* 의 *operational* 보강
6. **v0.7.42+**: OpenPhish / VirusTotal API integration (multi-source 의 *operational* 의 *low-friction*)

## §10. Related

- [decisions/adr-022-phishing-keyword-feed.md](../decisions/adr-022-phishing-keyword-feed.md) — 본 concept 의 *formal documentation*
- [decisions/adr-017-v-r11-body-audit.md](../decisions/adr-017-v-r11-body-audit.md) — V-R11 의 *prerequisite*
- [concepts/v-r11-body-audit.md](../concepts/v-r11-body-audit.md) — V-R11 의 *rule definition*