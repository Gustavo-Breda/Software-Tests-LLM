"""FastAPI application entrypoint.

On startup we reset and reseed the database — fine for a PoC whose purpose
is reproducible test execution. Override via environment variables if needed
(see .env.example at the repo root).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import auth, requests as requests_router
from .seed import reset_and_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the data dir exists for SQLite file URLs
    db_url = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
    if db_url.startswith("sqlite:////"):
        data_dir = "/" + db_url.split("sqlite:////")[1].rsplit("/", 1)[0]
        os.makedirs(data_dir, exist_ok=True)
    if os.getenv("RESET_DB_ON_STARTUP", "1") == "1":
        reset_and_seed()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="QA Assistant PoC — API",
        version="0.1.0",
        description=(
            "Proof-of-concept API exposing the 5 user stories (US-01..US-05) "
            "consumed by the QA Assistant pipeline."
        ),
        lifespan=lifespan,
    )

    # CORS — Angular dev server (4200) and the dockerized nginx (8080)
    origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:4200,http://localhost:8080",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(requests_router.router)

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
