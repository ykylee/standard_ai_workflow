---
type: concept
title: OKF (Open Knowledge Format) v0.1
description: A bundle is a self-contained, hierarchical collection of knowledge documents — the unit of distribution.
resource: "https://github.com/ykylee/standard_ai_workflow/blob/main/external (https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md, 2026-06-16)"
tags: [status:active, wiki-type:concept]
timestamp: "2026-06-16T00:00:00Z"
created: 2026-06-16
status: active
related_pages: [concepts/wiki-source-rule-r9, concepts/stage-gate-pattern, concepts/contract-v1-output-validation, decisions/adr-001-3-layer-separation, patterns/r4-anchor-index, topics/wiki-ingest-lifecycle, patterns/wiki-stub-emit]
r9_skip: true
---
# OKF (Open Knowledge Format) v0.1

- 문서 목적: Google Cloud 가 2026-06-12 발표한 **Open Knowledge Format (OKF) v0.1** spec 의 구조·원칙·우리의 wiki (ai-workflow/wiki/) 와의 정합/갭을 정리한다. **status=active** — primary source 확보 완료.
- 범위: 1차 출처 (`GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md`, 457 lines) + 3 sample bundle (GA4 / Stack Overflow / Bitcoin) + 우리 schema 대비 정합
- 최종 수정일: 2026-06-16

## §0 Verification  {#s0-verification}

| # | 항목 | 값 |
|---|---|---|
| 1 | verification_status | **VERIFIED** — primary source located 2026-06-16 |
| 2 | primary source | `https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md` (457 lines, v0.1 Draft) |
| 3 | publisher | Google Cloud (GoogleCloudPlatform org, Apache 2.0) |
| 4 | release date | 2026-06-12 |
| 5 | reference impl | `enrichment_agent` (BQ + web pass → OKF bundle) + `visualize` (Cytoscape.js graph viewer) in same repo |
| 6 | sample bundles | `bundles/ga4/`, `bundles/stackoverflow/`, `bundles/crypto_bitcoin/` (3 ready-to-browse) |
| 7 | C-OKF-1 status | **RESOLVED** — primary source located, all `[INFERENCE]` removed |

## §1 TL;DR  {#s1-tldr}

| # | 항목 | 값 |
|---|---|---|
| 1 | container | directory of Markdown files = "Knowledge Bundle" |
| 2 | file = concept | one `.md` per concept, file path (sans `.md`) = concept ID |
| 3 | encoding | UTF-8 Markdown |
| 4 | frontmatter | YAML, `---` delimiters, 첫 block. **non-reserved `.md` 모든 파일에 required** |
| 5 | required field | `type` (non-empty string, no central registry) |
| 6 | recommended fields | `title`, `description`, `resource`, `tags`, `timestamp` (ISO 8601) |
| 7 | reserved files | `index.md` (directory listing, no frontmatter), `log.md` (date-grouped change log) |
| 8 | cross-link | standard markdown link, `/abs/path.md` (bundle-relative, 권장) or relative |
| 9 | consumer policy | MUST NOT reject (missing optional, unknown type, unknown key, broken link, missing index) |
| 10 | authority | none — no SDK, runtime, or schema registry |
| 11 | version | v0.1 (draft, `okf_version: "0.1"` in bundle root `index.md` frontmatter) |

## §2 Core Concept: The Knowledge Bundle  {#s2-bundle}

A bundle is a self-contained, hierarchical collection of knowledge documents — the unit of distribution.

### §2.1 Distribution Forms

- git repository (recommended — provides history, attribution, diffs)
- tarball / zip of the directory
- subdirectory within a larger repository

### §2.2 Bundle Structure (Directory Layout)

```
path/to/bundle/
├── index.md                      # optional, reserved — directory listing
├── log.md                        # optional, reserved — update history
├── <concept>.md                  # a concept at the bundle root
└── <subdirectory>/
    ├── index.md
    ├── <concept>.md
    └── <subdirectory>/
        └── …
```

### §2.3 Reserved Filenames (§3.1)

`index.md` 와 `log.md` 는 어느 hierarchy level 에서든 concept 으로 사용 불가. 정의된 의미만 가짐 (§6, §7).

## §3 Concept Documents  {#s3-concepts}

Every concept = one UTF-8 Markdown file with two parts:
1. **YAML frontmatter block** (`---` 시작 + 닫음)
2. **markdown body** (free-form, structural 권장)

### §3.1 Frontmatter Schema (§4.1)

