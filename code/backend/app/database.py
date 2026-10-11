"""
SQLAlchemy engine/session setup.

Uses PostgreSQL for local development, per the project's tech stack
decision (Section 2 of the proposal). The connection string is read from
DATABASE_URL so it's easy to point at a different local instance or a
throwaway CI database without touching code.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://devproof:devproof@localhost:5432/devproof"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
