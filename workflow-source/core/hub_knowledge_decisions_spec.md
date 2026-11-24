# Hub Knowledge and Decisions Contract (draft)

- 문서 목적: 프로젝트 지식 카탈로그, 문서 provenance/version, DCR 및 ADR lifecycle의 저장·API·MCP·권한·충돌 계약을 정한다.
- 범위: 3.1 Hub Wiki/Memory Index를 확장하는 source sync와 decision workflow; Git 작업은 export instruction까지만 다룬다.
- 대상 독자: Python·Go hub 구현자, project owner, 검증자
- 상태: design contract accepted 2026-11-24 — TASK-2026-11-24-main-002, ADR-036; implementation WBS-59.3~59.4
- 최종 수정일: 2026-11-24
- 관련 문서: `../../docs/planning/project-knowledge-decisions-concept-2026-11.md`, `../../docs/planning/project-knowledge-decisions-requirements-2026-11.md`, `./hub_spec.md`, `./hub_go_spec.md`, `../../ai-workflow/wiki/decisions/adr-036-project-knowledge-decisions.md`

> D1~D3 are owner-approved. This contract is normative for implementation; any deviation requires a DCR.

## 1. Logical model proposal

| Record | Key data | Mutation policy |
|---|---|---|
| `knowledge_source` | project, id, kind, authority, remote key, allowlist, visibility, enabled, indexed SHA/status/time, version | project owner/admin; expected version; hub event |
| `knowledge_revision` | project/source/path, revision, commit SHA, content SHA-256, content MD, metadata JSON, indexed at | immutable snapshot; create on changed content |
| `decision_change` | DCR id, title, body, target refs/revisions, reason, alternatives, impact refs, validation, status, author, reviewer, decision | append-only decision/event; project writer creates; human owner decides |
| `decision_relation` | project, from ref, relation (`records`, `supersedes`, `superseded_by`, `affected_by`), to ref | immutable relation event, with current graph projection |

### 1.1 Accepted authority and visibility (D1, D3)

| Content | Authority | Hub representation | Default access |
|---|---|---|---|
| Repository design docs, requirements, specs, accepted ADRs | `git` | Immutable projection pinned to repository commit SHA and path | Project callsigns only |
| Project Wiki authored/managed in Hub | `hub` | Existing `wiki_page` version history and export instruction | Project callsigns only |
| DCR proposal and review history | `hub` | First-class project record and append-only events | Project callsigns only |
| Accepted ADR created by a DCR | `git` | Hub tracks approved pending publication and links the resulting Git projection after sync confirms the new ADR | Project callsigns only |
| Memory Index | `hub` project entry or imported source | Existing `memory_entry`, returned as `memory` kind rather than canonical design/decision | Project callsigns only |

No cross-project knowledge search is provided by the initial contract. `hub_wide` requires a separate owner decision and authorization contract.

Existing `wiki_page`, `wiki_ingest`, `memory_entry`, `event` remain readable. Migration must not reinterpret or delete their payloads. Logical merge/storage deduplication is deferred until source authority and DCR decisions are accepted.

## 2. Read API proposal

```text
hub_knowledge_sources() -> sources[]
hub_knowledge_sync(source_id, expected_version?, request_id?) -> sync report
hub_knowledge_search(query, kinds?, statuses?, source_ids?, task_id?, limit?) -> hits[]
hub_knowledge_get(ref, revision?) -> document + provenance + relations
hub_dcr_list(status?, target_ref?) -> DCR summaries
hub_dcr_get(id) -> DCR + timeline + linked ADRs
```

Each hit carries `ref`, `kind`, `title`, `status`, `authority`, `canonical_ref`, `revision`, `source_sha`, `content_sha256`, `updated_at`, `excerpt`, and `relations`. Results never cross the authorized project boundary. A Git source is read from its registered/approved remote identity and path allowlist at a pinned commit; sync cannot read an arbitrary local path or execute Git remote helpers.