```yaml
---
type: <Type name>                  # REQUIRED
title: <Optional display name>
description: <Optional one-line summary>
resource: <Optional canonical URI for the underlying asset>
tags: [<tag>, <tag>, …]            # Optional
timestamp: <ISO 8601 datetime>     # Optional last-modified time
# … other producer-defined key/value pairs
---
```

**Required:**
- `type` — short string. Example values: `BigQuery Table`, `BigQuery Dataset`, `API Endpoint`, `Metric`, `Playbook`, `Reference`. **No central registry** — producers pick self-explanatory values; consumers tolerate unknown types.

**Recommended (in priority order):**
- `title` — human-readable display name (consumer MAY derive from filename)
- `description` — single sentence summary
- `resource` — canonical URI for the underlying asset
- `tags` — YAML list of short strings
- `timestamp` — ISO 8601 last-modified time

**Extensions:** Producers MAY include any additional keys. Consumers SHOULD preserve unknown keys on round-trip and SHOULD NOT reject unknown fields.

### §3.2 Body (§4.2)

Standard markdown. No required sections, but **conventional headings**:

| Heading | Purpose |
|---|---|
| `# Schema` | structured description of an asset's columns/fields |
| `# Examples` | concrete usage examples, often as fenced code blocks |
| `# Citations` | external sources backing claims (see §8) |

### §3.3 Example: resource-bound concept (§4.3)

```markdown
---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
timestamp: 2026-05-28T14:30:00Z
---

# Schema

| Column        | Type      | Description                              |
|---------------|-----------|------------------------------------------|
| `order_id`    | STRING    | Globally unique order identifier.        |
| `customer_id` | STRING    | Foreign key into [customers](/tables/customers.md). |
| `total_usd`   | NUMERIC   | Order total in US dollars.               |
| `placed_at`   | TIMESTAMP | When the customer submitted the order.   |

# Joins

Joined with [customers](/tables/customers.md) on `customer_id`.

# Citations

[1] [BigQuery table schema](https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders)
```

## §4 Cross-Linking (§5)  {#s4-links}

### §4.1 Two Forms

- **Bundle-relative (권장)**: `/tables/customers.md` — stable when documents move within their subdirectory
- **Relative**: `./other.md` — standard markdown relative

### §4.2 Semantics

A link from A to B asserts a *relationship*. The specific kind (parent/child, references, joins-with, depends-on) is conveyed by surrounding prose, not the link itself. Graph consumers treat all links as directed edges of an untyped relationship.

**Consumers MUST tolerate broken links** — a missing target is not malformed, it may represent not-yet-written knowledge.

## §5 Index Files (§6)  {#s5-index}

`index.md` MAY appear in any directory. It enumerates contents to support **progressive disclosure**.

### §5.1 Structure

- **No frontmatter** (in an `index.md`)
- Body: one or more section headings, each grouping concepts:

```markdown
# Section / Group Heading

* [Title 1](relative-url-1) - short description of item 1
* [Title 2](relative-url-2) - short description of item 2

# Another Section

* [Subdirectory](subdir/) - short description of the subdirectory
```

Entries SHOULD include the description from the linked concept's frontmatter. Producers MAY generate `index.md` automatically; consumers MAY synthesize one on the fly.

## §6 Log Files (§7)  {#s6-log}

`log.md` MAY appear at any level. Records change history of that scope.

### §6.1 Format

- Flat list of date-grouped entries, newest first
- Date headings: ISO 8601 `YYYY-MM-DD`
- Entries are prose; leading bold word (`**Update**`, `**Creation**`, `**Deprecation**`) is convention only

### §6.2 Example

```markdown
# Directory Update Log

## 2026-05-22
* **Update**: Added new BigQuery table reference for [Customer Metrics](/tables/customer-metrics.md).
* **Creation**: Established the [Dataplex Playbook](/playbooks/dataplex.md).

## 2026-05-15
* **Initialization**: Created foundational directory structure.
```

## §7 Citations (§8)  {#s7-citations}

When a concept's body makes claims sourced from external material, list under `# Citations` at the bottom:

```markdown
# Citations

[1] [BigQuery public dataset announcement](https://cloud.google.com/blog/products/data-analytics/...)
[2] [Internal data quality runbook](https://wiki.acme.internal/data/quality)
```

Citation links MAY be absolute URLs, bundle-relative paths, or paths into a `references/` subdirectory that mirrors external material as first-class OKF concepts.

## §8 Conformance (§9)  {#s8-conformance}

A bundle is **conformant** with OKF v0.1 if:

1. Every non-reserved `.md` file contains a parseable YAML frontmatter block.
2. Every frontmatter block contains a non-empty `type` field.
3. Every reserved filename (`index.md`, `log.md`) follows §6/§7 when present.

