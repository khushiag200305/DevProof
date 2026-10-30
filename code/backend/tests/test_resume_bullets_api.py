"""
Tests for POST /api/candidates/{id}/resume-bullets. GitHub is never
called - the analysis' GitHub functions are monkeypatched.
"""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token

RECENT = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat().replace("+00:00", "Z")

REPOS = [
    {
        "name": "shop-api",
        "language": "Python",
        "is_fork": False,
        "stars": 0,
        "updated_at": RECENT,
        "url": "https://github.com/octocat/shop-api",
        "description": "REST API for an online shop",
        "topics": [],
        "homepage": None,
        "created_at": "2026-03-02T10:00:00Z",
        "pushed_at": RECENT,
    },
]


def _make_user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name=email, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _make_candidate(user_id: int, skills: list[str]) -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=user_id, name="Aditi Sharma", github_username="octocat")
        db.add(candidate)
        db.flush()
        for name in skills:
            skill = db.query(models.Skill).filter_by(skill_name=name).first()
            if skill is None:
                skill = models.Skill(skill_name=name)
                db.add(skill)
                db.flush()
            db.add(models.CandidateSkill(candidate_id=candidate.candidate_id, skill_id=skill.skill_id))
        db.commit()
        return candidate.candidate_id


def _headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _fake_github(monkeypatch):
    async def fake_repos(username: str):
        return REPOS

    async def fake_inspect(owner: str, repo: str):
        return {
            "technologies": {
                "Docker": ["Dockerfile present"],
                "FastAPI": ["fastapi in requirements.txt"],
                "PostgreSQL": ["psycopg2 in requirements.txt"],
                "Python": ["12 Python files"],
            },
            "signals": {"has_tests": True, "has_ci": True, "has_compose": False, "source_files": 12},
            "commit_count": 25,
        }

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", fake_repos)
    monkeypatch.setattr("app.services.analysis.inspect_repo", fake_inspect)


def test_needs_an_analysis_first(client):
    student = _make_user("b1@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python"])
    response = client.post(
        f"/api/candidates/{candidate_id}/resume-bullets", json={}, headers=_headers(student)
    )
    assert response.status_code == 400
    assert "analysis first" in response.json()["detail"]


def test_bullets_after_analysis(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("b2@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python", "Docker"])
    client.post(f"/api/candidates/{candidate_id}/analyze", headers=_headers(student))

    response = client.post(
        f"/api/candidates/{candidate_id}/resume-bullets", json={}, headers=_headers(student)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_match"] is None
    project = body["projects"][0]
    assert project["title"] == "Shop API"
    texts = [b["text"] for b in project["bullets"]]
    assert texts[0].startswith("Built Shop API, REST API for an online shop using")
    assert "Wrote automated tests and set up continuous integration to run them on every change." in texts
    assert any("25 commits" in t for t in texts)


def test_bullets_tailored_to_a_job_description(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("b3@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python", "Docker", "React"])
    client.post(f"/api/candidates/{candidate_id}/analyze", headers=_headers(student))

    response = client.post(
        f"/api/candidates/{candidate_id}/resume-bullets",
        json={"job_description": "Backend intern: Python, React, PostgreSQL"},
        headers=_headers(student),
    )
    match = response.json()["job_match"]
    assert match["proven"] == ["Python"]
    assert match["claimed_only"] == ["React"]
    assert match["missing"] == ["PostgreSQL"]
    assert response.json()["projects"][0]["matched_skills"] == ["PostgreSQL", "Python"]


def test_other_students_cannot_see_bullets(client, monkeypatch):
    owner = _make_user("b4@thapar.edu", "student")
    other = _make_user("b5@thapar.edu", "student")
    candidate_id = _make_candidate(owner.user_id, ["Python"])
    response = client.post(
        f"/api/candidates/{candidate_id}/resume-bullets", json={}, headers=_headers(other)
    )
    assert response.status_code == 403
