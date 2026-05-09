#!/usr/bin/env bash
# Rebuild + restart the build-telemetry service.
# Usage: ./restart.sh [--no-build] [--logs]
#   --no-build : skip docker image rebuild (just restart)
#   --logs     : tail container logs after restart
set -euo pipefail

cd "$(dirname "$0")"

NO_BUILD=0
TAIL_LOGS=0
for a in "$@"; do
  case "$a" in
    --no-build) NO_BUILD=1 ;;
    --logs)     TAIL_LOGS=1 ;;
    -h|--help)
      sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done

if [[ $NO_BUILD -eq 1 ]]; then
  echo ">> docker compose restart"
  docker compose restart
else
  echo ">> docker compose up -d --build"
  docker compose up -d --build
fi

echo
echo ">> status"
docker ps --filter name=build-telemetry --format "{{.Names}} | {{.Status}} | {{.Ports}}"

echo
echo ">> health"
for i in 1 2 3 4 5; do
  if curl -sS --max-time 2 http://localhost:8080/api/health 2>/dev/null | grep -q '"ok":true'; then
    echo "ok"; break
  fi
  sleep 1
  [[ $i -eq 5 ]] && { echo "WARN: health check failed after 5s"; exit 1; }
done

if [[ $TAIL_LOGS -eq 1 ]]; then
  echo
  echo ">> logs (Ctrl-C to detach)"
  docker logs -f build-telemetry
fi
