"""Aggregate queries for dashboard."""
from __future__ import annotations

import time
from .db import get_conn


def summary(days: int = 7) -> dict:
    since = int(time.time()) - days * 86400
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
              COUNT(*)                                              AS total,
              SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END)        AS success,
              SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END)   AS running,
              AVG(total_time)                                       AS avg_total,
              AVG(ninja_time)                                       AS avg_ninja,
              SUM(COALESCE(rbe_hits, 0))                            AS rbe_hits,
              SUM(COALESCE(rbe_misses, 0))                          AS rbe_misses,
              SUM(COALESCE(ccache_direct_hit, 0)
                  + COALESCE(ccache_preproc_hit, 0))                AS cc_hits,
              SUM(COALESCE(ccache_miss, 0))                         AS cc_miss
            FROM builds WHERE ts >= ?
        """, (since,)).fetchone()
    total = row["total"] or 0
    success = row["success"] or 0
    running = row["running"] or 0
    rbe_hits = row["rbe_hits"] or 0
    rbe_total = rbe_hits + (row["rbe_misses"] or 0)
    cc_hits = row["cc_hits"] or 0
    cc_total = cc_hits + (row["cc_miss"] or 0)
    return {
        "days": days,
        "total": total,
        "success": success,
        "fail": total - success - running,
        "running": running,
        "success_rate": round(success / total * 100, 2) if total else 0.0,
        "avg_total_time": round(row["avg_total"] or 0, 1),
        "avg_ninja_time": round(row["avg_ninja"] or 0, 1),
        "rbe_hit_rate":   round(rbe_hits / rbe_total * 100, 2) if rbe_total else 0.0,
        "ccache_hit_rate": round(cc_hits / cc_total * 100, 2) if cc_total else 0.0,
    }


def timeseries(days: int = 14) -> list[dict]:
    since = int(time.time()) - days * 86400
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
              date(ts, 'unixepoch', 'localtime')              AS day,
              COUNT(*)                                        AS total,
              SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END)  AS success,
              AVG(total_time)                                 AS avg_total
            FROM builds WHERE ts >= ?
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
              SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END)  AS success,
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
