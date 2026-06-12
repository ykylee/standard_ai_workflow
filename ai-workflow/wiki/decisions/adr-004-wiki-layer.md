---
type: decision
status: accepted
decided_at: 2026-06-12
accepted_in: v0.6.0
alternatives_considered: [memory-replacement, federated-wiki, crdt, docs-wiki, source-wiki]
related_pages: [concepts/project-architecture, patterns/r4-anchor-index]
---

# ADR-004: LLM Wiki Layer 도입

## Status

Accepted (v0.6.0, P1 implemented). Full spec at [ADR-004 file](../../docs/architecture/ADR-004-llm-wiki-layer.md).

## Context

Karpathy LLM Wiki (2026-04 gist) analysis showed that `ai-workflow/memory/` was excellent for workflow state but lacked knowledge accumulation/synthesis/reuse capability. A separate layer was needed.

## Decision

`ai-workflow/wiki/` created as a parallel Runtime layer (ADR-001 §3). Git-tracked. Ingest-first + release-freeze model. 7 rules (R1~R7) from the distributed rules plan.

## Consequences

Positive: knowledge accumulates across sessions, ~70x token efficiency vs RAG (within 500KB), existing infra reusable (bootstrap_lib, contract_v1, 6 harness overlays).
Negative: new components needed (SCHEMA, lint, ingest skills), `.gitignore` carve-out required.

## Alternatives Rejected

| Option | Reason |
|---|---|
| memory/ 대체 (방향 B) | 11 skills + 6 harnesses redesign needed |
| Federated Wiki (Ward Cunningham) | federation discovery didn't scale |
| CRDT (Yjs, Automerge) | tombstone overhead + semantic conflict blind |
| `docs/wiki/` (Project Layer) | ADR-001 layer boundary violation |
| `workflow-source/wiki/` (Source Layer) | Source is for templates only, not runtime state |
