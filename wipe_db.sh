#!/usr/bin/env bash
# Wipe ALL telemetry data (SQLite DB) and restart the service.
#
# Usage:
#   ./wipe_db.sh            # interactive — asks for confirmation
#   ./wipe_db.sh --yes      # non-interactive (CI / scripted)
#   ./wipe_db.sh --backup   # snapshot DB to ./backups/ before deleting
#   ./wipe_db.sh --yes --backup
#
# Effect:
#   1. Optionally back up /data/builds.db to ./backups/builds-YYYYmmdd-HHMMSS.db
#   2. Remove /data/builds.db (and -wal, -shm)
#   3. Restart container — init_db() recreates empty schema + indexes
set -euo pipefail

cd "$(dirname "$0")"

CONTAINER="build-telemetry"
DB_PATH_IN_CONTAINER="/data/builds.db"

YES=0
DO_BACKUP=0
for a in "$@"; do
  case "$a" in
    --yes|-y)     YES=1 ;;
    --backup|-b)  DO_BACKUP=1 ;;
    -h|--help)    sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  echo "ERROR: cannot talk to docker daemon." >&2
  echo "  Either docker is down, or your user is not in the 'docker' group." >&2
  echo "  Fix: sudo usermod -aG docker \$USER && exec bash -l" >&2
  exit 1
fi
if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "ERROR: container '$CONTAINER' not found. Bring it up first:" >&2
  echo "  ./restart.sh" >&2
  exit 1
fi

echo ">> current row count:"
docker exec -i "$CONTAINER" python3 - <<'PY' 2>/dev/null || echo "  (count unavailable — DB may be empty)"
import sqlite3, os
p = os.environ.get("DB_PATH", "/data/builds.db")
if not os.path.exists(p):
    print("  (no DB file yet)")
else:
    c = sqlite3.connect(p)
    n = c.execute("SELECT COUNT(*) FROM builds").fetchone()[0]
    print(f"  {n} rows in builds")
PY

if [[ $YES -ne 1 ]]; then
  read -r -p ">> Wipe ALL telemetry rows? Type 'yes' to confirm: " ans
  [[ "$ans" == "yes" ]] || { echo "aborted"; exit 1; }
fi

if [[ $DO_BACKUP -eq 1 ]]; then
  mkdir -p backups
  ts="$(date +%Y%m%d-%H%M%S)"
  out="backups/builds-${ts}.db"
  echo ">> backup -> $out"
  docker cp "${CONTAINER}:${DB_PATH_IN_CONTAINER}" "$out" 2>/dev/null || {
    echo "  (no DB to back up — continuing)"
  }
fi

echo ">> remove DB files inside container"
docker exec "$CONTAINER" sh -c "rm -f ${DB_PATH_IN_CONTAINER} ${DB_PATH_IN_CONTAINER}-wal ${DB_PATH_IN_CONTAINER}-shm" || true

echo ">> restart container"
docker restart "$CONTAINER" >/dev/null

echo ">> wait for health"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS --max-time 2 http://localhost:8080/api/health 2>/dev/null | grep -q '"ok":true'; then
    echo "  ok"; break
  fi
  sleep 1
  [[ $i -eq 10 ]] && { echo "  WARN: health check timed out" >&2; exit 1; }
done

echo ">> verify empty"
curl -sS http://localhost:8080/api/stats/summary
echo
