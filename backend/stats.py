"""Aggregate queries for dashboard."""
from __future__ import annotations

import time
from .db import get_conn


def summary(days: int = 30) -> dict:
    since = int(time.time()) - days * 86400
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
              COUNT(*)                                              AS total,
              SUM(CASE WHEN exit_code = 0 AND COALESCE(status,'') != 'cancelled' THEN 1 ELSE 0 END) AS success,
              SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END)   AS running,
              SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
              AVG(total_time)                                       AS avg_total,
              AVG(ninja_time)                                       AS avg_ninja,
              AVG(CASE WHEN rbe_total_actions > 46000 THEN total_time END) AS avg_full,
              SUM(CASE WHEN rbe_total_actions > 46000
                       AND COALESCE(status,'') NOT IN ('cancelled','running')
                       THEN 1 ELSE 0 END)                       AS full_eligible,
              SUM(CASE WHEN rbe_total_actions > 46000
                       AND exit_code = 0
                       AND COALESCE(status,'') NOT IN ('cancelled','running')
                       THEN 1 ELSE 0 END)                       AS full_success,
              SUM(COALESCE(rbe_hits, 0))                            AS rbe_hits,
              SUM(COALESCE(rbe_misses, 0))                          AS rbe_misses,
              SUM(CASE WHEN rbe_total_actions > 46000
                       THEN COALESCE(rbe_hits, 0) ELSE 0 END)       AS full_rbe_hits,
              SUM(CASE WHEN rbe_total_actions > 46000
                       THEN COALESCE(rbe_misses, 0) ELSE 0 END)     AS full_rbe_misses,
              SUM(COALESCE(ccache_direct_hit, 0)
                  + COALESCE(ccache_preproc_hit, 0))                AS cc_hits,
              SUM(COALESCE(ccache_miss, 0))                         AS cc_miss,
              SUM(CASE WHEN rbe_total_actions > 46000
                       THEN COALESCE(ccache_direct_hit, 0)
                          + COALESCE(ccache_preproc_hit, 0)
                       ELSE 0 END)                                  AS full_cc_hits,
              SUM(CASE WHEN rbe_total_actions > 46000
                       THEN COALESCE(ccache_miss, 0) ELSE 0 END)    AS full_cc_miss
            FROM builds WHERE ts >= ?
        """, (since,)).fetchone()
    total = row["total"] or 0
    success = row["success"] or 0
    running = row["running"] or 0
    cancelled = row["cancelled"] or 0
    rbe_hits = row["rbe_hits"] or 0
    rbe_total = rbe_hits + (row["rbe_misses"] or 0)
    cc_hits = row["cc_hits"] or 0
    cc_total = cc_hits + (row["cc_miss"] or 0)
    return {
        "days": days,
        "total": total,
        "success": success,
        "fail": max(0, total - success - running - cancelled),
        "cancelled": cancelled,
        "running": running,
        "success_rate": round(success / max(1, total - cancelled - running) * 100, 2)
                          if (total - cancelled - running) > 0 else 0.0,
        "avg_total_time": round(row["avg_total"] or 0, 3),
        "avg_ninja_time": round(row["avg_ninja"] or 0, 3),
        "avg_full_build_time": round(row["avg_full"] or 0, 3) if row["avg_full"] is not None else None,
        "full_builds_success_rate": (
            round((row["full_success"] or 0) / row["full_eligible"] * 100, 2)
            if (row["full_eligible"] or 0) > 0 else 0.0
        ),
        "full_builds_failures": max(0, (row["full_eligible"] or 0) - (row["full_success"] or 0)),
        "rbe_hit_rate":   round(rbe_hits / rbe_total * 100, 2) if rbe_total else 0.0,
        "ccache_hit_rate": round(cc_hits / cc_total * 100, 2) if cc_total else 0.0,
        "full_rbe_hit_rate": (
            round((row["full_rbe_hits"] or 0) /
                  ((row["full_rbe_hits"] or 0) + (row["full_rbe_misses"] or 0)) * 100, 2)
            if ((row["full_rbe_hits"] or 0) + (row["full_rbe_misses"] or 0)) > 0 else 0.0
        ),
        "full_ccache_hit_rate": (
            round((row["full_cc_hits"] or 0) /
                  ((row["full_cc_hits"] or 0) + (row["full_cc_miss"] or 0)) * 100, 2)
            if ((row["full_cc_hits"] or 0) + (row["full_cc_miss"] or 0)) > 0 else 0.0
        ),
    }


FULL_BUILD_ACTIONS_THRESHOLD = 46000

def timeseries(days: int = 14, kind: str | None = None) -> list[dict]:
    since = int(time.time()) - days * 86400
    extra_where = ""
    if kind == "full":
        extra_where = f" AND rbe_total_actions > {FULL_BUILD_ACTIONS_THRESHOLD}"
    elif kind == "incremental":
        extra_where = (
            f" AND (rbe_total_actions IS NULL OR rbe_total_actions <= {FULL_BUILD_ACTIONS_THRESHOLD})"
        )
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT
              date(ts, 'unixepoch', 'localtime')              AS day,
              COUNT(*)                                        AS total,
              SUM(CASE WHEN exit_code = 0 AND COALESCE(status,'') != 'cancelled' THEN 1 ELSE 0 END) AS success,
              SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
              AVG(total_time)                                 AS avg_total
            FROM builds WHERE ts >= ?{extra_where}
            GROUP BY day ORDER BY day
        """, (since,)).fetchall()
    return [dict(r) for r in rows]


def by_user(days: int = 14) -> list[dict]:
    since = int(time.time()) - days * 86400
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
              COALESCE(user_email, 'unknown')                 AS user,
              COUNT(*)                                        AS total,
              SUM(CASE WHEN exit_code = 0 AND COALESCE(status,'') != 'cancelled' THEN 1 ELSE 0 END) AS success,
              SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
              AVG(total_time)                                 AS avg_total
            FROM builds WHERE ts >= ?
            GROUP BY user ORDER BY total DESC LIMIT 20
        """, (since,)).fetchall()
    return [dict(r) for r in rows]


def by_platform(days: int = 14) -> list[dict]:
    since = int(time.time()) - days * 86400
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
              COALESCE(platform, 'unknown') AS platform,
              COUNT(*) AS total
            FROM builds WHERE ts >= ?
            GROUP BY platform ORDER BY total DESC
        """, (since,)).fetchall()
    return [dict(r) for r in rows]
