"""
Tests for POST /api/candidates/{id}/analyze: runs the evidence engine for
a stored candidate and saves scores, evidence and interview questions.

GitHub is never called: the GitHub client and fingerprinting functions
used by app/services/analysis.py are monkeypatched with fixed data, so
the rest of the flow (access rules, scoring, persistence, response
shape) runs for real against the test database.
"""
from datetime import datetime, timedelta, timezone

import httpx

from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token

RECENT = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z")

FAKE_REPOS = [
    {
        "name": "shop-api",
        "language": "Python",
        "is_fork": False,
        "stars": 3,
        "updated_at": RECENT,
        "url": "https://github.com/octocat/shop-api",
    },
]

FAKE_FINGERPRINTS = {
    "shop-api": {
        "Docker": ["Dockerfile present"],
        "React": [],
        "Express": [],
        "Node.js": [],
        "Flask": [],
        "FastAPI": [],
        "Django": [],
    },
}


def _make_user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name=email, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _make_candidate(user_id: int, skills: list[str], github_username: str | None = "octocat") -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=user_id, name="Test Candidate", github_username=github_username)
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


def _auth_headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _fake_github(monkeypatch):
    async def fake_fetch_repos(username: str):
        return FAKE_REPOS

    async def fake_fingerprint(owner: str, repo: str):
        return FAKE_FINGERPRINTS[repo]

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", fake_fetch_repos)
    monkeypatch.setattr("app.services.analysis.fingerprint_repo", fake_fingerprint)


def _skill(body: dict, name: str) -> dict:
    return next(s for s in body["skills"] if s["skill_name"] == name)


def test_analyze_scores_and_saves_each_skill(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("s@thapar.edu", "student")
    recruiter = _make_user("r@acme.com", "recruiter")
    candidate_id = _make_candidate(student.user_id, ["Docker", "Python", "React"])

    response = client.post(f"/api/candidates/{candidate_id}/analyze", headers=_auth_headers(recruiter))

    assert response.status_code == 200
    body = response.json()
    assert body["analyzed"] is True
    assert body["repos_analyzed"] == 1

    docker = _skill(body, "Docker")
    assert docker["score"] == 80
    assert docker["status"] == "Strong Evidence"
    assert "shop-api: Dockerfile present" in docker["reasons"]
    assert docker["interview_question"] is None

    python = _skill(body, "Python")
    assert python["score"] == 60
    assert python["status"] == "Good Evidence"

    react = _skill(body, "React")
    assert react["score"] == 0
    assert react["status"] == "Needs Verification"
    assert react["interview_question"]

    # Saved, not just returned: a plain GET shows the same results.
    detail = client.get(f"/api/candidates/{candidate_id}", headers=_auth_headers(recruiter)).json()
    assert _skill(detail, "Docker")["score"] == 80
    assert _skill(detail, "React")["interview_question"] == react["interview_question"]


def test_reanalyzing_replaces_previous_results(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("s2@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Docker"])
    headers = _auth_headers(student)

    client.post(f"/api/candidates/{candidate_id}/analyze", headers=headers)
    client.post(f"/api/candidates/{candidate_id}/analyze", headers=headers)

    with SessionLocal() as db:
        assert db.query(models.Repository).filter_by(candidate_id=candidate_id).count() == 1
        assert db.query(models.Evidence).filter_by(candidate_id=candidate_id).count() == 3


def test_student_can_analyze_own_candidate_only(client, monkeypatch):
    _fake_github(monkeypatch)
    owner = _make_user("owner@thapar.edu", "student")
    other = _make_user("other@thapar.edu", "student")
    candidate_id = _make_candidate(owner.user_id, ["Docker"])

    assert client.post(f"/api/candidates/{candidate_id}/analyze", headers=_auth_headers(other)).status_code == 403
    assert client.post(f"/api/candidates/{candidate_id}/analyze", headers=_auth_headers(owner)).status_code == 200


def test_analyze_requires_authentication(client):
    assert client.post("/api/candidates/1/analyze").status_code == 401


def test_analyze_without_github_username_is_rejected(client, monkeypatch):
    _fake_github(monkeypatch)
    recruiter = _make_user("r2@acme.com", "recruiter")
    student = _make_user("s3@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Docker"], github_username=None)

    response = client.post(f"/api/candidates/{candidate_id}/analyze", headers=_auth_headers(recruiter))

    assert response.status_code == 400


