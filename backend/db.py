import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "/data/builds.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# (column_name, type/default) — applied if missing on existing DBs.
MIGRATIONS = [
    ("started_ts",  "INTEGER"),
    ("finished_ts", "INTEGER"),
    ("status",      "TEXT DEFAULT 'finished'"),
]

# Indexes to create AFTER migrations (depend on possibly-new columns).
POST_MIGRATION_INDEXES = [
    ("idx_builds_status",     "status"),
    ("idx_builds_started_ts", "started_ts"),
]


def _existing_columns(conn) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(builds)").fetchall()}


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_PATH.read_text())

        cols = _existing_columns(conn)
        for name, decl in MIGRATIONS:
            if name not in cols:
                conn.execute(f"ALTER TABLE builds ADD COLUMN {name} {decl}")

        for idx_name, col in POST_MIGRATION_INDEXES:
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON builds({col})"
            )

        # Backfill status for rows inserted before the column existed.
        conn.execute(
            "UPDATE builds SET status='finished' WHERE status IS NULL"
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
    finally:
        conn.close()
