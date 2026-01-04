# DevOps Control Plane (Local)

A fully local DevOps platform with:

- FastAPI backend (JWT access + refresh, RBAC admin/user)
- PostgreSQL (SQLAlchemy ORM)
- React (Vite) frontend (Axios JWT interceptor + auto refresh)
- NGINX reverse proxy:
  - `/` → React UI
  - `/api/*` → Backend
- Docker Compose orchestration (postgres, backend, frontend, nginx)
- Default admin user:
  - username: `admin`
  - password: `admin123`

## Run
## Database migrations

Migrations are managed with **Alembic** and are applied automatically when the backend container starts.

 (Windows)

1. Install **Docker Desktop** and ensure it is running.
2. Double-click `run.bat` in the project root.

It will:
- build Docker images
- start containers
- open `http://localhost:9000`

## Run
## Database migrations

Migrations are managed with **Alembic** and are applied automatically when the backend container starts.

 (CLI)

```bash
docker compose up --build
```

Then open:

- http://localhost:9000

## Services

- NGINX: `localhost:9000`
- Backend (internal): `backend:8000`
- Frontend dev server (internal): `frontend:5173`
- PostgreSQL (internal): `postgres:5432`

## API

- `POST /api/auth/login` → `{ access_token, refresh_token, token_type }`
- `POST /api/auth/refresh` → `{ access_token, refresh_token, token_type }`
- `GET /api/auth/me`
- `GET /api/tools` (user/admin)
- `POST /api/tools` (admin)
- `PUT /api/tools/{id}` (admin)
- `DELETE /api/tools/{id}` (admin)
- Admin users:
  - `GET /api/admin/users`
  - `POST /api/admin/users`
  - `PUT /api/admin/users/{id}`
  - `DELETE /api/admin/users/{id}`

## Notes

- Database tables are auto-created on backend startup.
- Default admin is auto-seeded if missing.

## CI

GitHub Actions workflow builds backend/frontend Docker images on push/PR.

## Optional Kubernetes

See `k8s/` for example manifests (optional).


## Tool metadata

Tools support **category** + **tags**. Use the Tools page filters (category dropdown, tag filter, search), or call `GET /api/tools?category=...&tag=...&q=...`.


## Pagination

`GET /api/tools` supports `limit` + `offset` and returns `{ items, total, limit, offset }`. The UI includes Prev/Next pagination.


## Sorting

`GET /api/tools` supports `sort_by=name|category|created_at` and `sort_dir=asc|desc`.


## Multi-column sorting

Use `sort=category:asc,name:asc` (comma-separated). Backwards compatible: `sort_by` + `sort_dir` still work.


## UI sorting

The Tools page provides presets, a builder (primary/secondary/tertiary), and a **Clear sort** button to reset to `Created (newest)`.


## Strict sort validation

The backend validates `sort` strictly. Invalid fields/directions, duplicates, or >3 fields return HTTP 422.

## Drag-and-drop sort priority

On the Tools page, drag the sort badges to reorder priority (1/2/3).