def test_github_failure_returns_502_and_saves_nothing(client, monkeypatch):
    async def failing_fetch(username: str):
        request = httpx.Request("GET", "https://api.github.com/users/octocat/repos")
        raise httpx.HTTPStatusError("rate limited", request=request, response=httpx.Response(403, request=request))

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", failing_fetch)
    recruiter = _make_user("r3@acme.com", "recruiter")
    student = _make_user("s4@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Docker"])

    response = client.post(f"/api/candidates/{candidate_id}/analyze", headers=_auth_headers(recruiter))

    assert response.status_code == 502
    assert "GITHUB_TOKEN" in response.json()["detail"]
    detail = client.get(f"/api/candidates/{candidate_id}", headers=_auth_headers(recruiter)).json()
    assert _skill(detail, "Docker")["status"] is None


def test_other_supporting_repos_are_saved_and_returned(client, monkeypatch):
    repos = FAKE_REPOS + [
        {
            "name": "docker-practice",
            "language": "Shell",
            "is_fork": True,
            "stars": 0,
            "updated_at": RECENT,
            "url": "https://github.com/octocat/docker-practice",
        },
    ]
    fingerprints = {**FAKE_FINGERPRINTS, "docker-practice": {"Docker": ["Dockerfile found at Dockerfile"]}}

    async def fake_fetch_repos(username: str):
        return repos

    async def fake_fingerprint(owner: str, repo: str):
        return fingerprints[repo]

    monkeypatch.setattr("app.services.analysis.fetch_github_repos", fake_fetch_repos)
    monkeypatch.setattr("app.services.analysis.fingerprint_repo", fake_fingerprint)
    student = _make_user("s5@thapar.edu", "student")
    candidate_id = _make_candidate(student.user_id, ["Docker", "React"])
    headers = _auth_headers(student)

    body = client.post(f"/api/candidates/{candidate_id}/analyze", headers=headers).json()

    docker = _skill(body, "Docker")
    assert docker["score"] == 80
    assert all(reason.startswith("shop-api:") for reason in docker["reasons"])
    assert docker["supporting_repos"] == [{"repo": "docker-practice", "score": 60}]
    assert _skill(body, "React")["supporting_repos"] == []

    # Saved: a plain GET returns the same list, and it is not mixed into the reasons.
    detail = client.get(f"/api/candidates/{candidate_id}", headers=headers).json()
    assert _skill(detail, "Docker")["supporting_repos"] == [{"repo": "docker-practice", "score": 60}]
    assert "docker-practice" not in _skill(detail, "Docker")["reasons"]


def test_skills_are_grouped_by_category_and_concepts_are_not_scored(client, monkeypatch):
    _fake_github(monkeypatch)
    student = _make_user("s6@thapar.edu", "student")
    candidate_id = _make_candidate(
        student.user_id, ["Object-Oriented Programming", "Docker", "Python", "Excel"]
    )
    headers = _auth_headers(student)

    # Before any analysis, concept skills already show why they aren't scored.
    before = client.get(f"/api/candidates/{candidate_id}", headers=headers).json()
    assert [s["skill_name"] for s in before["skills"]] == [
        "Python", "Docker", "Excel", "Object-Oriented Programming",
    ]
    assert [s["category"] for s in before["skills"]] == [
        "Programming Languages", "Cloud & DevOps", "Data & Analytics", "Core Concepts",
    ]
    oop = _skill(before, "Object-Oriented Programming")
    assert oop["checkable"] is False
    assert oop["status"] == "Not checkable on GitHub"
    assert oop["score"] is None
    assert oop["reasons"] == ["Concept knowledge - best checked in the interview."]
    assert "encapsulation" in oop["interview_question"]
    assert _skill(before, "Python")["status"] is None

    after = client.post(f"/api/candidates/{candidate_id}/analyze", headers=headers).json()

    assert _skill(after, "Docker")["score"] == 80
    assert _skill(after, "Excel")["status"] == "Not checkable on GitHub"
    assert _skill(after, "Excel")["score"] is None
    assert _skill(after, "Excel")["reasons"] == ["Spreadsheet work isn't stored on GitHub."]
