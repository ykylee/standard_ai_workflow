package db

// Code generated from workflow-source/workflow_kit/hub/db.py (DG5); check_go_assets_sync verifies exact byte parity.

const V1 = `
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE project (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    owner_callsign TEXT NOT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE project_alias (
    key TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id),
    kind TEXT NOT NULL CHECK (kind IN ('primary', 'alias')),
    added_by TEXT NOT NULL,
    added_at TEXT NOT NULL
);
CREATE TABLE callsign (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('human', 'agent')),
    human_approved INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor')),
    label TEXT NOT NULL DEFAULT '',
    host TEXT NOT NULL DEFAULT '',
    token_hash TEXT NOT NULL UNIQUE,
    guide_version_seen TEXT,
    client_version_seen TEXT,
    created_at TEXT NOT NULL,
    last_seen_at TEXT,
    revoked_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, id)
);
CREATE TABLE hub_token (
    token_hash TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('web', 'admin')),
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE task (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'in_progress', 'blocked', 'done')),
    priority TEXT NOT NULL DEFAULT 'high',
    assignee TEXT,
    branch TEXT NOT NULL DEFAULT '',
    wbs TEXT NOT NULL DEFAULT '',
    wbs_exempt_reason TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    plan_md TEXT NOT NULL DEFAULT '',
    fields_json TEXT NOT NULL DEFAULT '{}',
    progress_note TEXT NOT NULL DEFAULT '',
    progress_at TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, id)
);
CREATE TABLE task_seq (
    project_id TEXT NOT NULL,
    date TEXT NOT NULL,
    namespace TEXT NOT NULL,
    next INTEGER NOT NULL,
    PRIMARY KEY (project_id, date, namespace)
);
CREATE TABLE task_commit (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    sha TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT '',
    added_by TEXT NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (project_id, task_id, sha),
    FOREIGN KEY (project_id, task_id) REFERENCES task(project_id, id)
);
CREATE TABLE event (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT,
    at TEXT NOT NULL,
    callsign TEXT,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    op TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT,
    via TEXT NOT NULL,
    client_version TEXT
);
CREATE INDEX event_target ON event (project_id, target_kind, target_id);
CREATE TABLE applied_request (
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    request_id TEXT NOT NULL,
    result_json TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (project_id, callsign, request_id)
);
`

const V2 = `
CREATE TABLE guide (
    project_id TEXT NOT NULL REFERENCES project(id),
    version INTEGER NOT NULL,
    body_md TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, version)
);
CREATE TABLE setup_step (
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    step_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    guide_version TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('issued', 'confirmed', 'unconfirmed')),
    detail TEXT NOT NULL DEFAULT '',
    issued_at TEXT NOT NULL,
    confirmed_at TEXT,
    PRIMARY KEY (project_id, callsign, step_id),
    FOREIGN KEY (project_id, callsign) REFERENCES callsign(project_id, id)
);
ALTER TABLE callsign ADD COLUMN setup_complete INTEGER NOT NULL DEFAULT 0;
`

const V3 = `
CREATE TABLE plan_response (
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    body TEXT NOT NULL,
    body_sha256 TEXT NOT NULL,
    received_at TEXT NOT NULL,
    responder TEXT NOT NULL DEFAULT '',
    UNIQUE (project_id, body_sha256),
    FOREIGN KEY (project_id, task_id) REFERENCES task(project_id, id)
);
CREATE TABLE roadmap_doc (
    project_id TEXT NOT NULL REFERENCES project(id),
    path TEXT NOT NULL,
    body_md TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, path)
);
`

const V4 = `
CREATE TABLE handoff (
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    sections_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, callsign),
    FOREIGN KEY (project_id, callsign) REFERENCES callsign(project_id, id)
);
CREATE TABLE memory_note (
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('session', 'lesson', 'handoff_rollover', 'archive_1x')),
    title TEXT NOT NULL,
    body_md TEXT NOT NULL,
    meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE checkpoint (
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    created_at TEXT NOT NULL,
    body_json TEXT NOT NULL,
    summary_md TEXT NOT NULL DEFAULT ''
);
`

const V5 = `
CREATE TABLE wiki_page (
    project_id TEXT NOT NULL REFERENCES project(id),
    path TEXT NOT NULL,
    body_md TEXT NOT NULL,
    source_repo_key TEXT NOT NULL DEFAULT '',
    source_sha TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_ingest TEXT NOT NULL,
    PRIMARY KEY (project_id, path)
);
CREATE TABLE wiki_ingest (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    callsign TEXT NOT NULL,
    at TEXT NOT NULL,
    log_line TEXT NOT NULL,
    pages_json TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    UNIQUE (project_id, seq)
);
`

