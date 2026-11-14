"""
Resume projects in the candidate report: tech stack, dates and points
are returned per project, and each is linked to its GitHub repository
after an analysis. Also covers the column migration helper that adds the
new Project columns to existing databases.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect, text

from app import models
from app.database import SessionLocal, engine, ensure_columns
from app.services.auth import create_access_token

RECENT = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace("+00:00", "Z")


def _repo(name: str) -> dict:
    return {
        "name": name,
        "language": "Python",
        "is_fork": False,
        "stars": 0,
        "updated_at": RECENT,
        "url": f"https://github.com/octocat/{name}",
        "description": None,
        "topics": [],
        "homepage": None,
        "created_at": RECENT,
        "pushed_at": RECENT,
    }


def _setup(client, monkeypatch) -> tuple[models.User, int]:
    async def fake_repos(username: str):
        return [_repo("credit-card-fraud-detection"), _repo("DSA-assignment")]

    async def fake_inspect(owner: str, repo: str, pushed_at=None):
        return {"technologies": {"Python": ["12 Python files"]}, "signals": {}, "commit_count": 3}

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", fake_repos)
    monkeypatch.setattr("app.services.analysis.inspect_repo", fake_inspect)

    with SessionLocal() as db:
        user = models.User(google_sub="sub-proj", email="proj@thapar.edu", name="P", role="student")
        db.add(user)
        db.flush()
        candidate = models.Candidate(user_id=user.user_id, name="P", github_username="octocat")
        db.add(candidate)
        db.flush()
        db.add(models.Project(
            candidate_id=candidate.candidate_id,
            project_name="Credit Card Fraud Detection & Transaction Analytics",
            description="Built a fraud detection model.\nDesigned a MySQL database.",
            tech_stack="Python, Scikit-learn, MySQL",
            period="Jan 2025 - Apr 2025",
        ))
        db.add(models.Project(candidate_id=candidate.candidate_id, project_name="Portfolio Website"))
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user, candidate.candidate_id


def _headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def test_projects_come_back_structured(client, monkeypatch):
    user, candidate_id = _setup(client, monkeypatch)
    body = client.get(f"/api/candidates/{candidate_id}", headers=_headers(user)).json()

    fraud, website = body["projects"]
    assert fraud["project_name"] == "Credit Card Fraud Detection & Transaction Analytics"
    assert fraud["tech_stack"] == ["Python", "Scikit-learn", "MySQL"]
    assert fraud["period"] == "Jan 2025 - Apr 2025"
    assert fraud["bullets"] == ["Built a fraud detection model.", "Designed a MySQL database."]
    assert fraud["repo"] is None  # not analyzed yet
    assert website["tech_stack"] == [] and website["bullets"] == []


def test_projects_are_linked_to_repositories_after_analysis(client, monkeypatch):
    user, candidate_id = _setup(client, monkeypatch)
    body = client.post(f"/api/candidates/{candidate_id}/analyze", headers=_headers(user)).json()

    fraud, website = body["projects"]
    assert fraud["repo"] == {
        "name": "credit-card-fraud-detection",
        "url": "https://github.com/octocat/credit-card-fraud-detection",
    }
    assert website["repo"] is None


def test_ensure_columns_adds_missing_project_columns():
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE "projects" DROP COLUMN "period"'))

    assert ensure_columns(engine) == ["projects.period"]
    columns = {c["name"] for c in inspect(engine).get_columns("projects")}
    assert {"tech_stack", "period"} <= columns
    assert ensure_columns(engine) == []  # nothing left to add


def test_resume_found_in_uploads_after_project_folder_moved(tmp_path):
    from app.routers.candidates import resolve_resume_path

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "abc_resume.pdf").write_bytes(b"%PDF-1.4")
    old_path = str(tmp_path / "DevProof-before-move" / "uploads" / "abc_resume.pdf")

    assert resolve_resume_path(old_path, str(uploads)) == str(uploads / "abc_resume.pdf")
    assert resolve_resume_path(str(uploads / "abc_resume.pdf"), str(uploads)) == str(uploads / "abc_resume.pdf")
    assert resolve_resume_path(str(tmp_path / "x" / "missing.pdf"), str(uploads)) is None
    assert resolve_resume_path(None, str(uploads)) is None
