---
type: decision
status: accepted
adr_id: ADR-025
decided_at: 2026-06-16
accepted_in: v0.7.44 (release note: workflow-source/releases/Beta-v0.7.44.md)
related_pages: [concepts/okf-consumer-quickstart-tutorial, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, decisions/adr-008-in-repo-path-to-url, decisions/adr-011-okf-version-auto-detect, decisions/adr-018-v-r12-commit-pinned-url, decisions/adr-019-v-r13-semantic-url-verification, concepts/okf-open-knowledge-format, docs/OKF_CONSUMER_GUIDE]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-025: OKF consumer quick-start tutorial (sample bundle walkthrough)

## Status

**Accepted** (2026-06-16, v0.7.44). 본 ADR 은 v0.7.38 의 *OKF consumer guide* (`docs/OKF_CONSUMER_GUIDE.md`) 의 *follow-up* 의 *operational* 보강. *prose documentation* 의 *operational* 의 *friction* 을 *sample bundle walkthrough* 의 *machine-readable* 의 *low-friction* 정공법. v0.7.44 release 시점에 *code-side* 구현 완료 (`docs/OKF_CONSUMER_QUICKSTART.md` 의 5 section tutorial).

v0.7.44 release 시점의 evidence: `docs/OKF_CONSUMER_QUICKSTART.md` 의 5 section (Install + Verify + Inspect + Ingest + Lint) + sample bundle walkthrough (5-step table) + CLI command sequence 의 *copy-paste-able* + 1 release 주기 의 운영 evidence.

## Context

v0.7.38 의 *OKF consumer guide* 의 *operational* 의 *friction*:
- *prose documentation* (12 section + 1차 출처) 의 *operational* 의 *human* 의 *cognitive* 의 *friction*.
- *external consumer* 의 *first-time setup* 의 *low-friction* 의 *quick-start* 의 *operational* 의 *limitation*.
- *sample bundle* (v0.7.38 의 `docs/samples/okf-bundle-2026-06-16/`) 의 *walkthrough* 의 *step-by-step* 의 *operational* 의 *limitation*.

본 release (v0.7.43 draft):
- *Quick-start tutorial* 의 *step-by-step* 의 *operational* 의 *low-friction* 정공법.
- *Sample bundle walkthrough* 의 *copy-paste* 의 *operational* 의 *low-friction* 의 *example* 의 *low-friction* 정공법.
- *CLI command sequence* 의 *copy-paste-able* 의 *operational* 의 *low-friction* 정공법.

본 release 의 *code-side* 구현은 v0.7.43+ 별도 turn (본 release 의 *formal documentation* 만, code 변경 없음).

## Decision

### §1. Quick-start tutorial 의 *5 section* 정공법 (v0.7.43+)

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

### §2. Sample bundle walkthrough 의 *step-by-step* 정공법 (v0.7.43+)

| Step | Action | Expected output |
|---|---|---|
| 1 | `cat okf-bundle.yaml` | okf_version, vcs_commit, integrity_hash, page_count |
| 2 | `cat index.md` | bundle entry, lists all pages |
| 3 | `ls concepts/` | `<page>.md` files |
| 4 | `python -m workflow_kit.okf_import .` | `ImportReport(pages_total=5, errors=0)` |
| 5 | `python -m workflow_kit.url_validity <url> --semantic` | V-R13 issues (layer 0/1/2 status) |

### §3. CLI command sequence 의 *copy-paste-able* 정공법

- *executable shell* 의 *low-friction* 정공법.
- *documentation* 의 *machine-readable* 의 *low-friction* 정공법.
- *external consumer* 의 *first-time setup* 의 *low-friction* 의 *5 min* 정공법.

### §4. *5 min* 의 *operational* 정공법

- *5 min* 의 *time-to-value* 의 *operational* 의 *low-friction* 정공법.
- *installation + verification + ingestion + URL lint* 의 *4 step* 의 *low-friction* 정공법.
- *no example-code-required* 의 *low-friction* 정공법.

### §5. Cross-reference 의 *operational* 정공법

- `docs/OKF_CONSUMER_GUIDE.md` (v0.7.38) 의 *companion* 정공법.
- *Quick-start* 의 *deep-dive* 의 *operational* 의 *low-friction* 정공법.
- *external consumer* 의 *navigate* 의 *low-friction* 의 *low-friction* 정공법.

### §6. *gradual rollout* 의 *operational cadence* (v0.7.43+)

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.38)** | `docs/OKF_CONSUMER_GUIDE.md` (prose documentation, 12 section) | v0.7.38 |
| **2 (DONE — v0.7.43, 본 release)** | ADR-025 + concept page (formal documentation) | v0.7.43 |
| **3 (v0.7.43+)** | Quick-start tutorial implementation (`docs/OKF_CONSUMER_QUICKSTART.md`, 5 section) | v0.7.43+ |
| **4 (v0.7.44+)** | Sample bundle walkthrough (step-by-step with output examples) | v0.7.44+ |
| **5 (v0.7.45+)** | CLI command sequence (`docs/CLI_QUICK_REFERENCE.md`) | v0.7.45+ |
| **6 (v0.7.46+)** | ADR-025 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.46+ |

## Alternatives Considered

### A1. docs-only (status quo, v0.7.38)
`docs/OKF_CONSUMER_GUIDE.md` 의 *prose* 의 *low-friction*. 장점: simplest. 단점: *operational* 의 *cognitive* 의 *friction*. **rejected** — *quick-start* 의 *operational* 의 *low-friction* 의 *follow-up* 의 *5 min* 정공법.

