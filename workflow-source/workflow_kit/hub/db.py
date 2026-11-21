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

#: 판 순서 = 목록 순서. 판 n = ``MIGRATIONS[n-1]`` (SQL 스크립트).
#: ``executescript`` 는 열린 트랜잭션을 먼저 커밋하므로, 판 하나의 원자성은
#: 스크립트 **안의** ``BEGIN IMMEDIATE … COMMIT`` 으로 만든다 (:func:`_apply`).
MIGRATIONS: list[str] = [_V1, _V2, _V3]


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