const V6 = `
CREATE TABLE memory_entry (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    body_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id)
);
`

const V7 = `
CREATE TABLE guide_proposal (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    base_version INTEGER NOT NULL,
    body_md TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    proposed_by TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'approved', 'rejected')),
    decided_by TEXT,
    decided_at TEXT,
    applied_version INTEGER,
    PRIMARY KEY (project_id, id)
);
`

const V8 = `
CREATE TABLE migration_1x (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    at TEXT NOT NULL,
    callsign TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'importing', 'done')),
    plan_json TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (project_id, id)
);
`

const V9 = `
CREATE TABLE project_doc (
    project_id TEXT NOT NULL REFERENCES project(id),
    name TEXT NOT NULL CHECK (name IN ('purpose', 'profile')),
    body_md TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, name)
);
`

const V10 = `
CREATE TABLE hub_invite (
    code_hash TEXT PRIMARY KEY,
    for_project TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    note TEXT NOT NULL DEFAULT ''
);
`

const V11 = `
CREATE TABLE session (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    harness TEXT NOT NULL DEFAULT '',
    harness_session_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'interactive' CHECK (kind IN ('interactive', 'worker')),
    allow_wait INTEGER NOT NULL DEFAULT 0,
    delivery_json TEXT NOT NULL DEFAULT '[]',
    guide_version TEXT NOT NULL DEFAULT '',
    host_id TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    last_signal_at TEXT NOT NULL,
    waiting_since TEXT,
    idle_waits INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, id)
);
CREATE UNIQUE INDEX session_harness_key ON session (project_id, callsign, harness, harness_session_id)
    WHERE harness_session_id != '';
CREATE TABLE inbox_message (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    to_kind TEXT NOT NULL CHECK (to_kind IN ('session', 'callsign')),
    to_id TEXT NOT NULL,
    from_callsign TEXT NOT NULL,
    from_session TEXT NOT NULL DEFAULT '',
    from_orchestrator INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL CHECK (kind IN ('assignment', 'note', 'release', 'report', 'approval')),
    body_json TEXT NOT NULL,
    ref_task TEXT NOT NULL DEFAULT '',
    ref_request TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'delivered', 'acked', 'declined', 'unacknowledged', 'expired')),
    delivered_via TEXT NOT NULL DEFAULT '',
    delivered_at TEXT,
    last_delivered_at TEXT,
    delivery_count INTEGER NOT NULL DEFAULT 0,
    acked_at TEXT,
    ack_by_session TEXT NOT NULL DEFAULT '',
    ack_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, id)
);
CREATE INDEX inbox_to ON inbox_message (project_id, to_kind, to_id, state);
CREATE TABLE assignment (
    project_id TEXT NOT NULL REFERENCES project(id),
    task_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    message_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('offered', 'accepted', 'declined', 'returned', 'reported')),
    return_reason TEXT NOT NULL DEFAULT '',
    offered_at TEXT NOT NULL,
    accepted_at TEXT,
    reported_at TEXT,
    report_json TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX assignment_open ON assignment (project_id, task_id) WHERE state IN ('offered', 'accepted');
CREATE TABLE orchestrator_lease (
    project_id TEXT PRIMARY KEY REFERENCES project(id),
    session_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    declared_by TEXT NOT NULL,
    declared_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    halted INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE session_request (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('spawn', 'stop')),
    host_id TEXT NOT NULL,
    target_json TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending_approval', 'approved', 'rejected', 'dispatched', 'done',
                                         'refused_by_host', 'failed')),
    decided_by TEXT NOT NULL DEFAULT '',
    decided_at TEXT,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (project_id, id)
);
CREATE TABLE relay_host (
    host_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    owner_callsign TEXT NOT NULL,
    projects_json TEXT NOT NULL DEFAULT '[]',
    allow_digest TEXT NOT NULL DEFAULT '',
    harnesses_json TEXT NOT NULL DEFAULT '[]',
    last_seen_at TEXT,
    revoked_at TEXT
);
CREATE TABLE orch_counter (
    project_id TEXT NOT NULL REFERENCES project(id),
    day TEXT NOT NULL,
    name TEXT NOT NULL,
    n INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, day, name)
);
`

