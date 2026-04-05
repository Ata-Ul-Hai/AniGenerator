"""SQLAlchemy engine and session factory.

Reads DATABASE_URL from environment:
  - Local dev:    sqlite:///./anigen.db
  - Production:   postgresql://anigen:password@localhost:5432/anigendb
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    url = settings.database_url

    connect_args: dict[str, object] = {}

    # SQLite needs check_same_thread=False for FastAPI's threading model
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif url.startswith("postgresql") and settings.database_ssl_mode:
        # Use DATABASE_SSL_MODE=require in production environments with managed Postgres.
        connect_args["sslmode"] = settings.database_ssl_mode

    return create_engine(url, connect_args=connect_args, echo=False, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Create all tables. Call once at startup."""
    from backend.db import models  # noqa: F401 — import so models register
    Base.metadata.create_all(bind=engine)