"""SQLite database setup. The database file is removed and recreated on startup
so the PoC starts in a deterministic state for tests (see seed.py)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
