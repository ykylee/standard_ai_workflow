---
type: decision
status: accepted
adr_id: ADR-036
decided_at: 2026-11-24
alternatives_considered: [repo-only-search, hub-copy-without-provenance, dcr-as-chat-message, dcr-auto-accept]
related_pages: [decisions/adr-001-3-layer-separation, decisions/adr-004-wiki-layer, decisions/adr-033-workflow-hub, decisions/adr-035-go-runtime]
created: 2026-11-24
updated: 2026-11-24
r9_skip: true
---

# ADR-036: 프로젝트 지식과 결정의 Hub 공유

## Status

**Accepted** (2026-11-24, TASK-2026-11-24-main-002, M-059/WBS-59.2). Owner decisions D1~D3 are recorded in the task. Implementation follows M-059/WBS-59.3~59.4.

## Context

3.1 Hub supports project Wiki ingest/version/search/get, Memory Index reads, and Git-oriented Wiki export. Design/spec documents are spread across repository directories; accepted ADRs are Markdown pages and some have an additional architecture mirror. There is no unified catalog that consistently returns authority, commit/revision, lifecycle status, and relations. There is no first-class DCR lifecycle connecting a proposed change to a reviewed ADR outcome.

The existing architecture constrains this proposal: ADR-001 separates source, runtime state, and durable knowledge; ADR-004 makes Wiki Git-tracked; ADR-033 makes the Hub the shared project workflow surface and already stores versioned Wiki pages with export rather than direct repository writes.

## Decision

1. Extend the Hub project boundary with a knowledge catalog that searches repository design docs, project Wiki, Memory Index, DCR, and ADR while preserving source kind, authority, canonical ref, immutable revision/SHA, lifecycle status, and relations.
2. Use **hybrid authority**: repository design docs and accepted ADRs are Git canonical and Hub stores commit-pinned projections; Hub-native project Wiki and DCR records are Hub canonical and versioned. Export instructions are explicit and hash-bound.
3. Add DCR as a first-class change proposal with target revision, rationale, alternatives, impact, validation plan, author, reviewer, and append-only decision history. Project writers may propose; only an approved human owner may approve/reject.
4. DCR approval creates a new ADR and enters `approved_pending_export`. The ADR becomes accepted and the previous ADR superseded only after Git source sync verifies the committed new ADR at the expected path/hash. DCR never writes or pushes Git.
5. Keep knowledge visibility project-scoped. Cross-project search is not provided.
6. Implement identical semantics in Python and Go, with additive DB migrations, API/MCP/UI parity, and fixture-backed conflict/authorization checks.

## Owner decisions (2026-11-24)

- **D1 — hybrid**: Git design documents/accepted ADRs are Git canonical and Hub projections; Hub-native Wiki/DCR are Hub canonical.
- **D2 — new ADR**: accepted DCR creates a new ADR, with the prior ADR marked superseded after Git sync verifies the new record.
- **D3 — project-only**: knowledge access is limited to project callsigns.

## Alternatives

| Alternative | Reason not preferred |
|---|---|
| Git grep/search only | Does not provide Hub MCP sessions a unified catalog or DCR review workflow |
| Copy Markdown into Hub without source SHA/revision | Creates an unverifiable second copy and silent divergence |
| Use chat/task comments as DCR | Lacks a stable lifecycle, target base revision, reviewer authority, and durable decision relation |
| Let agents auto-accept or rewrite ADR | Removes the human decision boundary and makes accepted history unreliable |

## Consequences if accepted

- Hub schema and both implementations gain source catalog/revision and DCR/ADR relations.
- Search and UI return provenance instead of flattening distinct sources into unattributed snippets.
- Source sync, stale conflict handling, export, and authority visibility require operations guidance.
- Existing wiki pages, memory entries, tasks, and ADR Markdown remain readable; migration is additive.

## References

- [Concept](../../../docs/planning/project-knowledge-decisions-concept-2026-11.md)
- [Requirements](../../../docs/planning/project-knowledge-decisions-requirements-2026-11.md)
- [Proposed contract](../../../workflow-source/core/hub_knowledge_decisions_spec.md)
