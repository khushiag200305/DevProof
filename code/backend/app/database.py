"""
SQLAlchemy engine/session setup.

Uses PostgreSQL for local development, per the project's tech stack
decision (Section 2 of the proposal). The connection string is read from
DATABASE_URL so it's easy to point at a different local instance or a
throwaway CI database without touching code.
"""
import os

from sqlalchemy import create_engine, inspect, text
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


# Columns added to existing tables after they were first created.
# Base.metadata.create_all() creates missing tables but never alters an
# existing one, so these are added here (until the project moves to Alembic).
ADDED_COLUMNS = {
    "projects": {"tech_stack": "TEXT", "period": "VARCHAR"},
    "users": {"visible_candidate_id": "INTEGER", "recruiter_status": "VARCHAR"},
}


def ensure_columns(bind=None) -> list[str]:
    """Add any ADDED_COLUMNS missing from existing tables. Returns what was added."""
    bind = bind or engine
    inspector = inspect(bind)
    added: list[str] = []
    with bind.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, sql_type in columns.items():
                if column not in existing:
                    conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}'))
                    added.append(f"{table}.{column}")
    return added