**Consumers SHOULD treat all other constraints as soft guidance. MUST NOT reject a bundle because of:**
- Missing optional frontmatter fields
- Unknown `type` values
- Unknown additional frontmatter keys
- Broken cross-links
- Missing `index.md` files

This permissive model is intentional: OKF is meant to remain useful as bundles grow, get refactored, and are partially generated by agents.

## §9 Versioning (§11)  {#s9-versioning}

- This document specifies **OKF v0.1** (Draft)
- Future revisions: `<major>.<minor>`
  - **minor**: backward-compatible additions (new optional fields, new conventional headings)
  - **major**: breaking changes (renaming required fields, changing reserved filenames)
- Bundles MAY declare their OKF version: `okf_version: "0.1"` in **bundle-root `index.md` frontmatter** (the only place frontmatter is permitted in an `index.md`)
- Consumers that don't understand a declared version SHOULD attempt best-effort consumption rather than refusing

## §10 Relationship to Other Formats (§10)  {#s10-relationship}

| Pattern | OKF 의 차이 |
|---|---|
| LLM "wiki" repos (markdown + frontmatter) | OKF 가 **specified** (interop 위해 small rule set 명시) |
| Obsidian / Notion (hierarchical markdown + cross-links) | OKF 가 format pinning, tool-independent |
| "Metadata as code" (catalog metadata alongside code) | OKF 가 format 만 정의, storage/service 불요 |

**Non-goals** (per §1):
- Defining a fixed taxonomy of concept types
- Prescribing storage / serving / query infrastructure
- Replacing domain-specific schemas (Avro, Protobuf, OpenAPI) — OKF *references* them

## §11 Reference Implementation & Samples  {#s11-reference-impl}

같은 repo (`GoogleCloudPlatform/knowledge-catalog`) 가 OKF 의 producer + consumer 양쪽 POC 제공:

| Component | Role | Stack |
|---|---|---|
| `enrichment_agent` | **producer** POC | Google ADK + Gemini + BigQuery. 2-pass: BQ metadata pass → web crawl pass with LLM-driven link selection. Hard cap `--web-max-pages` + allowed-host filter. |
| `visualize` | **consumer** POC | Self-contained HTML viewer (Cytoscape.js graph + marked.js markdown). Reads bundle, embeds as JSON, no backend. |

### §11.1 Sample Bundles (체크인됨)

| Bundle | Domain | Reference |
|---|---|---|
| `bundles/ga4/` | GA4 e-commerce dataset | [viz.html](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/bundles/ga4/viz.html) |
| `bundles/stackoverflow/` | Stack Overflow public dataset | [viz.html](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/bundles/stackoverflow/viz.html) |
| `bundles/crypto_bitcoin/` | Bitcoin blocks/transactions (cross-table FK in prose) | [viz.html](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/bundles/crypto_bitcoin/viz.html) |

### §11.2 Recipes

각 sample = `samples/<name>/` 의 recipe (`seed URL` + `enrich` command) + `bundles/<name>/` 의 produced bundle. recipe 열면 재현 가능, bundle 열면 즉시 browse 가능.

## §12 Gap vs. Our Wiki Schema  {#s12-gap}

[ai-workflow/wiki/SCHEMA.md](../SCHEMA.md) 와의 정합 매트릭스 (C-OKF-1 해소 후 정밀 분석).

