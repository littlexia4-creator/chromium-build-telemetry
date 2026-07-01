from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import asyncio
from .db import init_db, get_conn, sweep_stale_running
from .extract import COLUMNS, extract_fields
from . import stats

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))

app = FastAPI(title="Chromium Build Telemetry", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    init_db()
    sweep_stale_running()
    asyncio.create_task(_periodic_sweep())


async def _periodic_sweep() -> None:
    # Mark rows still in status=running after 24h as status=timeout.
    # Loops forever, swallows any DB error so the task survives transient
    # contention.
    while True:
        try:
            sweep_stale_running()
        except Exception:
            pass
        await asyncio.sleep(3600)  # hourly


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


def _parse_body(raw: bytes) -> dict[str, Any]:
    try:
        payload: Any = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"invalid json: {exc}")
    if not isinstance(payload, dict):
        raise HTTPException(400, "payload must be object")
    return payload


@app.post("/api/start")
async def start_build(request: Request) -> dict:
    """Record a build kickoff. Returns {id} so client can pair on finish."""
    raw = await request.body()
    payload = _parse_body(raw)

    fields = extract_fields(payload)
    fields["started_ts"] = int(payload.get("ts") or time.time())
    fields["status"]     = "running"
    fields["raw_json"]   = raw.decode("utf-8", errors="replace")

    cols = COLUMNS + ["started_ts", "status", "raw_json"]
    placeholders = ",".join("?" for _ in cols)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO builds ({','.join(cols)}) VALUES ({placeholders})",
            [fields[c] for c in cols],
        )
        return {"id": cur.lastrowid}


@app.post("/api/ingest")
async def ingest(request: Request) -> dict:
    """Record finish stats. If `build_id` present, UPDATE that row; else INSERT new."""
    raw = await request.body()
    payload = _parse_body(raw)

    fields = extract_fields(payload)
    fields["finished_ts"] = int(time.time())
    _client_status = fields.get("status")
    # Status timeout is reserved for the 24h sweep on still-running rows; it
    # must NOT be set at ingest time, even for SIGINT/SIGTERM exit codes.
    # Ctrl+C builds land here with exit_code=130 and are classified finished
    # so the real exit_code stays visible.
    if _client_status and _client_status not in ("timeout", "cancelled"):
        fields["status"] = _client_status
    else:
        fields["status"] = "finished"
    fields["raw_json"]    = raw.decode("utf-8", errors="replace")

    bid = payload.get("build_id")
    if bid:
        try:
            bid_int = int(bid)
        except (TypeError, ValueError):
            raise HTTPException(400, "build_id must be int")
        # Only overwrite columns the client actually provided. Skip Nones so
        # earlier /api/start data (branch/platform/args/etc) is preserved.
        patch = {k: v for k, v in fields.items() if v is not None}
        if not patch:
            raise HTTPException(400, "no fields to update")
        sets = ",".join(f"{k}=?" for k in patch)
        with get_conn() as conn:
            cur = conn.execute(
                f"UPDATE builds SET {sets} WHERE id=?",
                list(patch.values()) + [bid_int],
            )
            if cur.rowcount == 0:
                raise HTTPException(404, f"build_id {bid_int} not found")
        return {"id": bid_int, "updated": True}

    cols = COLUMNS + ["finished_ts", "status", "raw_json"]
    placeholders = ",".join("?" for _ in cols)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO builds ({','.join(cols)}) VALUES ({placeholders})",
            [fields[c] for c in cols],
        )
        return {"id": cur.lastrowid, "updated": False}


@app.get("/api/builds")
def list_builds(
    limit: int = 100,
    offset: int = 0,
    user: str | None = None,
    platform: str | None = None,
    exit_code: int | None = None,
    status: str | None = None,
    since: int | None = None,
    kind: str | None = None,
) -> dict:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    where = []
    params: list[Any] = []
    if user:
        where.append("user_email = ?"); params.append(user)
    if platform:
        where.append("platform = ?"); params.append(platform)
    if exit_code is not None:
        where.append("exit_code = ?"); params.append(exit_code)
    if status:
        where.append("status = ?"); params.append(status)
    if since:
        where.append("ts >= ?"); params.append(since)
    if kind == "full":
        where.append(stats.FULL_BUILD_SQL)
    elif kind == "incremental":
        where.append(stats.INCREMENTAL_BUILD_SQL)
    sql_where = ("WHERE " + " AND ".join(where)) if where else ""

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM builds {sql_where}", params
        ).fetchone()["c"]
        rows = conn.execute(
            f"""SELECT id, ts, started_ts, finished_ts, status,
                       user_email, platform, build_type, browser_type, ninja_jobs, target,
                       total_time, ninja_time, exit_code, reclient_enabled,
                       cable_state, exec_strategy,
                       rbe_hits, rbe_misses, rbe_remote_executions,
                       rbe_local_fallback, rbe_local_executions,
                       ccache_direct_hit, ccache_preproc_hit, ccache_miss,
                       ccache_size_kib, ccache_maxsize
                FROM builds {sql_where}
                ORDER BY ts DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

    return {"total": total, "items": [dict(r) for r in rows]}


@app.get("/api/builds/{build_id}")
def get_build(build_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM builds WHERE id = ?", (build_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "not found")
    out = dict(row)
    try:
        out["raw"] = json.loads(out.pop("raw_json") or "{}")
    except json.JSONDecodeError:
        out["raw"] = {}
    return out


@app.get("/api/stats/summary")
def stats_summary(days: int = 30) -> dict:
    return stats.summary(days)


@app.get("/api/stats/timeseries")
def stats_timeseries(days: int = 14, kind: str | None = None) -> list[dict]:
    return stats.timeseries(days, kind=kind)


@app.get("/api/stats/by_user")
def stats_by_user(days: int = 14) -> list[dict]:
    return stats.by_user(days)


@app.get("/api/stats/by_platform")
def stats_by_platform(days: int = 14) -> list[dict]:
    return stats.by_platform(days)


@app.get("/api/stats/distinct")
def distinct_values() -> dict:
    with get_conn() as conn:
        users = [r["v"] for r in conn.execute(
            "SELECT DISTINCT user_email AS v FROM builds WHERE user_email IS NOT NULL ORDER BY v"
        )]
        plats = [r["v"] for r in conn.execute(
            "SELECT DISTINCT platform AS v FROM builds WHERE platform IS NOT NULL ORDER BY v"
        )]
    return {"users": users, "platforms": plats}


# SPA: serve built Vue assets + index fallback
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(404)
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(404)