const V12 = `
CREATE TABLE relay_invite (
    code_hash TEXT PRIMARY KEY,
    for_project TEXT NOT NULL,
    owner_callsign TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    host_id TEXT NOT NULL DEFAULT ''
);
`

const V13 = `
CREATE TABLE knowledge_source (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('git', 'hub_wiki')),
    authority TEXT NOT NULL CHECK (authority IN ('git', 'hub')),
    repo_key TEXT NOT NULL DEFAULT '',
    allowlist_json TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id),
    UNIQUE (project_id, repo_key)
);
CREATE TABLE knowledge_revision (
    project_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    path TEXT NOT NULL,
    revision INTEGER NOT NULL,
    commit_sha TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    title TEXT NOT NULL,
    body_md TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'tombstone')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, source_id, path, revision),
    FOREIGN KEY (project_id, source_id) REFERENCES knowledge_source(project_id, id)
);
CREATE INDEX knowledge_revision_lookup ON knowledge_revision(project_id, source_id, path, revision DESC);
CREATE TABLE wiki_page_revision (
    project_id TEXT NOT NULL,
    path TEXT NOT NULL,
    revision INTEGER NOT NULL,
    body_md TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'tombstone')),
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, path, revision),
    FOREIGN KEY (project_id) REFERENCES project(id)
);
INSERT INTO wiki_page_revision(project_id,path,revision,body_md,status,updated_by,updated_at)
SELECT project_id,path,version,body_md,'active',updated_by,updated_at FROM wiki_page;
CREATE TABLE decision_change (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    proposal_md TEXT NOT NULL,
    target_refs_json TEXT NOT NULL,
    base_revisions_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'approved_pending_export', 'accepted', 'rejected', 'withdrawn', 'stale')),
    version INTEGER NOT NULL DEFAULT 1,
    author TEXT NOT NULL,
    reviewer TEXT,
    decision_rationale TEXT,
    adr_path TEXT,
    adr_sha256 TEXT,
    supersedes_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id)
);
CREATE TABLE decision_event (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    dcr_id TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    op TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT,
    FOREIGN KEY (project_id, dcr_id) REFERENCES decision_change(project_id, id)
);
CREATE INDEX decision_event_target ON decision_event(project_id, dcr_id, seq);
`

// V14 is generated from workflow-source/workflow_kit/hub/db.py (M-060).
const V14 = `
CREATE TABLE harness_report (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id),
    harness_id TEXT NOT NULL,
    report_json TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    client_version TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT,
    decision_note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX harness_report_queue ON harness_report(status, submitted_at DESC);
CREATE INDEX harness_report_project ON harness_report(project_id, submitted_at DESC);
CREATE TABLE harness_registry (
    harness_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    source_report_id TEXT NOT NULL REFERENCES harness_report(id),
    version INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    registered_by TEXT NOT NULL,
    registered_at TEXT NOT NULL
);
`

// V15 is generated from workflow-source/workflow_kit/hub/db.py (M-060).
const V15 = `
CREATE TABLE harness_person (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE harness_registry_person (
    harness_id TEXT NOT NULL REFERENCES harness_registry(harness_id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES harness_person(id),
    assigned_by TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (harness_id, person_id)
);
`

// V16 is generated from workflow-source/workflow_kit/hub/db.py.
const V16 = `
CREATE TABLE hub_account (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE hub_account_callsign (
    account_id TEXT NOT NULL REFERENCES hub_account(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL,
    callsign TEXT NOT NULL,
    linked_at TEXT NOT NULL,
    PRIMARY KEY (account_id, project_id, callsign),
    UNIQUE (project_id, callsign),
    UNIQUE (account_id, project_id),
    FOREIGN KEY (project_id, callsign) REFERENCES callsign(project_id, id)
);
CREATE TABLE hub_account_session (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES hub_account(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX hub_account_session_account ON hub_account_session(account_id, expires_at);
CREATE TABLE hub_account_login_attempt (
    username_hash TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL,
    window_started_at TEXT NOT NULL,
    locked_until TEXT
);
`

// V17 is generated from workflow-source/workflow_kit/hub/db.py.
const V17 = `
CREATE TABLE approval_grant (
    id TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES project(id),
    action TEXT NOT NULL,
    params_json TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'approved', 'rejected', 'used')),
    decided_by TEXT,
    decided_account TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    expires_at TEXT,
    used_at TEXT,
    PRIMARY KEY (project_id, id)
);
`

var Migrations = []string{V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17}

func LatestVersion() int {
	return len(Migrations)
}
