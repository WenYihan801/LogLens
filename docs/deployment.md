# Deployment

## Local full mode

```bash
cp .env.example .env      # set POSTGRES_PASSWORD
docker compose up --build -d
open http://localhost:8080
```

| Service | Image | Host port | Notes |
|---|---|---|---|
| frontend | `nginx:1.27-alpine` + built SPA | 8080 | Proxies `/api` and `/health` to the backend |
| backend | `python:3.12-slim` | 127.0.0.1:8000 | Runs `alembic upgrade head` on start, non-root user |
| db | `postgres:16-alpine` | 127.0.0.1:5432 | Named volume `pgdata`; init script creates `loglens_test` |

`docker compose down` keeps data; `docker compose down -v` deletes the volume.

## Public read-only demo (FR-31 – FR-34)

Goal: recruiters and other developers can browse the product with synthetic data; nobody can upload or modify anything.

Preview it locally first:

```bash
make demo   # = docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build -d
```

### Suggested free-tier hosting (verify current terms before deploying)

Free plans, sleep policies and database retention change often — check the providers' current documentation before you rely on them.

**1. Database – managed PostgreSQL (e.g. Neon)**
Create a project and copy the connection string. Use the `postgresql+psycopg://` scheme and keep `sslmode=require`:
```
postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

**2. Seed the demo data once (from your Mac)**
```bash
cd backend
DATABASE_URL='postgresql+psycopg://…?sslmode=require' .venv/bin/alembic upgrade head
DATABASE_URL='postgresql+psycopg://…?sslmode=require' .venv/bin/python -m app.scripts.seed_samples --reset
```
Optionally create a second database role with `SELECT`-only privileges for the web service — then even a bug in the read-only guard could not write.

**3. Backend – Docker web service (e.g. Render)**
* Build from the repo root with `backend/Dockerfile` (context `.`).
* Environment:
  ```
  APP_ENV=demo
  DEMO_READ_ONLY=true
  DATABASE_URL=<managed postgres URL>
  CORS_ORIGINS=https://<your-frontend-domain>
  ```
* Health check path: `/health`.

**4. Frontend – static site**
* Root `frontend/`, build `npm ci && npm run build`, publish `dist/`.
* Set `VITE_API_BASE_URL=https://<your-backend-domain>` at build time.
* Add a rewrite `/* → /index.html` so client-side routes work on refresh.

Alternatively deploy the `frontend/Dockerfile` image and set `BACKEND_URL=https://<backend>` so Nginx proxies `/api` (then no CORS is needed).

### Pre-launch checklist (SRS §10.4)

- [ ] Only synthetic sample data in the demo database.
- [ ] `DEMO_READ_ONLY=true`; verify `curl -X POST https://<backend>/api/v1/datasets/samples/ssh-normal` → `403`.
- [ ] HTTPS on both domains (provided by the platform).
- [ ] `CORS_ORIGINS` is exactly the frontend origin.
- [ ] Database not publicly writable; credentials only in the platform's secret manager.
- [ ] `LOG_LEVEL=INFO` (no request bodies or secrets are logged).
- [ ] Dependencies updated (`pip list --outdated`, `npm outdated`).
- [ ] A local Docker one-command fallback is documented in the README in case the free tier sleeps.
