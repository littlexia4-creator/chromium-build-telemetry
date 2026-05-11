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


def _first_non_none(*vals):
    """Return first value that is not None. Unlike , this preserves
    falsy-but-meaningful values like 0 and False."""
    for v in vals:
        if v is not None:
            return v
    return None


def extract_fields(payload: dict) -> dict:
    """Map ingest payload -> column dict. Tolerant of missing keys."""
    rbe = payload.get("rbe", {}) if isinstance(payload.get("rbe"), dict) else {}
    cc = payload.get("ccache", {}) if isinstance(payload.get("ccache"), dict) else {}

    os_val   = _to_str(payload.get("os"))
    arch_val = _to_str(payload.get("arch"))
    platform_val = _to_str(payload.get("platform"))
    if not platform_val and os_val and arch_val:
        platform_val = f"{os_val}-{arch_val}"

    return {
        "ts": int(payload.get("ts") or time.time()),
        "user_email":         _to_str(payload.get("email") or payload.get("user_email")),
        "repo":               _to_str(payload.get("repo")),
        "branch":             _to_str(payload.get("branch")),
        "commit_sha":         _to_str(payload.get("commit_sha") or payload.get("commit")),
        "platform":           platform_val,
        "ncpu":               _to_int(payload.get("ncpu")),
        "build_type":         _to_str(payload.get("build_type")),
        "target":             _to_str(payload.get("target") or payload.get("targets")),
        "args":               _to_str(payload.get("args")),
        "output_dir":         _to_str(
            payload.get("OUTPUT_DIR")
            or payload.get("output_dir")
            or payload.get("out_dir")
        ),
        "chromium_src_dir":   _to_str(
            payload.get("chromium_src_dir")
            or payload.get("src_dir")
            or payload.get("dir")          # legacy build.sh alias
        ),
        "os":                 os_val,
        "arch":               arch_val,
        "start_ts":           _to_str(payload.get("start")),
        "end_ts":             _to_str(payload.get("end")),
        "total_time":         _to_int(payload.get("total_time")),
        "ninja_time":         _to_int(_first_non_none(payload.get("ninja_total_time"), payload.get("ninja_time"))),
        "exit_code":          _to_int(payload.get("exit_code")),
        "reclient_enabled":   _bool_to_int(payload.get("reclient_enabled")),
        "rbe_hits":           _to_int(_first_non_none(rbe.get("hits"), payload.get("rbe_hits"))),
        "rbe_misses":         _to_int(_first_non_none(rbe.get("misses"), payload.get("rbe_misses"))),
        "rbe_local_fallback": _to_int(_first_non_none(rbe.get("local_fallback"), payload.get("rbe_local_fallback"))),
        "rbe_total_actions":  _to_int(_first_non_none(rbe.get("total_actions"), payload.get("rbe_total_actions"))),
        "ccache_direct_hit":  _to_int(_first_non_none(cc.get("direct_hit"), payload.get("ccache_direct_hit"))),
        "ccache_preproc_hit": _to_int(_first_non_none(cc.get("preproc_hit"), payload.get("ccache_preproc_hit"))),
        "ccache_miss":        _to_int(_first_non_none(cc.get("miss"), payload.get("ccache_miss"))),
        "ccache_size_kib":    _to_int(_first_non_none(cc.get("size_kib"), payload.get("ccache_size_kib"))),
        "ccache_maxsize":     _to_str(
            cc.get("CCACHE_MAXSIZE")
            or cc.get("maxsize")
            or cc.get("max_size")
            or payload.get("ccache_maxsize")
            or payload.get("ccache_max_size")
        ),
    }


COLUMNS = [
    "ts", "user_email", "repo", "branch", "commit_sha",
    "platform", "os", "arch", "ncpu",
    "build_type", "target", "args",
    "output_dir", "chromium_src_dir",
    "start_ts", "end_ts", "total_time", "ninja_time", "exit_code",
    "reclient_enabled",
    "rbe_hits", "rbe_misses", "rbe_local_fallback", "rbe_total_actions",
    "ccache_direct_hit", "ccache_preproc_hit", "ccache_miss", "ccache_size_kib",
    "ccache_maxsize",
]
