"""Extract known fields from arbitrary build telemetry JSON."""
from __future__ import annotations

import time
from typing import Any


def _to_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _to_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v)
    return s if s else None


def _bool_to_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1 if v else 0
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return 1
    if s in ("false", "0", "no"):
        return 0
    return None


def extract_fields(payload: dict) -> dict:
    """Map ingest payload -> column dict. Tolerant of missing keys."""
    rbe = payload.get("rbe", {}) if isinstance(payload.get("rbe"), dict) else {}
    cc = payload.get("ccache", {}) if isinstance(payload.get("ccache"), dict) else {}

    return {
        "ts": int(payload.get("ts") or time.time()),
        "user_email":         _to_str(payload.get("email") or payload.get("user_email")),
        "repo":               _to_str(payload.get("repo")),
        "branch":             _to_str(payload.get("branch")),
        "commit_sha":         _to_str(payload.get("commit_sha") or payload.get("commit")),
        "platform":           _to_str(payload.get("platform")),
        "ncpu":               _to_int(payload.get("ncpu")),
        "build_type":         _to_str(payload.get("build_type")),
        "target":             _to_str(payload.get("target") or payload.get("targets")),
        "args":               _to_str(payload.get("args")),
        "output_dir":         _to_str(payload.get("dir") or payload.get("output_dir")),
        "start_ts":           _to_str(payload.get("start")),
        "end_ts":             _to_str(payload.get("end")),
        "total_time":         _to_int(payload.get("total_time")),
        "ninja_time":         _to_int(payload.get("ninja_total_time") or payload.get("ninja_time")),
        "exit_code":          _to_int(payload.get("exit_code")),
        "reclient_enabled":   _bool_to_int(payload.get("reclient_enabled")),
        "rbe_hits":           _to_int(rbe.get("hits") or payload.get("rbe_hits")),
        "rbe_misses":         _to_int(rbe.get("misses") or payload.get("rbe_misses")),
        "rbe_local_fallback": _to_int(rbe.get("local_fallback") or payload.get("rbe_local_fallback")),
        "rbe_total_actions":  _to_int(rbe.get("total_actions") or payload.get("rbe_total_actions")),
        "ccache_direct_hit":  _to_int(cc.get("direct_hit") or payload.get("ccache_direct_hit")),
        "ccache_preproc_hit": _to_int(cc.get("preproc_hit") or payload.get("ccache_preproc_hit")),
        "ccache_miss":        _to_int(cc.get("miss") or payload.get("ccache_miss")),
        "ccache_size_kib":    _to_int(cc.get("size_kib") or payload.get("ccache_size_kib")),
    }


COLUMNS = [
    "ts", "user_email", "repo", "branch", "commit_sha",
    "platform", "ncpu", "build_type", "target", "args", "output_dir",
    "start_ts", "end_ts", "total_time", "ninja_time", "exit_code",
    "reclient_enabled",
    "rbe_hits", "rbe_misses", "rbe_local_fallback", "rbe_total_actions",
    "ccache_direct_hit", "ccache_preproc_hit", "ccache_miss", "ccache_size_kib",
]
