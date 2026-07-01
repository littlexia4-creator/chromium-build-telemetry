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

    _d = {
        "ts": int(payload.get("ts") or time.time()),
        "user_email":         _to_str(payload.get("email") or payload.get("user_email")),
        "repo":               _to_str(payload.get("repo")),
        "branch":             _to_str(payload.get("branch")),
        "commit_sha":         _to_str(payload.get("commit_sha") or payload.get("commit")),
        "platform":           platform_val,
        "ncpu":               _to_int(payload.get("ncpu")),
        "ncpu_physical":      _to_int(payload.get("ncpu_physical")),
        "ninja_jobs":         _to_int(payload.get("ninja_jobs") or payload.get("NINJA_JOBS")),
        "build_type":         _to_str(payload.get("build_type")),
        "browser_type":       _to_str(payload.get("browser_type")
                                      or payload.get("UC_BUILD_PRODUCT_TYPE")),
        "cable_state":        ((_to_str(payload.get("cable_state")) or "").upper() or None),
        "exec_strategy":      _to_str(_first_non_none(payload.get("exec_strategy"), payload.get("RBE_exec_strategy"), payload.get("rbe_exec_strategy"))),
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
        "rbe_remote_executions": _to_int(_first_non_none(rbe.get("remote_executions"), payload.get("rbe_remote_executions"))),
        "rbe_local_executions": _to_int(_first_non_none(rbe.get("local_executions"), payload.get("rbe_local_executions"))),
        "rbe_total_actions":  _to_int(_first_non_none(rbe.get("total_actions"), payload.get("rbe_total_actions"))),
        "ccache_direct_hit":  _to_int(_first_non_none(cc.get("direct_hit"), payload.get("ccache_direct_hit"))),
        "ccache_preproc_hit": _to_int(_first_non_none(cc.get("preproc_hit"), payload.get("ccache_preproc_hit"))),
        "ccache_miss":        _to_int(_first_non_none(cc.get("miss"), payload.get("ccache_miss"))),
        "ccache_errors":      _to_int(_first_non_none(cc.get("errors"), cc.get("error"), payload.get("ccache_errors"))),
        "ccache_size_kib":    _to_int(_first_non_none(cc.get("size_kib"), payload.get("ccache_size_kib"))),
        "status":             _to_str(payload.get("status")),
        "ccache_maxsize":     _to_str(
            cc.get("CCACHE_MAXSIZE")
            or cc.get("maxsize")
            or cc.get("max_size")
            or payload.get("ccache_maxsize")
            or payload.get("ccache_max_size")
        ),
    }
    # Derive remote_executions when missing — covers older clients that
    # didn't compute the breakdown but did send rbe_total_actions. Local
    # executions are subtracted too so they aren't folded into remote.
    if _d.get("rbe_remote_executions") is None and _d.get("rbe_total_actions") is not None:
        _d["rbe_remote_executions"] = max(0,
            (_d.get("rbe_total_actions") or 0)
            - (_d.get("rbe_hits") or 0)
            - (_d.get("rbe_local_fallback") or 0)
            - (_d.get("rbe_local_executions") or 0))
    return _d


COLUMNS = [
    "ts", "user_email", "repo", "branch", "commit_sha",
    "platform", "os", "arch", "ncpu", "ncpu_physical", "ninja_jobs",
    "build_type", "browser_type", "target", "args",
    "output_dir", "chromium_src_dir",
    "start_ts", "end_ts", "total_time", "ninja_time", "exit_code",
    "reclient_enabled",
    "cable_state", "exec_strategy",
    "rbe_hits", "rbe_misses", "rbe_local_fallback", "rbe_total_actions",
    "rbe_remote_executions", "rbe_local_executions",
    "ccache_direct_hit", "ccache_preproc_hit", "ccache_miss", "ccache_errors", "ccache_size_kib",
    "ccache_maxsize",
]
