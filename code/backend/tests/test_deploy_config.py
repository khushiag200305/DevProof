"""Settings that matter when the app runs on a hosting platform."""
from app.database import normalize_database_url


def test_platform_database_urls_are_normalised():
    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg2://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
    assert normalize_database_url("postgresql+psycopg2://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"


def test_frontend_origins_come_from_the_environment(monkeypatch):
    from app.main import allowed_origins

    monkeypatch.setenv("FRONTEND_ORIGINS", "https://devproof.vercel.app/, https://other.example.com")
    origins = allowed_origins()
    assert "https://devproof.vercel.app" in origins and "https://other.example.com" in origins
    assert "http://localhost:5173" in origins
