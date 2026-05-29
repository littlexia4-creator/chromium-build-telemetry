import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", "/data/builds.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# (column_name, type/default) — applied if missing on existing DBs.
MIGRATIONS = [
    ("started_ts",       "INTEGER"),
    ("finished_ts",      "INTEGER"),
    ("status",           "TEXT DEFAULT 'finished'"),
    ("ccache_maxsize",   "TEXT"),
    ("chromium_src_dir", "TEXT"),
    ("os",               "TEXT"),
    ("arch",             "TEXT"),
    ("browser_type",     "TEXT"),
    ("rbe_remote_executions", "INTEGER"),
    ("rbe_local_failures",  "INTEGER"),
    ("ninja_jobs",           "INTEGER"),
    ("ccache_errors",        "INTEGER"),
]

# (old_col, new_col) — applied if old exists and new does not.
RENAMES = [
    ("ccache_max_size", "ccache_maxsize"),
    ("rbe_local_executions", "rbe_local_failures"),
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

        # 1. Renames (must run before ADD COLUMN so we don't end up with both
        #    old and new columns when an old DB already has the old name).
        for old, new in RENAMES:
            if old in cols and new not in cols:
                conn.execute(
                    f"ALTER TABLE builds RENAME COLUMN {old} TO {new}"
                )
                cols = _existing_columns(conn)

        # 2. Add missing columns.
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


ORPHAN_RUNNING_AGE_SECONDS = 2 * 3600

def sweep_orphan_running() -> int:
    """Mark stuck 'running' rows as 'cancelled' once they're older than
    ORPHAN_RUNNING_AGE_SECONDS. These rows come from builds where the
    /api/ingest call never reached the server (script killed before the
    sync POST flushed, network blip, etc.). Returns rowcount."""
    import time as _t
    cutoff = int(_t.time()) - ORPHAN_RUNNING_AGE_SECONDS
    with sqlite3.connect(DB_PATH, timeout=30, isolation_level=None) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        cur = conn.execute(
            "UPDATE builds SET status='cancelled', exit_code=NULL, "
            "finished_ts=COALESCE(finished_ts, ?) "
            "WHERE status='running' AND (started_ts IS NULL OR started_ts < ?)",
            (cutoff, cutoff),
        )
        return cur.rowcount


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


STALE_RUNNING_TIMEOUT_S = 24 * 60 * 60  # 24h


def sweep_stale_running() -> int:
    """Mark rows status='running' older than 24h as status='timeout'.

    Uses started_ts when present, falls back to ts. Returns # rows updated.
    """
    import time
    cutoff = int(time.time()) - STALE_RUNNING_TIMEOUT_S
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE builds SET status='timeout' "
            "WHERE status='running' AND started_ts IS NOT NULL AND started_ts < ?",
            (cutoff,),
        )
        return cur.rowcount
