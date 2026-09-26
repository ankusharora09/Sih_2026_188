"""Database connection and session handling.

Creates the SQLAlchemy engine based on the ``DATABASE_URL`` setting and provides a
dependency ``get_db`` that yields a session for FastAPI routes.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..config import settings

# The engine is created lazily; echo is disabled for production‑like runs.
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a SQLAlchemy session and ensures it is
    closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
