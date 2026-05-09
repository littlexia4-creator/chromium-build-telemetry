# Chromium Build Telemetry

Self-hosted telemetry for chromium build. Collects per-build stats (duration,
exit code, reclient/ccache hit rate, target, args, platform) and serves a Vue
dashboard for browsing.

## Stack

- **Backend**: FastAPI + SQLite (single-file DB, WAL mode)
- **Frontend**: Vue 3 + Vite + Element Plus + ECharts
- **Packaging**: single multi-stage Docker image, served on port 8080

## Layout

```
telemetry/
├── backend/        FastAPI app
├── frontend/       Vue 3 SPA
├── Dockerfile      multi-stage
└── docker-compose.yml
```

## Local dev

```bash
# backend (in one terminal)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DB_PATH=./builds.db STATIC_DIR=./_skip uvicorn backend.app:app --reload --port 8080

# frontend (another terminal)
cd frontend
npm install && npm run dev
# open http://localhost:5173 (vite proxies /api -> :8080)
```

## Deploy

```bash
# on server
cd ~/build-telemetry
docker compose up -d --build
# dashboard: http://<host>:8080/
# ingest:    POST http://<host>:8080/api/ingest  (Content-Type: application/json)
```

## API

| Method | Path                          | Notes |
|--------|-------------------------------|-------|
| POST   | /api/ingest                   | accepts arbitrary JSON build record |
| GET    | /api/builds                   | list, supports `limit/offset/user/platform/exit_code/since` |
| GET    | /api/builds/{id}              | full record + raw payload |
| GET    | /api/stats/summary?days=7     | top-level cards |
| GET    | /api/stats/timeseries?days=14 | per-day counts |
| GET    | /api/stats/by_user?days=14    | top users |
| GET    | /api/stats/by_platform?days=14 | platform mix |
| GET    | /api/stats/distinct           | filter values |
| GET    | /api/health                   | liveness |

## Sample ingest payload

```json
{
  "ts": 1730983200,
  "email": "user@example.com",
  "repo": "ssh://gerrit/.../desktop",
  "branch": "main_144",
  "commit_sha": "abc1234",
  "platform": "linux-x64",
  "ncpu": 64,
  "build_type": "Debug",
  "target": "chrome",
  "args": "-d --reclient",
  "dir": "out/Debug",
  "start": "2026/05/08 10:00:00",
  "end":   "2026/05/08 10:23:11",
  "total_time": 1391,
  "ninja_total_time": 1305,
  "exit_code": 0,
  "reclient_enabled": true,
  "rbe": { "hits": 12000, "misses": 800, "local_fallback": 12, "total_actions": 12812 },
  "ccache": { "direct_hit": 8000, "preproc_hit": 200, "miss": 600, "size_kib": 64000000 }
}
```
