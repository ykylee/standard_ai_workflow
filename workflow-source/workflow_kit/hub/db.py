"""허브 SQLite — 연결 · 스키마 이관 · 백업 (hub_spec §3.1 · §3.4, 요구 R1.2~R1.4).

이관은 :data:`MIGRATIONS` 의 순서가 판이다. 판 n 을 적용하기 전에 DB 사본을
``<db>.pre-v<n>-<시각>`` 으로 남긴다. DB 판이 허브가 아는 최신보다 크면 열기를
거절한다 (``db_newer_than_hub``).

M-033 은 판 1 — 등록 · 콜사인 · task · 이력 표. M-034 는 판 2 — 지침 · 셋업 단계. handoff · 지침 · 위키 ·
로드맵 표는 그 마일스톤이 새 판으로 더한다 (이관 경로가 실제로 쓰이게).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
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

#: 판 순서 = 목록 순서. 판 n = ``MIGRATIONS[n-1]`` (SQL 스크립트).
#: ``executescript`` 는 열린 트랜잭션을 먼저 커밋하므로, 판 하나의 원자성은
#: 스크립트 **안의** ``BEGIN IMMEDIATE … COMMIT`` 으로 만든다 (:func:`_apply`).
MIGRATIONS: list[str] = [_V1, _V2, _V3, _V4, _V5, _V6, _V7, _V8, _V9, _V10, _V11, _V12]


def latest_version() -> int:
    return len(MIGRATIONS)


def connect(path: Path) -> sqlite3.Connection:
    """자동 커밋 연결 — 트랜잭션은 호출자가 ``BEGIN IMMEDIATE`` 로 연다."""
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row else 0


def backup(src: Path, out: Path) -> None:
    """돌고 있는 허브의 DB 도 일관되게 복사한다 (SQLite 온라인 백업, 요구 R1.4)."""
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


def open_db(path: Path, *, now: datetime) -> list[Path]:
    """DB 를 최신 판으로 맞춘다. 만든 이관 전 사본 경로를 돌려준다."""
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
            500, "db_newer_than_hub",
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
