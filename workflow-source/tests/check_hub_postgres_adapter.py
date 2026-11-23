"""PostgreSQL SQL adaptation checks; SQLite remains the offline test backend."""

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workflow-source"))

from workflow_kit.hub import db  # noqa: E402


def main() -> int:
    url_path = Path("postgresql://user@localhost/hub")
    assert db.is_postgres(url_path)
    assert db.normalize_target(url_path) == "postgresql://user@localhost/hub"
    got = db._PGConnection._sql(
        "INSERT OR IGNORE INTO inbox_message(id, body) VALUES (?, '?') "
        "AND callsign IS NOT ? ORDER BY rowid"
    )
    want = (
        "INSERT INTO inbox_message(id, body) VALUES (%s, '?') "
        "AND callsign IS DISTINCT FROM %s ORDER BY ctid ON CONFLICT DO NOTHING"
    )
    assert got == want, (got, want)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hub.db"
        db.open_db(path, now=datetime(2026, 11, 23, tzinfo=timezone.utc))
        conn = db.connect(path)
        assert db.schema_version(conn) == db.latest_version()
        conn.close()
    print("PostgreSQL SQL rewrite + SQLite default schema: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
