import os

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from .seed import *
from .routers import auth, requests as requests_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
    if db_url.startswith("sqlite:////"):
        os.makedirs("/" + db_url.split("sqlite:////")[1].rsplit("/", 1)[0], exist_ok=True)
    if os.getenv("RESET_DB_ON_STARTUP", "1") == "1":
        reset_and_seed()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="QA Assistant PoC — API",
        version="0.1.0",
        description="Proof-of-concept API for US-01..US-05.",
        lifespan=lifespan,
    )

    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
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
