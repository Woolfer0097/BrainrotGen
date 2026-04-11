"""Database connection and session management.

Sets up SQLAlchemy engine, session factory, and base class for models.
Provides SQLite-compatible configuration with multi-threading support.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

# SQLite requires check_same_thread=False for use with FastAPI's async workers
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
"""SQLAlchemy engine for database connections."""

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
"""Session factory for creating database sessions."""

Base = declarative_base()
"""Base class for SQLAlchemy ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for dependency injection.

    Yields:
        SQLAlchemy Session instance.

    Example:
        Used with FastAPI Depends:
        `def endpoint(db: Session = Depends(get_db))`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
