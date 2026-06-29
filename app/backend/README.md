# Backend — POC

FastAPI application covering the 5 user stories (US-01..US-05). Uses SQLite by default; the database is reset and reseeded on every startup for reproducible test execution.

## Structure

```
src/
  main.py          # app factory + lifespan (reseeds DB on startup)
  models.py        # SQLAlchemy models: User, ServiceRequest
  schemas.py       # Pydantic schemas (validation mirrors acceptance criteria)
  security.py      # JWT issuance/verification + bcrypt; lockout policy (US-01)
  database.py      # SQLAlchemy engine + SessionLocal (SQLite by default)
  deps.py          # FastAPI dependencies: get_db, get_current_user
  seed.py          # Deterministic seed: alice + bob + 6 requests
  routers/
    auth.py        # POST /api/auth/login, /register; GET /api/auth/me
    requests.py    # GET/POST /api/requests; POST /api/requests/{id}/cancel
tests/
  conftest.py      # Fixtures: client (fresh DB per test), auth_header()
  test_auth.py     # US-01, US-02
  test_requests.py # US-03, US-04, US-05
```

## Running

Via Docker (recommended):

```bash
docker compose up -d backend
```

Running the tests (inside the container):

```bash
docker compose run --rm backend python -m pytest tests/ -v
```

## Seed data

| Email | Password | Requests |
|---|---|---|
| alice@example.com | Senha123 | 4 (aberta, em_analise, finalizada, cancelada) |
| bob@example.com | Senha123 | 2 (aberta alta, em_analise baixa) |

## Business rules

| Rule | Story | Location |
|---|---|---|
| 5 consecutive failures → 60s lockout | US-01 | `security.py`, `routers/auth.py` |
| Name 3–80 chars; password ≥8 with letter+digit | US-02 | `schemas.py` |
| Title 5–100 chars; description 10–500 | US-03 | `schemas.py` |
| Default scope: own requests, newest first | US-04 | `routers/requests.py` |
| Only aberta/em_analise cancellable; owner only | US-05 | `routers/requests.py` |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/app.db` | SQLAlchemy connection URL |
| `JWT_SECRET` | `dev-secret-change-me` | JWT signing key — change in production |
| `JWT_EXPIRES_HOURS` | `8` | Token lifetime in hours |
| `RESET_DB_ON_STARTUP` | `1` | Set to `0` to preserve data across restarts |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
