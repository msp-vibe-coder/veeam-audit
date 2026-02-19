# CLAUDE.md

# Docker Deployment
docker_deploy.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Veeam/Wasabi backup audit web application. Monitors backup storage across Veeam BDR servers and Wasabi S3 buckets, detects anomalies, tracks costs, and generates Excel reports. Full-stack: React frontend, FastAPI backend, PostgreSQL database, with a data pipeline that ingests CSVs from Wasabi S3.

## Commands

### Docker (primary way to run)
```bash
docker compose up --build          # Start all services (db, api, frontend)
docker compose down                # Stop all services
docker compose up db               # Start only PostgreSQL
```

### Frontend (local dev)
```bash
cd frontend
npm install
npm run dev                        # Vite dev server on :5173, proxies /api to :8000
npm run build                      # Production build (tsc + vite)
npx tsc --noEmit                   # Type check only
```

### Backend (local dev)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
alembic upgrade head               # Run migrations
alembic revision --autogenerate -m "description"  # Create new migration
```

### Data Pipeline
```bash
pip install -r scripts/requirements.txt  # pandas, boto3, requests, psycopg2, dotenv
python scripts/pipeline.py --verbose     # Full pipeline (download + process + store)
python scripts/pipeline.py --skip-download  # Process only (skip S3 download)
python scripts/process_and_store.py --date 2026-01-28  # Process specific date
python scripts/migrate_from_sqlite.py --dry-run  # Preview SQLite migration
```

## Architecture

### Stack
- **Frontend**: React 19, TypeScript 5.7 (strict), Vite 6, Tailwind CSS 3 (dark mode default), Recharts, Axios
- **Backend**: FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, Alembic migrations
- **Database**: PostgreSQL 16 with JSONB for settings
- **Infrastructure**: Docker Compose, nginx (SPA routing + API proxy)

### Backend Structure
All API endpoints live under `/api/v1`. Seven routers in `backend/app/routers/` map 1:1 to frontend pages: `dashboard`, `sites`, `trends`, `issues`, `reports`, `settings`, `pipeline`.

**Data flow**: Router → `get_db()` dependency → SQLAlchemy query → Pydantic schema → JSON response.

Models in `backend/app/models/` use `DeclarativeBase`. Schemas in `backend/app/schemas/schemas.py` use `ConfigDict(from_attributes=True)` for ORM compatibility. Output schemas are suffixed with `Out` (e.g., `SiteMetricOut`).

The 8 models track time-series data keyed by `report_date`:
- `DailySummary` (PK: report_date) — aggregate daily KPIs
- `SiteMetric` (unique: report_date + site_code) — per-site storage and job metrics
- `BdrMetric` (unique: report_date + bdr_server) — BDR disk capacity
- `BucketMetric` (unique: report_date + bucket_name) — Wasabi bucket costs
- `Anomaly` — detected issues with severity levels
- `Setting` — JSONB key-value config store
- `PipelineRun` — pipeline execution history
- `GeneratedReport` — Excel report file tracking

### Frontend Structure
Path alias `@` maps to `src/`. Pages in `src/pages/` correspond to routes defined in `App.tsx`. The `useApi<T>` hook (`src/hooks/useApi.ts`) handles all data fetching with loading/error/data states. API functions in `src/lib/api.ts` are typed to interfaces in `src/types/index.ts`.

Reusable components: `DataTable` (generic sortable table), `KpiCard`, `Badge` (severity colors), `Card`, `DateRangePicker`, `LoadingSpinner`. Chart components wrap Recharts.

Custom CSS classes `btn-primary`, `btn-secondary`, `input-field` are defined in `src/index.css` via `@layer components`.

### Data Pipeline
Pipeline scripts in `scripts/` run outside Docker (require separate `scripts/requirements.txt`). The orchestrator (`pipeline.py`) runs three steps sequentially: download Veeam CSVs from Wasabi S3, fetch bucket utilization via Wasabi Stats API, then `process_and_store.py` computes all metrics and writes directly to PostgreSQL (no Excel intermediary).

Site codes are extracted from BDR server names via regex (e.g., `AJC-BDR3` → `AJC`, `HBCCORPPS1BDR1` → `HBC`). Cost formula: `storage_tb * $6.99/TB * (1 + 6.85% tax)`. Thresholds are configurable via the Settings page/DB table.

### Deployment
The backend Dockerfile runs `alembic upgrade head` before starting uvicorn. The frontend Dockerfile is a multi-stage build (Node build → nginx serve). In Docker Compose, the frontend container maps port 3000→80 (nginx). The frontend nginx proxies `/api/` to the backend service.

## Production Server

**Host**: `10.69.69.10` (ptscorpvs0wapp01)
**SSH user**: `wapp01admin`
**App URL**: `https://ptswebapps/veeam-audit/`
**App directory**: `/home/wapp01admin/apps/veeam-audit/`

### Docker containers
- `veeam-audit` — frontend (nginx, port 80 internal, behind Traefik)
- `veeam-audit-api` — backend (FastAPI/uvicorn)
- `veeam-audit-db` — PostgreSQL 16 (port 5432 internal, not exposed to host)

### Database access
PostgreSQL is only accessible inside the Docker network. Two ways to connect:

**From the server (exec into container):**
```bash
ssh wapp01admin@10.69.69.10 "docker exec veeam-audit-db psql -U veeam -d veeam_audit -c 'SELECT count(*) FROM daily_summaries;'"
```

**From this dev machine (SSH tunnel):**
```bash
# 1. Get the DB container's internal IP
ssh wapp01admin@10.69.69.10 "docker inspect veeam-audit-db --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'"
# Returns something like 172.19.0.2

# 2. Create SSH tunnel (replace IP if it changed)
ssh -f -N -L 5432:172.19.0.2:5432 wapp01admin@10.69.69.10

# 3. Connect locally via the tunnel
# DB password contains a literal backslash: V33amAud1t#2026\!
# URL-encoded for DATABASE_URL: V33amAud1t%232026%5C%21
# Example DATABASE_URL for tunnel: postgresql://veeam:V33amAud1t%232026%5C%21@localhost:5432/veeam_audit
```

**Important**: The dev machine does NOT have Docker installed. To run pipeline scripts against the production DB, use the SSH tunnel approach and temporarily update `DATABASE_URL` in `.env`. Remember to restore it afterward.

### SSH output quirk
SSH output from the server doesn't display directly in Claude Code's bash tool. Redirect to a file and read it:
```bash
ssh wapp01admin@10.69.69.10 "some command" > C:/tmp_ssh.txt 2>&1
# Then use Read tool on C:\tmp_ssh.txt
```

## Key Conventions

- Backend models use `Numeric(12, 4)` for TB values, `Numeric(12, 2)` for costs
- All routers query the latest `report_date` by default using `func.max(Model.report_date)`
- Settings have hardcoded defaults in the settings router that are used when DB values are missing
- Frontend uses `lucide-react` for icons, `clsx` for conditional classes, `date-fns` for date formatting
- Dark mode is the default; toggled via class on `<html>` element, persisted in localStorage
- Environment variables are loaded from `.env` at project root (both backend and scripts use `python-dotenv`)
