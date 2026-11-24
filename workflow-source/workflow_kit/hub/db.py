"""허브 SQLite — 연결 · 스키마 이관 · 백업 (hub_spec §3.1 · §3.4, 요구 R1.2~R1.4).

이관은 :data:`MIGRATIONS` 의 순서가 판이다. 판 n 을 적용하기 전에 DB 사본을
``<db>.pre-v<n>-<시각>`` 으로 남긴다. DB 판이 허브가 아는 최신보다 크면 열기를
거절한다 (``db_newer_than_hub``).

M-033 은 판 1 — 등록 · 콜사인 · task · 이력 표. M-034 는 판 2 — 지침 · 셋업 단계. handoff · 지침 · 위키 ·
로드맵 표는 그 마일스톤이 새 판으로 더한다 (이관 경로가 실제로 쓰이게).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
from collections.abc import Iterator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, SupportsIndex, overload

from workflow_kit.hub.errors import HubError

_V1 = """
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
"""


#: 판 2 (M-034) — 프로젝트 지침 판 · 부트스트랩 셋업 단계 (hub_spec §3.3 · §6.1 · §6.5).
_V2 = """
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
"""

#: 판 3 (M-035) — 결정 응답 · 로드맵 원문 (hub_spec §3.3).
_V3 = """
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
"""

#: 판 4 (M-035 WBS-35.1) — 콜사인별 handoff · 작업 기억 · compact 체크포인트 (hub_spec §3.3).
_V4 = """
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
"""

#: 판 5 (M-036 WBS-36.1) — 위키 페이지 · ingest 묶음 (hub_spec §3.3, 요구 R8.1 · R8.2).
#: ``index.md`` · ``log.md`` 는 저장하지 않는다 — 페이지와 ingest 에서 생성한다.
_V5 = """
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
"""

#: 판 6 (M-036 WBS-36.2) — memory_index entry (hub_spec §3.3, 요구 R8.1 · E5).
#: 위키 원격 읽기 설정은 ``project.settings_json`` 의 ``wiki_remote`` 칸이다 (표를 늘리지 않는다).
_V6 = """
CREATE TABLE memory_entry (
    project_id TEXT NOT NULL REFERENCES project(id),
    id TEXT NOT NULL,
    body_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, id)
);
"""

#: 판 7 (M-037 WBS-37.3) — 지침 제안 (hub_spec §3.3 · §6.5, 요구 R7.5 · R7.7 · D11).
_V7 = """
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
"""

#: 판 8 (M-038 WBS-38.1) — 1.x 전환 기록 (hub_spec §3.3 · §6.6, 요구 R14).
_V8 = """
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
"""

#: 판 9 (M-039 WBS-39.2) — 프로젝트 문서 (PURPOSE · PROJECT_PROFILE). 소유자 2026-11-21: 전환이 들이고,
#: 상태 요약(state.json v1)의 목적 · 프로젝트 칸이 여기서 나온다.
_V9 = """
CREATE TABLE project_doc (
    project_id TEXT NOT NULL REFERENCES project(id),
    name TEXT NOT NULL CHECK (name IN ('purpose', 'profile')),
    body_md TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, name)
);
"""

#: 판 10 (M-039 WBS-39.4) — 허브 간 이전 초대 코드 (소유자 2026-11-21: 대상 허브 일회용 초대 코드).
#: 허브 전역 표다 — 프로젝트 표로 파생되지 않도록 열 이름을 ``for_project`` 로 둔다 (``project_id`` 아님).
_V10 = """
CREATE TABLE hub_invite (
    code_hash TEXT PRIMARY KEY,
    for_project TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    note TEXT NOT NULL DEFAULT ''
);
"""

#: 판 11 (M-044, 2.1 오케스트레이션 — ``core/hub_orchestration_spec.md`` §3). 2.0 표는 건드리지 않는다 —
#: 배정은 ``task`` 칼럼이 아니라 ``assignment`` 표 (DO4). 허브 전역 표 ``relay_host`` 는 ``project_id`` 칼럼이 없다.
_V11 = """
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
"""

#: 판 12 (M-046) — 중계 초대 코드. 허브 간 이전 초대(``hub_invite``)와 **따로** 둔다 — 그 표의 조회는 종류를 가리지 않아,
#: 같은 표를 쓰면 중계 초대 코드로 프로젝트 들여오기가 열린다. 허브 전역 표라 열 이름을 ``for_project`` 로 둔다.
_V12 = """
CREATE TABLE relay_invite (
    code_hash TEXT PRIMARY KEY,
    for_project TEXT NOT NULL,
    owner_callsign TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    host_id TEXT NOT NULL DEFAULT ''
);
"""

#: 판 13 — project-scoped knowledge snapshots and auditable DCR lifecycle.
_V13 = """
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
"""

#: 판 14 (M-060) — client-reported harness intake and hub-admin-reviewed registry.
_V14 = """
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
"""

#: 판 15 (M-060) — web-admin harness review and human owner roster.
_V15 = """
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
"""

#: 판 순서 = 목록 순서. 판 n = ``MIGRATIONS[n-1]`` (SQL 스크립트).
#: ``executescript`` 는 열린 트랜잭션을 먼저 커밋하므로, 판 하나의 원자성은
#: 스크립트 **안의** ``BEGIN IMMEDIATE … COMMIT`` 으로 만든다 (:func:`_apply`).
MIGRATIONS: list[str] = [_V1, _V2, _V3, _V4, _V5, _V6, _V7, _V8, _V9, _V10, _V11, _V12, _V13, _V14, _V15]


def latest_version() -> int:
    return len(MIGRATIONS)


class _PGRow(tuple[Any, ...]):
    """Tuple-compatible row with SQLite Row-style name lookup."""

    _names: tuple[str, ...]

    def __new__(cls, values: tuple[Any, ...], names: tuple[str, ...]) -> _PGRow:
        row = super().__new__(cls, values)
        row._names = names
        return row

    @overload
    def __getitem__(self, key: str) -> Any: ...

    @overload
    def __getitem__(self, key: SupportsIndex) -> Any: ...

    @overload
    def __getitem__(self, key: slice) -> tuple[Any, ...]: ...

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            key = self._names.index(key)
        return super().__getitem__(key)

    def keys(self) -> tuple[str, ...]:
        return self._names


class _PGCursor:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self.rowcount = cursor.rowcount

    def _row(self, row: Any) -> _PGRow | None:
        if row is None:
            return None
        values = tuple(
            value.decode("utf-8") if isinstance(value, bytes) else value for value in row
        )
        return _PGRow(values, tuple(d.name for d in self._cursor.description or ()))

    def fetchone(self) -> _PGRow | None:
        return self._row(self._cursor.fetchone())

    def fetchall(self) -> list[_PGRow]:
        return [
            converted
            for row in self._cursor.fetchall()
            if (converted := self._row(row)) is not None
        ]

    def __iter__(self) -> Iterator[_PGRow]:
        for row in self._cursor:
            converted = self._row(row)
            if converted is not None:
                yield converted


class _PGConnection:
    dialect = "postgresql"

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    @staticmethod
    def _sql(sql: str) -> str:
        sql = sql.replace("BEGIN IMMEDIATE", "BEGIN")
        sql = re.sub(r"\browid\b", "ctid", sql, flags=re.I)
        ignored_insert = bool(re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", sql, re.I))
        sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.I)
        if ignored_insert:
            sql += " ON CONFLICT DO NOTHING"
        out, quote, i = [], None, 0
        while i < len(sql):
            ch = sql[i]
            if quote:
                out.append(ch)
                if ch == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        out.append(sql[i + 1])
                        i += 1
                    else:
                        quote = None
            elif ch in ("'", '"'):
                quote = ch
                out.append(ch)
            elif ch == "?":
                out.append("%s")
            else:
                out.append(ch)
            i += 1
        rendered = "".join(out)
        return re.sub(r"\bIS\s+NOT\s+%s", "IS DISTINCT FROM %s", rendered, flags=re.I)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _PGCursor:
        try:
            cur = self._conn.execute(self._sql(sql), params or ())
        except Exception as exc:
            if str(getattr(exc, "sqlstate", "")).startswith("23"):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        return _PGCursor(cur)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    @property
    def in_transaction(self) -> bool:
        return not self._conn.autocommit


def normalize_target(path: Path | str) -> str:
    raw = str(path)
    # pathlib collapses the `//` in URL-like strings; restore it for API callers
    # that already constructed a Path before handing the value to the hub.
    for scheme in ("postgresql", "postgres"):
        if raw.startswith(f"{scheme}:/") and not raw.startswith(f"{scheme}://"):
            return raw.replace(f"{scheme}:/", f"{scheme}://", 1)
    return raw


def is_postgres(path: Path | str) -> bool:
    return normalize_target(path).startswith(("postgres://", "postgresql://"))


def connect(path: Path | str) -> Any:
    """자동 커밋 연결 — 트랜잭션은 호출자가 ``BEGIN IMMEDIATE`` 로 연다."""
    if is_postgres(path):
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "PostgreSQL 허브에는 psycopg[binary]가 필요하다 — pip install 'workflow_kit[hub-postgres]'"
            ) from exc
        try:
            return _PGConnection(psycopg.connect(normalize_target(path), autocommit=True))
        except Exception as exc:
            raise HubError(
                503,
                "postgres_connection_failed",
                "PostgreSQL 연결에 실패했다 — URL 자격 증명은 숨겼다",
            ) from exc
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def schema_version(conn: Any) -> int:
    if isinstance(conn, _PGConnection):
        has_meta = conn.execute("SELECT to_regclass('public.meta') AS name").fetchone()
        if not has_meta or has_meta["name"] is None:
            return 0
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row["value"]) if row else 0
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row else 0


def backup(src: Path, out: Path) -> None:
    """돌고 있는 허브의 DB 도 일관되게 복사한다 (SQLite 온라인 백업, 요구 R1.4)."""
    if is_postgres(src):
        raise HubError(
            400,
            "postgres_backup_external",
            "PostgreSQL 백업은 서버 운영 도구(pg_dump 또는 managed snapshot)를 사용한다",
        )
    if out.exists():
        raise HubError(409, "backup_target_exists", f"백업 대상이 이미 있다: {out}")
    source = sqlite3.connect(str(src), timeout=10.0)
    try:
        target = sqlite3.connect(str(out))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def open_db(path: Path | str, *, now: datetime) -> list[Path]:
    """DB 를 최신 판으로 맞춘다. 만든 이관 전 사본 경로를 돌려준다."""
    if is_postgres(path):
        conn = connect(path)
        try:
            current = schema_version(conn)
        finally:
            conn.close()
        latest = latest_version()
        if current > latest:
            raise HubError(
                500,
                "db_newer_than_hub",
                f"DB 판 {current} 이 이 허브가 아는 최신 판 {latest} 보다 새롭다 — 허브를 올린다",
                {"db_version": current, "hub_version": latest},
            )
        for n in range(current + 1, latest + 1):
            _apply_postgres(normalize_target(path), n, now)
        return []
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        current = schema_version(conn)
    finally:
        conn.close()
    latest = latest_version()
    if current > latest:
        raise HubError(
            500,
            "db_newer_than_hub",
            f"DB 판 {current} 이 이 허브가 아는 최신 판 {latest} 보다 새롭다 — 허브를 올린다",
            {"db_version": current, "hub_version": latest},
        )
    copies: list[Path] = []
    for n in range(current + 1, latest + 1):
        if current > 0:  # 새 DB 는 사본이 필요 없다 — 지킬 데이터가 없다
            stamp = now.strftime("%Y%m%dT%H%M%SZ")
            copy = path.with_name(f"{path.name}.pre-v{n}-{stamp}")
            backup(path, copy)
            copies.append(copy)
        _apply(path, n, now)
    return copies


def copy_sqlite_to_postgres(
    source_path: Path, target_url: str, *, now: datetime
) -> dict[str, object]:
    """Copy a consistent, upgraded SQLite snapshot into an empty PostgreSQL hub."""
    if not is_postgres(target_url):
        raise ValueError("대상은 postgresql:// 또는 postgres:// URL이어야 한다")
    with tempfile.TemporaryDirectory(prefix="workflow-hub-import-") as tmp:
        snapshot_path = Path(tmp) / "snapshot.db"
        source = sqlite3.connect(
            f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True, timeout=10
        )
        try:
            snapshot = sqlite3.connect(snapshot_path)
            try:
                source.backup(snapshot)
            finally:
                snapshot.close()
        finally:
            source.close()
        # Upgrade only the temporary snapshot; the operator's source file stays read-only.
        open_db(snapshot_path, now=now)
        src = sqlite3.connect(f"file:{snapshot_path.as_posix()}?mode=ro", uri=True)
        src.row_factory = sqlite3.Row
        dst = connect(target_url)
        tables = [
            r[0]
            for r in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
            )
        ]
        try:
            target_tables = [
                r["table_name"]
                for r in dst.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
                    "AND table_type='BASE TABLE' AND table_name <> 'meta'"
                )
            ]
            for table in target_tables:
                count = dst.execute(f'SELECT count(*) AS n FROM "{table}"').fetchone()["n"]
                if count:
                    raise HubError(
                        409,
                        "postgres_target_not_empty",
                        "PostgreSQL 대상에 이미 데이터가 있다 — 빈 대상으로 다시 시도한다",
                        {"table": table},
                    )
            dst.execute("BEGIN")
            summary: dict[str, dict[str, object]] = {}
            for table in tables:
                cols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
                pk = [
                    r[1]
                    for r in sorted(
                        (r for r in src.execute(f'PRAGMA table_info("{table}")') if r[5]),
                        key=lambda r: r[5],
                    )
                ]
                order = pk or cols
                quoted_cols = ",".join('"' + c.replace('"', '""') + '"' for c in cols)
                sort = ",".join('"' + c.replace('"', '""') + '"' for c in order)
                insert = (
                    f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({",".join("?" for _ in cols)})'
                )
                if table == "meta":
                    insert += " ON CONFLICT(key) DO UPDATE SET value=excluded.value"
                source_rows = src.execute(f'SELECT {quoted_cols} FROM "{table}" ORDER BY {sort}')
                source_hash, source_count = hashlib.sha256(), 0
                for row in source_rows:
                    values = tuple(row)
                    dst.execute(insert, values)
                    source_hash.update(
                        json.dumps(
                            values, ensure_ascii=False, separators=(",", ":"), default=str
                        ).encode()
                    )
                    source_hash.update(b"\n")
                    source_count += 1
                target_hash, target_count = hashlib.sha256(), 0
                target_rows = dst.execute(f'SELECT {quoted_cols} FROM "{table}" ORDER BY {sort}')
                for row in target_rows:
                    target_hash.update(
                        json.dumps(
                            tuple(row), ensure_ascii=False, separators=(",", ":"), default=str
                        ).encode()
                    )
                    target_hash.update(b"\n")
                    target_count += 1
                if source_count != target_count or source_hash.digest() != target_hash.digest():
                    raise HubError(
                        500,
                        "postgres_import_mismatch",
                        "SQLite와 PostgreSQL 데이터 검증이 맞지 않는다 — 이관을 롤백한다",
                        {"table": table, "source_rows": source_count, "target_rows": target_count},
                    )
                summary[table] = {"rows": source_count, "sha256": source_hash.hexdigest()}
            dst.execute(
                "SELECT setval(pg_get_serial_sequence('public.event','seq'), COALESCE(MAX(seq),1), MAX(seq) IS NOT NULL) FROM event"
            )
            dst.execute("COMMIT")
            return {"status": "ok", "tables": summary, "source_retained": True}
        except Exception:
            try:
                dst.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            src.close()
            dst.close()


def _apply_postgres(url: str, n: int, now: datetime) -> None:
    conn = connect(url)
    try:
        conn.execute("BEGIN")
        conn.execute("SELECT pg_advisory_xact_lock(78192341)")
        locked_version = schema_version(conn)
        if locked_version >= n:
            conn.execute("COMMIT")
            return
        ddl = MIGRATIONS[n - 1]
        ddl = re.sub(
            r"INTEGER\s+PRIMARY KEY\s+AUTOINCREMENT",
            "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY",
            ddl,
            flags=re.I,
        )
        for statement in ddl.split(";"):
            if statement.strip():
                conn.execute(statement)
        meta = conn.execute("SELECT to_regclass('public.meta') AS name").fetchone()
        if not meta or meta["name"] is None:
            conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("schema_version", str(n)),
        )
        if n == 1:
            conn.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO NOTHING",
                ("created_at", now.isoformat()),
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _apply(path: Path, n: int, now: datetime) -> None:
    meta = (
        f"INSERT INTO meta (key, value) VALUES ('schema_version', {_quote(str(n))}) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value;\n"
    )
    if n == 1:
        meta += f"INSERT INTO meta (key, value) VALUES ('created_at', {_quote(now.isoformat())});\n"
    conn = connect(path)
    try:
        conn.executescript("BEGIN IMMEDIATE;\n" + MIGRATIONS[n - 1] + "\n" + meta + "COMMIT;\n")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
