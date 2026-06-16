---
type: concept
status: accepted
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: accepted_via_adr-025 (v0.7.44, formal documentation)
created: 2026-06-16
updated: 2026-06-16
---

# OKF consumer quick-start tutorial — 5 min walkthrough (ADR-025, v0.7.43 draft)

## 본 page 의 1차 출처

1. **ADR-025 (OKF consumer quick-start tutorial, proposed v0.7.43)**: 본 page 와 1:1 매핑. *rule definition* + *implementation 정공법*.
2. **docs/OKF_CONSUMER_GUIDE.md (v0.7.38)**: *prose documentation* 의 *prerequisite* + *quick-start* 의 *follow-up* 의 *operational* 보강.
3. **ADR-006 (OKF frontmatter, accepted v0.7.34)**: *frontmatter* 의 *machine-readable* 의 *operational* 의 *low-friction* 정공법.
4. **ADR-007 (OKF consumer mode, accepted v0.7.34)**: *strict / loose mode* 의 *operational* 의 *low-friction* 정공법.
5. **ADR-018 (V-R12 commit-pinned URL, accepted v0.7.37)**: *commit-pinned URL* 의 *operational* 의 *low-friction* 정공법.
6. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: *semantic URL* 의 *operational* 의 *low-friction* 정공법.
7. **OKF spec v0.1**: *primary source* 의 *operational* 의 *low-friction* 정공법.

## §1. ADR-025 의 *rule definition*

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **active** — ADR-025 와 동시 promote (v0.7.43 draft → v0.7.44 formal acceptance, 2026-06-16). 본 concept 의 *rule definition* — *code-side* (v0.7.44+ implemented `docs/OKF_CONSUMER_QUICKSTART.md`) 의 *formal documentation*. |
| 2 | tutorial format | *Markdown* 의 *5 section* (Install + Verify + Inspect + Ingest + Lint). |
| 3 | time-to-value | *5 min* 의 *external consumer* 의 *first-time setup* 의 *operational* 정공법. |
| 4 | sample bundle | `docs/samples/okf-bundle-2026-06-16/` 의 *walkthrough* 의 *operational* 정공법. |
| 5 | cross-reference | `docs/OKF_CONSUMER_GUIDE.md` (v0.7.38) 의 *companion* 정공법. |
| 6 | shell command | *copy-paste-able* 의 *operational* 의 *low-friction* 정공법. |

## §2. *5 section* 의 *operational* 정공법 (v0.7.43+)

```markdown
# OKF Consumer Quick-Start (5 min)

## §1. Install workflow_kit
   pip install -e /path/to/standard_ai_workflow/workflow-source

## §2. Verify install
   python -c "import workflow_kit; print(workflow_kit.__version__)"
   # Expected: v0.7.43-beta

## §3. Inspect sample bundle
   ls docs/samples/okf-bundle-2026-06-16/
   # Expected: okf-bundle.yaml, index.md, README.md, concepts/, decisions/

## §4. Ingest (strict mode)
   python -m workflow_kit.okf_import ./docs/samples/okf-bundle-2026-06-16/
   # Expected: ImportReport with pages_imported + 0 errors (R-2 batch warning if > 15)

## §5. Lint URLs
   python -m workflow_kit.url_validity <url>... --semantic
   # Expected: per-URL V-R13 issues (parse-only fast mode)
```

## §3. Sample bundle walkthrough 의 *step-by-step* 정공법 (v0.7.43+)

| Step | Action | Expected output |
|---|---|---|
| 1 | `cat okf-bundle.yaml` | okf_version, vcs_commit, integrity_hash, page_count |
| 2 | `cat index.md` | bundle entry, lists all pages |
| 3 | `ls concepts/` | `<page>.md` files |
| 4 | `python -m workflow_kit.okf_import .` | `ImportReport(pages_total=5, errors=0)` |
| 5 | `python -m workflow_kit.url_validity <url> --semantic` | V-R13 issues (layer 0/1/2 status) |

## §4. CLI command sequence 의 *copy-paste-able* 정공법