| Concern | OKF v0.1 | 우리 wiki (R1~R9) | Gap | Resolution |
|---|---|---|---|---|
| container | dir of `.md` | `ai-workflow/wiki/` 단일 (R1) | OK | — |
| file = concept | yes | 1 page = 1 concept/decision/pattern/entity/query | OK | — |
| YAML frontmatter | required | required (5 type-specific) | OK | — |
| `type` field | required (string, no registry) | required (5 enum) | strict vs free string | **OKF consumer 가 우리 `type: concept` / `entity` / `decision` / `pattern` / `query` 모두 tolerate** — `type` 은 string 이므로 호환 |
| `title` | recommended (optional) | not required | OK | OKF 권장 field, 우리 보너스. emit 권장 |
| `description` | recommended | not required | OK | emit 권장 |
| `resource` | recommended (canonical URI) | `last_ingested_from` (similar) | 의미 유사 | 우리 `last_ingested_from` ≠ URI 일 수 있음 (in-repo path). OKF export 시 `resource` 로 매핑 가능 |
| `tags` | recommended (list) | not required | OK | OKF 권장. emit 시 우리 위키 taxonomy (`r4-anchor-index` 등) 와 alignment |
| `timestamp` | recommended (ISO 8601) | `updated` (YYYY-MM-DD) | granularity | 우리 가 `updated` 만 emit, OKF export 시 `updated` → `timestamp: <YYYY-MM-DD>T00:00:00Z` 변환 |
| `status` | not defined | required (active/draft/deprecated) | OKF에 부재 | OKF consumer 가 `status` 무시. OKF export 시 `tags: [status:active]` 같은 식으로 표현 가능 |
| `created` / `updated` | `timestamp` 1개 | 둘 다 required | semantic diff | OKF export 시 둘 다 `timestamp` 로 매핑 불가 → `created` 별도 처리 필요 (e.g. `created` field 추가 — OKF 가 unknown key tolerate 하므로 가능) |
| `related_pages` | not defined (cross-link 가 역할) | required | OKF 의 cross-link 와 중복 | OKF export 시 cross-link 로 풀어 emit |
| `last_ingested_from` | not defined (대신 `resource`) | required | 의미 유사 — R9 audit | OKF export 시 `resource` 또는 `references` 섹션으로 |
| 5-type enum | no (free string) | yes (R8 strict) | strict vs loose | OKF consumer 는 unknown type tolerate, 우리 는 strict. **양방향 OK** |
| reserved `index.md` | yes (no frontmatter) | yes (R4 anchor) | 우리 가 strict | OKF index 는 우리 anchor 의 relaxed form. OKF-spec index.md 그대로 expose 가능 |
| reserved `log.md` | yes (date-grouped entries) | yes (R8 append-only) | format 차이 | OKF log 형식 = date-grouped prose. 우리 log.md 는 R8 formal structure. **cross-export 시 format 변환 필요** |
| body section conventions | `# Schema` / `# Examples` / `# Citations` (soft) | free (anchor based) | OK | OKF 가 soft convention, 우리 도 자유 — 호환 |
| ADR pattern | not defined | defined (decisions/ADR-NNN) | OKF 무관 | 우리 ADR format 그대로 OKF export 가능 (`type: ADR`) |
| lint rules | not defined | 5 lint (V-1~V-8, V-R9) | OKF 무관 | 우리 side 의 R8/R9/R4 enforcement. OKF consumer 무관 |
| permissive consumption | MUST NOT reject (unknown key, broken link, missing optional) | strict (5 lint error) | 정반대 | 우리 가 OKF consumer 역할 시 우리 lint 는 reject → **OKF 호환 consumer 모드 별도 필요** |

### §12.1 핵심 갭 (양방향)

1. **우리 → OKF export**: `updated` (date) → `timestamp` (ISO 8601 datetime) 정밀도 갭. `last_ingested_from` (in-repo path) ≠ `resource` (URI) 매핑 결정 필요. `status`/`related_pages` → `tags` or extra frontmatter key 변환 규약 필요.
2. **OKF → 우리 consumer**: 우리 R8/R9/R4 strict lint 가 OKF spec 위반 reject 가능. **loose consumer mode 별도 필요** — 우리 wiki 가 OKF consumer 역할 시 strict lint disable + unknown key / broken link / missing field tolerate 모드.

## §13 OKF-Compatible Wiki Page (스키마 가교)  {#s13-bridge}

우리 wiki 가 OKF consumer 에 노출될 때의 권장 가교 frontmatter:

```yaml
---
# wiki native (우리 schema, 5 lint 가 검증)
type: concept
status: active
last_ingested_from: <path>
related_pages: [<path>, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
r9_skip: <bool>

# OKF compatible (OKF consumer 가 tolerate)
title: <string>
description: <string>
resource: <URL>
tags: [<string>, ...]
timestamp: <ISO 8601 datetime>   # = updated 와 동일 값
---
```

규칙:
- OKF required (`type`) 와 우리 required (`type`) 동일 key → 충족
- OKF 의 unknown-key tolerate 정책이 우리 추가 필드 (`status`, `created`, `related_pages`, `last_ingested_from`, `r9_skip`) 허용
- 우리 R9 / R4 / V-1~V-8 lint 는 wiki side 에서만 enforce

## §14 Verification Trail  {#s14-trail}

| Step | Date | Result | Source |
|---|---|---|---|
| 1. Initial search | 2026-06-16 | grounding redirect 5/5 일관, 1차 출처 부재로 보임 | web_search (3 queries) |
| 2. Draft wiki page | 2026-06-16 | status=draft, [INFERENCE] marking, C-OKF-1 flag | local |
| 3. Direct repo fetch | 2026-06-16 | **`okf/SPEC.md` 457 lines 존재 확인** (raw.githubusercontent.com) | primary source |
| 4. Direct subdir README | 2026-06-16 | "This repository is primarily about the Open Knowledge Format (OKF)" 명시 | primary source |
| 5. Re-verify claims | 2026-06-16 | 모든 §1-§11 의 structural claim primary source 와 일치 | primary source |
| 6. C-OKF-1 close | 2026-06-16 | resolved → status=draft→active, [INFERENCE] 제거, verification_status=VERIFIED | this page |

