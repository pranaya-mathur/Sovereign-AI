"""Database configuration and session management."""

import os
import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)


# Database URL from environment or default to SQLite for development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./llm_observability.db",  # Development default
)

# For PostgreSQL in production:
# DATABASE_URL = "postgresql://user:password@localhost:5432/llm_observability"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    # CRITICAL FIX: Disable pool_pre_ping for SQLite (causes 2s delays on Windows)
    # pool_pre_ping=True,  # Only needed for PostgreSQL in production
    pool_size=5,  # Reduced for SQLite (was 20)
    max_overflow=5,  # Reduced for SQLite (was 10)
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session.
    
    Yields:
        Database session that is automatically closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Import here to ensure all models are loaded
    from persistence.models import Base
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")
