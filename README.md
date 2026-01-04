# Control Ops (Local)

[![CI](https://github.com/Subash107/control-ops-local/actions/workflows/ci.yml/badge.svg)](https://github.com/Subash107/control-ops-local/actions/workflows/ci.yml)

A fully local DevOps platform that combines:

- FastAPI backend (JWT access + refresh, RBAC admin/user)
- PostgreSQL (SQLAlchemy ORM)
- React (Vite) frontend (Axios JWT interceptor + auto refresh)
- NGINX reverse proxy serving `/` for the UI and `/api/*` for the backend
- Docker Compose orchestration (postgres, backend, frontend, nginx)
- Default admin user (username: `admin`, password: `admin123`)

## Quick start

1. Copy `.env.example` to `.env` to enable the `COMPOSE_PROJECT_NAME=control-ops` prefix, then run `docker compose up --build` or double-click `run.bat` on Windows.
2. Open `http://localhost:9000` after the containers are healthy.

## Configuration checklist

Override the environment variables in `backend/app/core/config.py` before running services so the stack behaves predictably:

- `DATABASE_URL` *(required)* – the PostgreSQL/SQLAlchemy URL (e.g. `postgresql+psycopg2://devops:devops@postgres:5432/devops_cp`); used by Alembic, the backend engine, and scripts.
- `JWT_SECRET` – rotate from the default `change-me` to protect signed access/refresh tokens.
- `ACCESS_TOKEN_EXPIRES_MINUTES` / `REFRESH_TOKEN_EXPIRES_DAYS` – tune token lifetimes (defaults 15m / 7d) to suit your security profile.
- `CORS_ORIGINS` – comma-separated origins allowed by FastAPI’s middleware (default `http://localhost:9000`); include any hosted UIs or clients.
- `DEFAULT_ADMIN_USERNAME` / `DEFAULT_ADMIN_PASSWORD` – the seeded admin user only exists if missing, so override before first run to avoid known credentials.

Set these vars (or source a `.env` file) before running Docker Compose, Alembic, or `pytest`.

## Running locally

- `run.bat` (Windows) – builds images, runs migrations, and starts postgres, backend, frontend, and nginx.
- `docker compose up --build` – the cross-platform alternative that runs the same stack and auto-applies migrations.

## Testing & linting

- Backend: `DATABASE_URL=... JWT_SECRET=... pytest backend/tests` (requires access to a PostgreSQL instance).
- Frontend: `npm install` then `npm run lint` to verify ESLint rules and `npm run build` to check the production bundle.

## Services

- NGINX: `localhost:9000`
- Backend (internal): `backend:8000`
- Frontend dev server: `frontend:5173`
- PostgreSQL: `postgres:5432`

## API

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `GET /api/tools` (user/admin)
- `POST /api/tools`, `PUT /api/tools/{id}`, `DELETE /api/tools/{id}` (admin)
- `GET /api/admin/users`, `POST /api/admin/users`, `PUT /api/admin/users/{id}`, `DELETE /api/admin/users/{id}` (admin)

## Notes

- Database tables are auto-created on backend startup.
- Default admin is auto-seeded when missing.

## GitHub setup

1. **Branch protection** – Configure a rule on `main` requiring the CI workflow to pass before merging and disallow direct pushes. This keeps the `ci.yml` run status meaningful and protects the clean history you pushed.
2. **Releases** – Draft a release (e.g., `v1.0.0`) from the Releases tab or run `git tag v1.0.0 && git push --tags` to capture this stable snapshot.
3. **Badges & metadata** – Update the repo description/topics and keep the CI badge at the top of this README so contributors know how the project is verified.

Keeping these GitHub features in sync ensures any future work merges through the secured `main` branch with automated checks and a clean audit trail.