## §15 Related  {#s15-related}

- [wiki-source-rule-r9](../concepts/wiki-source-rule-r9.md) — R9 rule (`last_ingested_from`) 가 OKF 의 `resource` 와 의미 중복, export 시 매핑 필요
- [stage-gate-pattern](../concepts/stage-gate-pattern.md) — output stage 의 structured payload 와 OKF 의 frontmatter 권장 field 부분 정합
- [contract-v1-output-validation](../concepts/contract-v1-output-validation.md) — orchestrator-subagent contract 와 OKF 의 concept-level metadata 정합 검토
- [adr-001-3-layer-separation](../decisions/adr-001-3-layer-separation.md) — Source/Runtime/Project 3-layer 분리 정책과 OKF 의 source-vs-bundle 분리 비교
- [r4-anchor-index](../patterns/r4-anchor-index.md) — wiki anchor 기반 index 와 OKF reserved `index.md` 의 progressive disclosure 패턴 유사
- [wiki-stub-emit](../patterns/wiki-stub-emit.md) — wiki stub emit 패턴이 OKF 의 "minimal example bundle" (§Appendix A) 과 직접 매핑 가능
- [wiki-ingest-lifecycle](../topics/wiki-ingest-lifecycle.md) — ingest cycle 과 OKF 의 knowledge graph emergent model 정합 검토

## §16 References  {#s16-references}

### §16.1 Primary Source (1차 출처) [VERIFIED]

- **OKF SPEC.md v0.1 (Draft, 457 lines)**: <https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md>
- **Subdirectory README**: <https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf>
- **Repository root**: <https://github.com/GoogleCloudPlatform/knowledge-catalog> (Apache 2.0)
- **Publisher**: Google Cloud (`GoogleCloudPlatform` org, 2026-06-12)

### §16.2 Reference Implementation

- **Producer (enrichment_agent)**: ADK + Gemini + BigQuery, 2-pass (BQ + web crawl). `enrich --source bq --dataset <p>.<d> --web-seed-file <path> --out ./bundles/<name>`
- **Consumer (visualize)**: self-contained HTML (Cytoscape.js + marked.js), `visualize --bundle ./bundles/<name>`
- **Sample bundles**: `bundles/ga4/`, `bundles/stackoverflow/`, `bundles/crypto_bitcoin/` + matching `samples/<name>/` recipes

### §16.3 Secondary Sources (used for context, not authority)

- Flowtivity, the-decoder, searchenginejournal, medium, pytorch.kr 등 보도 매체 — 모두 Google Vertex AI Search 의 grounding redirect 결과 재서술. 1차 출처 아님.

### §16.4 Related Formats (context)

- OpenAPI (<https://spec.openapis.org/>) — API contract 표준
- Frictionless Data Package (<https://specs.frictionlessdata.io/>) — tabular data container
- Open Knowledge Foundation (<https://okfn.org/>) — 동일 약자 OKF 의 별개 단체, proprietary spec 없음

## §17 Revision Log  {#s17-revision-log}

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. 외부 grounding/AI search 결과 합성. 모든 structural claim `[INFERENCE]` + C-OKF-1 flag | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **C-OKF-1 RESOLVED**: `GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md` (457 lines) primary source 확인. 모든 `[INFERENCE]` 제거, status=draft→active, verification_status=VERIFIED, §0~§17 재구성. §8 conformance, §9 versioning, §7 citations, §11 reference impl + 3 sample bundle, §14 verification trail 추가. initial draft 의 §1-§6 structural claim 검증 완료. | Sisyphus (orchestrator) |

## See Also

- [concepts/wiki-source-rule-r9](../concepts/wiki-source-rule-r9)
- [concepts/stage-gate-pattern](../concepts/stage-gate-pattern)
- [concepts/contract-v1-output-validation](../concepts/contract-v1-output-validation)
- [decisions/adr-001-3-layer-separation](../decisions/adr-001-3-layer-separation)
- [patterns/r4-anchor-index](../patterns/r4-anchor-index)
- [topics/wiki-ingest-lifecycle](../topics/wiki-ingest-lifecycle)
- [patterns/wiki-stub-emit](../patterns/wiki-stub-emit)
