CREATE TABLE IF NOT EXISTS builds (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                  INTEGER NOT NULL,
  user_email          TEXT,
  repo                TEXT,
  branch              TEXT,
  commit_sha          TEXT,
  platform            TEXT,
  ncpu                INTEGER,
  build_type          TEXT,
  target              TEXT,
  args                TEXT,
  output_dir          TEXT,
  start_ts            TEXT,
  end_ts              TEXT,
  total_time          INTEGER,
  ninja_time          INTEGER,
  exit_code           INTEGER,
  reclient_enabled    INTEGER,
  rbe_hits            INTEGER,
  rbe_misses          INTEGER,
  rbe_local_fallback  INTEGER,
  rbe_total_actions   INTEGER,
  ccache_direct_hit   INTEGER,
  ccache_preproc_hit  INTEGER,
  ccache_miss         INTEGER,
  ccache_size_kib     INTEGER,
  ccache_maxsize      TEXT,
  raw_json            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_builds_ts          ON builds(ts);
CREATE INDEX IF NOT EXISTS idx_builds_user        ON builds(user_email);
CREATE INDEX IF NOT EXISTS idx_builds_exit        ON builds(exit_code);
CREATE INDEX IF NOT EXISTS idx_builds_platform    ON builds(platform);
