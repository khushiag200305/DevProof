"""
Shared pytest fixtures.

Integration tests (auth, candidates) run against a real PostgreSQL
instance - either the one started locally for dev, or the `postgres`
service container backend-ci.yml spins up - rather than mocking the DB
layer, since the whole point of this iteration is role-gated access
enforced through real queries. Each test gets a clean database via the
autouse `_clean_db` fixture, which truncates every table afterward.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    with SessionLocal() as db:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        db.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        db.commit()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