- *executable shell* 의 *low-friction* 정공법.
- *documentation* 의 *machine-readable* 의 *low-friction* 정공법.
- *external consumer* 의 *first-time setup* 의 *low-friction* 의 *5 min* 정공법.

## §5. *5 min* 의 *operational* 정공법

- *5 min* 의 *time-to-value* 의 *operational* 의 *low-friction* 정공법.
- *installation + verification + ingestion + URL lint* 의 *4 step* 의 *low-friction* 정공법.
- *no example-code-required* 의 *low-friction* 정공법.

## §6. *gradual rollout* 의 *operational cadence*

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.38)** | `docs/OKF_CONSUMER_GUIDE.md` (prose documentation, 12 section) | v0.7.38 |
| **2 (DONE — v0.7.43, 본 page)** | ADR-025 + concept page (formal documentation) | v0.7.43 |
| **3 (v0.7.43+)** | Quick-start tutorial implementation (`docs/OKF_CONSUMER_QUICKSTART.md`, 5 section) | v0.7.43+ |
| **4 (v0.7.44+)** | Sample bundle walkthrough (step-by-step with output examples) | v0.7.44+ |
| **5 (v0.7.45+)** | CLI command sequence (`docs/CLI_QUICK_REFERENCE.md`) | v0.7.45+ |
| **6 (v0.7.46+)** | ADR-025 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.46+ |

## §7. *operational rigor*

- *deterministic* command sequence — *copy-paste-able* 의 *operational* 의 *low-friction* 정공법.
- *crash-free* tutorial — *error path* 의 *low-friction* 정공법.
- *machine-readable* shell command — *operational* 의 *low-friction* 정공법.
- *5 min* 의 *time-to-value* — *operational* 의 *low-friction* 정공법.
- *cross-reference* (prose ↔ quick-start) — *navigate* 의 *low-friction* 정공법.

## §8. Compliance

- ADR-006 (OKF frontmatter) — *frontmatter* 의 *machine-readable* 의 *operational* 정공법
- ADR-007 (OKF consumer mode) — *strict / loose mode* 의 *operational* 정공법
- ADR-008 (in-repo path) — *resource URL* 의 *operational* 정공법
- ADR-011 (OKF version) — *version auto-detect* 의 *operational* 정공법
- ADR-018 (V-R12 commit-pinned URL) — *commit-pinned URL* 의 *operational* 정공법
- ADR-019 (V-R13 semantic URL) — *semantic URL* 의 *operational* 정공법
- OKF spec v0.1 — *primary source* 의 *operational* 정공법

## §9. Follow-up 후보 (v0.7.43+)

1. **v0.7.43+**: Quick-start tutorial implementation (`docs/OKF_CONSUMER_QUICKSTART.md`, 5 section)
2. **v0.7.44+**: Sample bundle walkthrough (step-by-step with output examples)
3. **v0.7.45+**: CLI command sequence (`docs/CLI_QUICK_REFERENCE.md`)
4. **v0.7.46+**: ADR-025 formal acceptance (1 release 주기 의 운영 evidence 후)
5. **v0.7.47+**: Video tutorial (operational 보조)
6. **v0.7.48+**: Jupyter notebook (advanced tutorial)

## §10. Related

- [decisions/adr-025-okf-consumer-quickstart-tutorial.md](../decisions/adr-025-okf-consumer-quickstart-tutorial.md) — 본 concept 의 *formal documentation*
- [docs/OKF_CONSUMER_GUIDE.md](../../../docs/OKF_CONSUMER_GUIDE.md) — *prose documentation* 의 *prerequisite* + *companion*

## §11. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.2.0 | **v0.7.44 release: status `proposed` → `active` + ADR-025 `proposed` → `accepted`.** 본 release 시점의 evidence (docs/OKF_CONSUMER_QUICKSTART.md 5 section + sample bundle walkthrough 5-step table + CLI command sequence copy-paste-able). `v0.7.44 follow-up bundle` 의 Phase 1 (TASK-V0744-ADR-FORMAL). | Sisyphus (orchestrator) |