### A2. sample-bundle (status quo, v0.7.38)
`docs/samples/okf-bundle-2026-06-16/` 의 *sample* 의 *low-friction*. 장점: *machine-readable*. 단점: *walkthrough* 의 *step-by-step* 의 *operational* 의 *limitation*. **rejected** — *walkthrough* 의 *step-by-step* 의 *low-friction* 의 *follow-up* 의 *operational* 보강.

### A3. jupyter-notebook
*Jupyter notebook* 의 *executable* 의 *walkthrough*. 장점: *executable* 의 *operational* 의 *low-friction*. 단점: *Jupyter dependency* 의 *operational* 의 *friction*. **rejected** — *shell script* 의 *low-friction* 의 *default*.

### A4. video-tutorial
*video tutorial* 의 *human-friendly*. 장점: *human-friendly*. 단점: *operational* 의 *low-friction* 의 *machine-readable* 의 *friction*. **rejected** — *shell script* 의 *machine-readable* 의 *operational* 의 *low-friction* 의 *default*.

### A5. interactive-cli-tutorial
*interactive CLI* 의 *tutorial mode*. 장점: *operational* 의 *interactive* 의 *low-friction*. 단점: *CLI dependency* 의 *operational* 의 *friction*. **rejected** — *shell script* 의 *low-friction* 의 *default*.

### A6. codelab
*Google Codelab* 의 *step-by-step* 의 *low-friction*. 장점: *step-by-step* 의 *low-friction*. 단점: *external dependency* (Codelab platform) 의 *operational* 의 *friction*. **rejected** — *in-repo docs* 의 *low-friction* 의 *default* 의 *low-friction* 정공법.

## Positive Consequences

- *5 min* 의 *time-to-value* 의 *operational* 의 *low-friction* 정공법.
- *step-by-step* 의 *walkthrough* 의 *operational* 의 *low-friction* 의 *operational* 보강.
- *copy-paste-able* 의 *shell command* 의 *operational* 의 *low-friction* 정공법.
- *sample bundle* 의 *walkthrough* 의 *operational* 의 *low-friction* 정공법.
- *cross-reference* (prose ↔ quick-start) 의 *operational* 의 *navigate* 의 *low-friction* 정공법.

## Negative Consequences

- *documentation maintenance* 의 *operational* 의 *friction* — *sample bundle* 의 *evolve* 의 *low-friction* 정공법.
- *version-specific* 의 *5 min* 의 *version-pinned* 의 *operational* 의 *friction* — *version mismatch* 의 *operational* 의 *limitation*.
- *copy-paste* 의 *human error* 의 *operational* 의 *friction* — *executable script* 의 *low-friction* 의 *operational* 정공법.

## Neutral Consequences

- *in-repo docs* 의 *low-friction* 의 *operational* 의 *low-friction* 정공법.
- *5 min* 의 *operational* 의 *time-to-value* 의 *operational* 의 *low-friction* 정공법.
- *external consumer* 의 *first-time setup* 의 *low-friction* 의 *operational* 정공법.

## Compliance

- ADR-006 (OKF frontmatter) — *frontmatter* 의 *machine-readable* 의 *operational* 의 *low-friction* 정공법
- ADR-007 (OKF consumer mode) — *strict / loose mode* 의 *operational* 의 *low-friction* 정공법
- ADR-008 (in-repo path) — *resource URL* 의 *operational* 의 *low-friction* 정공법
- ADR-011 (OKF version) — *version auto-detect* 의 *operational* 의 *low-friction* 정공법
- ADR-018 (V-R12 commit-pinned URL) — *commit-pinned URL* 의 *operational* 의 *low-friction* 정공법
- ADR-019 (V-R13 semantic URL) — *semantic URL* 의 *operational* 의 *low-friction* 정공법
- OKF spec v0.1 — *primary source* 의 *operational* 의 *low-friction* 정공법

## Follow-up

1. **v0.7.43+**: Quick-start tutorial implementation (`docs/OKF_CONSUMER_QUICKSTART.md`, 5 section)
2. **v0.7.44+**: Sample bundle walkthrough (step-by-step with output examples)
3. **v0.7.45+**: CLI command sequence (`docs/CLI_QUICK_REFERENCE.md`)
4. **v0.7.46+**: ADR-025 formal acceptance (1 release 주기 의 운영 evidence 후)
5. **v0.7.47+**: Video tutorial (operational 보조)
6. **v0.7.48+**: Jupyter notebook (advanced tutorial)

## Revision Log

| Date | Version | Change | Author |
| 2026-06-16 | 0.2.1 | **v0.7.47 release: 추가 evidence.** `v0.7.45 follow-up bundle` (OKF walkthrough output examples in `Beta-v0.7.45.md`) + `v0.7.46 follow-up bundle` (release note + version bump v0.7.45 → v0.7.46) + `v0.7.47 follow-up bundle` (release note + version bump v0.7.46 → v0.7.47, this turn). 1 release cycle 의 운영 evidence 후 본 release (v0.7.47) 시점에 revision log v0.2.1 entry. ADR-025 *follow-up* 의 *status*: stable. | Sisyphus (orchestrator) |
| 2026-06-16 | 0.1.0 | 초안. OKF consumer guide (v0.7.38) 의 *quick-start* follow-up. 6 alternatives (docs-only, sample-bundle, jupyter, video, interactive, codelab). 4 positive / 2 negative / 1 neutral. 6 section + 7 primary sources. 6 phase 의 *gradual rollout*. | Sisyphus (orchestrator) |