## 3. DCR write proposal

```text
hub_dcr_create(target_refs, base_revisions, title, rationale, proposal, alternatives[], impacts[], validation_plan, request_id)
hub_dcr_update(id, expected_version, fields, request_id)
hub_dcr_decide(id, expected_version, outcome=accepted|rejected, rationale, adr_payload?, request_id)
hub_dcr_withdraw(id, expected_version, rationale, request_id)
hub_adr_export_plan(id) -> expected source SHA + path + content hash + write instructions
```

Normative transitions:

```text
draft → open → approved_pending_export | rejected
  └──────────→ withdrawn
approved_pending_export → accepted (after the new ADR is committed and source sync confirms path + SHA)
open + stale target revision → stale (requires rebase/reproposal before decision)
```

- `decide` requires an approved `human` project owner; web/admin generic access does not imply project decision authority.
- Owner approval creates a new ADR ID and a hash-bound export instruction; DCR enters `approved_pending_export`. It does not push or write Git.
- The ADR becomes `accepted` and the DCR becomes `accepted` only after a subsequent Git source sync confirms the new ADR path, expected base commit, and content hash. This preserves Git as the accepted ADR authority.
- The prior ADR's Git projection is marked `superseded` only after that confirming sync; history remains queryable by pinned revision.
- `rejected` retains proposal and decision rationale. `withdrawn` retains history. No terminal state is silently reopened; a changed proposal uses a new DCR or explicit revision flow.
- If target revision no longer matches `base_revisions`, decision returns 409 `stale_decision_base` without state mutation.

## 4. Authority and visibility proposal

| Source authority | Canonical bytes | Hub behavior | Git output |
|---|---|---|---|
| `git` | Repository path at commit SHA | Read snapshot, search index, revision history, source status | Hash-bound write instruction only |
| `hub` | Hub source record/page | Versioned Hub content, event trail, project access | Explicit export; commit SHA checked on re-sync |

Hub scopes source, revisions, search and DCR by `project_id`. Cross-project sharing is a future extension requiring separate authorization and data-retention decisions. `web` principal cannot decide a DCR or write canonical ADR content.

## 5. Search and session integration

- Search indexes only explicitly registered sources and does not read a working tree from a server-side path supplied by the caller.
- Search output includes canonical path/URL, commit SHA or Hub revision, status, and relation identifiers so a session can cite and re-read the same revision.
- Session start may accept `knowledge_refs[]` or a task relation and return a bounded list of relevant references. It does not inject whole source documents by default.
- Memory Index entries are labeled `memory`, never represented as a canonical design doc or accepted ADR.

## 6. Conflict, audit, and failure behavior

- Snapshot revisions are immutable. New content appends a revision; deletes create a tombstone rather than erase provenance.
- DCR writes are optimistic-concurrency checked with `expected_version` and idempotent by request ID.
- Each write and decision has an event in the same transaction. Decision events include actual principal identity and before/after states.
- Source fetch, parsing, indexing, and commit comparison failures produce an explicit failed/partial sync report. Existing indexed revision stays readable and is marked stale.
- Git export instructions include exact expected SHA and content hash. Consumers must refuse to apply if either no longer matches.

## 7. Proposed parity contract

Python and Go expose the same MCP tool schemas, HTTP JSON shapes, transitions, role checks, error codes, stale behavior, and SQL schema version. Python remains a contract reference until the owner approves any change to the current Go/Python shadow policy. The implementation plan must add conformance cases for two projects, two callsigns, web principal, owner/editor, conflict, replay, stale source, superseded ADR, and export mismatch.

## 8. Open design decisions

1. D1 accepted: hybrid authority as specified in §1.1.
2. D2 accepted: new ADR and `supersedes` relation; existing ADR is never edited in place by DCR acceptance.
3. D3 accepted: project-only visibility; cross-project search is excluded.
