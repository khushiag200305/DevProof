"""
Tests for the portfolio endpoints: owner-only publishing, the public page
(no login), and what the page contains after an analysis. GitHub is never
called - the analysis' GitHub functions are monkeypatched as in
test_analysis.py.
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
        "stars": 2,
        "updated_at": RECENT,
        "url": "https://github.com/octocat/shop-api",
        "description": "REST API for an online shop",
        "topics": ["fastapi"],
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
            "technologies": {"Docker": ["Dockerfile present"], "Python": ["12 Python files"]},
            "signals": {"has_tests": True, "has_ci": False, "source_files": 12},
            "commit_count": 21,
        }

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", fake_repos)
    monkeypatch.setattr("app.services.analysis.inspect_repo", fake_inspect)


def test_portfolio_is_private_until_the_owner_publishes(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("pf@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python", "Docker", "React"])
    client.post(f"/api/candidates/{candidate_id}/analyze", headers=_headers(student))

    settings = client.get(f"/api/candidates/{candidate_id}/portfolio", headers=_headers(student)).json()
    assert settings["is_public"] is False
    assert settings["slug"] is None

    published = client.put(
        f"/api/candidates/{candidate_id}/portfolio",
        json={"is_public": True, "headline": "  Backend developer  "},
        headers=_headers(student),
    )
    assert published.status_code == 200
    body = published.json()
    assert body["is_public"] is True
    assert body["headline"] == "Backend developer"
    slug = body["slug"]

    # Public page: no login needed.
    page = client.get(f"/api/portfolio/{slug}")
    assert page.status_code == 200
    data = page.json()
    assert data["name"] == "Aditi Sharma"
    assert data["headline"] == "Backend developer"
    shown = [s["name"] for g in data["skill_groups"] for s in g["skills"]]
    assert "Python" in shown and "Docker" in shown and "React" not in shown
    project = data["projects"][0]
    assert project["name"] == "shop-api"
    assert project["description"] == "REST API for an online shop"
    assert project["commit_count"] == 21
    assert "Automated tests" in project["highlights"]


def test_unpublishing_hides_the_page_but_keeps_the_link(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("pf2@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python"])
    url = f"/api/candidates/{candidate_id}/portfolio"

    slug = client.put(url, json={"is_public": True}, headers=_headers(student)).json()["slug"]
    client.put(url, json={"is_public": False}, headers=_headers(student))
    assert client.get(f"/api/portfolio/{slug}").status_code == 404

    again = client.put(url, json={"is_public": True}, headers=_headers(student)).json()
    assert again["slug"] == slug
    assert client.get(f"/api/portfolio/{slug}").status_code == 200


def test_only_the_owner_can_publish(client):
    owner = _make_user("own@thapar.edu", "student")
    other = _make_user("other@thapar.edu", "student")
    recruiter = _make_user("r@acme.com", "recruiter")
    candidate_id = _make_candidate(owner.user_id, ["Python"])
    url = f"/api/candidates/{candidate_id}/portfolio"

    assert client.put(url, json={"is_public": True}, headers=_headers(other)).status_code == 403
    assert client.put(url, json={"is_public": True}, headers=_headers(recruiter)).status_code == 403
    assert client.put(url, json={"is_public": True}).status_code == 401
    # A recruiter may still preview it.
    assert client.get(url, headers=_headers(recruiter)).status_code == 200


def test_unknown_portfolio_link_is_404(client):
    assert client.get("/api/portfolio/no-such-page-123abc").status_code == 404


def test_headline_length_is_limited(client):
    student = _make_user("long@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Python"])
    response = client.put(
        f"/api/candidates/{candidate_id}/portfolio",
        json={"is_public": True, "headline": "x" * 121},
        headers=_headers(student),
    )
    assert response.status_code == 422
