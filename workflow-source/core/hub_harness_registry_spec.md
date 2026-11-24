# Hub Harness Intake and Registry Contract

Status: implementation contract (M-060/WBS-60.1)

## 1. Trust boundary

Client observations are untrusted submissions. A report never adds a supported harness,
changes project setup, or modifies the global registry. An authenticated human hub
administrator reviews and decides reports through the web Hub. Registration does not
imply setup support; only built-in adapters are currently setup-ready.

## 2. Lifecycle and provenance

`pending -> approved | rejected` is a one-way decision. Corrections use a new report and
an explicit registry revision. Every report stores project, callsign, client version,
submission time, normalized harness ID, bounded compatibility observations, and the
admin decision actor/time/note. Events are append-only. Reports are visible to their
submitting project; hub admin can review all reports in the web Hub. Approved registry
entries are readable by authenticated projects.

Human contacts are a separate hub-level registry. An administrator registers people
independently from harness reports, then assigns one or more active people to a harness
when approving its first registry entry. A later approved revision replaces the assigned
set. The registry response includes the assigned people. These records identify
stakeholders; they are not login accounts or authorization principals.

## 3. Client report schema

The report accepts only `harness_id`, `display_name`, `version`, `platforms`,
`mcp_transports`, `config_formats`, `entry_file_candidates`, `documentation_url`, and
`notes`. IDs use lowercase kebab-case. Lists have bounded cardinality and length. File
names are relative, normalized paths with no `..`, home directory, or drive prefix.
URLs must be HTTPS. Notes are short plain text. Unknown fields are rejected. Secrets are
scanned recursively before persistence. Raw config, environment, logs, executable paths,
and command lines are not accepted.

## 4. MCP tools

- `hub_harness_report`: callsign token; submit one pending report; deduplicate identical
  pending reports from the same project and harness ID.
- `hub_harness_report_list`: callsign token lists reports scoped to the caller's project.
- `hub_harness_registry_list`: callsign token reads published profiles; project tools
  receive no pending reports from other projects.
- No MCP tool can approve or reject a report. The agent only submits a report and can read
  its own project's report status.

The web Hub exposes admin-token-only `/api/harness-reports`, `/api/harness-people`, and
`/api/harness-registry` APIs. Approval is `POST /api/harness-reports/{id}/decision` and
requires one or more IDs from the separate active human registry. Shared web and project
callsign tokens cannot view the global queue, manage the people registry, or decide.

## 5. Setup integration

`hub_session_start(session.harness=...)` returns `hub.harness_support` with one of
`setup_supported`, `registered_metadata_only`, or `unknown`. For `unknown`, it names the
report tool and accepted fields. Built-in adapters remain unchanged; a metadata-only
registry entry does not make `hub_setup_plan` or `hub_guide_render` accept the harness.
The client-submitted profile is never executed.

## 6. Storage and migration

`harness_report` and versioned `harness_registry` records are followed by separate
`harness_person` and `harness_registry_person` tables. Registry rows reference the
approved report; people are independent records and the join table tracks assignment.
Project provenance remains on the report; registry visibility is hub-wide. SQLite and
PostgreSQL migrations must match.

## 7. Security and concurrency

Reject unknown fields, malformed identifiers, unsafe paths, non-HTTPS documentation URLs,
oversized lists/text, and secret-like values. Approval requires 1–20 distinct active
human record IDs. It updates the report, registry entry, and assigned people in one
transaction. A decision against a non-pending report returns a conflict. A failed
approval leaves report status, registry, and assignments unchanged.
