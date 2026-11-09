"""
Talent search API: recruiter-only search by proven skills, saved
searches (with new-match counts), shortlist with notes, and compare.
"""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name=email.split("@")[0], role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _candidate(name: str, skills: dict, user_id=None, created=None, github=None) -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=user_id, name=name, github_username=github or name.lower())
        if created:
            candidate.created_at = created
        db.add(candidate)
        db.flush()
        for skill_name, (status, score) in skills.items():
            skill = db.query(models.Skill).filter_by(skill_name=skill_name).first()
            if skill is None:
                skill = models.Skill(skill_name=skill_name)
                db.add(skill)
                db.flush()
            db.add(models.CandidateSkill(
                candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status=status, score=score
            ))
        db.add(models.Repository(
            candidate_id=candidate.candidate_id, repo_name=f"{name}-repo", repo_url="https://github.com/x/y",
            is_fork=False, commit_count=5, last_updated=datetime.now(timezone.utc) - timedelta(days=5),
        ))
        db.commit()
        return candidate.candidate_id


def _headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


STRONG, GOOD, NEEDS = "Strong Evidence", "Good Evidence", "Needs Verification"


def _setup():
    recruiter = _user("hr@acme.com", "recruiter")
    aditi = _candidate("Aditi", {"Python": (STRONG, 100), "React": (GOOD, 60)})
    rohit = _candidate("Rohit", {"Python": (GOOD, 70), "Docker": (NEEDS, 0)})
    return recruiter, aditi, rohit


def test_students_cannot_use_talent_search(client):
    student = _user("s@thapar.edu", "student")
    assert client.post("/api/talent/search", json={}, headers=_headers(student)).status_code == 403
    assert client.get("/api/talent/shortlist", headers=_headers(student)).status_code == 403


def test_search_by_proven_skills(client):
    recruiter, aditi, rohit = _setup()
    h = _headers(recruiter)

    body = client.post("/api/talent/search", json={"skills": ["Python"]}, headers=h).json()
    assert [r["name"] for r in body] == ["Aditi", "Rohit"]
    assert body[0]["matched"] == [{"skill": "Python", "status": STRONG, "score": 100}]
    assert body[0]["shortlisted"] is False

    body = client.post("/api/talent/search", json={"skills": ["Python", "React"]}, headers=h).json()
    assert [r["name"] for r in body] == ["Aditi"]

    body = client.post(
        "/api/talent/search", json={"skills": ["Docker"], "min_level": "claimed"}, headers=h
    ).json()
    assert [r["name"] for r in body] == ["Rohit"]

    assert client.get("/api/talent/skills", headers=h).json() == ["Docker", "Python", "React"]


def test_each_person_appears_once_even_if_one_account_uploaded_several(client):
    recruiter = _user("hr@acme.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    now = datetime.now(timezone.utc)
    _candidate("Khushi", {"Python": (GOOD, 60)}, user_id=student.user_id, created=now - timedelta(days=20), github="khushi")
    latest = _candidate("Khushi", {"Python": (STRONG, 100)}, user_id=student.user_id, created=now - timedelta(days=10), github="khushi")
    # Same account later uploads a friend's resume: Khushi must still be found.
    rohit = _candidate("Rohit", {"Python": (GOOD, 70)}, user_id=student.user_id, created=now, github="rohit")

    body = client.post("/api/talent/search", json={"skills": ["Python"]}, headers=_headers(recruiter)).json()
    assert [r["candidate_id"] for r in body] == [latest, rohit]


def test_saved_search_counts_new_matches_and_resets_on_run(client):
    recruiter, aditi, rohit = _setup()
    other = _user("other@acme.com", "recruiter")
    h = _headers(recruiter)

    saved = client.post(
        "/api/talent/saved-searches",
        json={"name": "Python devs", "query": {"skills": ["Python"]}},
        headers=h,
    )
    assert saved.status_code == 201
    search_id = saved.json()["search_id"]
    assert saved.json()["match_count"] == 2

    # A student uploads after the search was saved: one new match.
    _candidate("Sneha", {"Python": (STRONG, 90)})
    listed = client.get("/api/talent/saved-searches", headers=h).json()
    assert [(s["name"], s["match_count"], s["new_count"]) for s in listed] == [("Python devs", 3, 1)]

    run = client.post(f"/api/talent/saved-searches/{search_id}/run", headers=h).json()
    assert [r["name"] for r in run["results"] if r["is_new"]] == ["Sneha"]
    assert client.get("/api/talent/saved-searches", headers=h).json()[0]["new_count"] == 0

    # Other recruiters can't see or delete it.
    assert client.get("/api/talent/saved-searches", headers=_headers(other)).json() == []
    assert client.delete(f"/api/talent/saved-searches/{search_id}", headers=_headers(other)).status_code == 404
    assert client.delete(f"/api/talent/saved-searches/{search_id}", headers=h).status_code == 204
    assert client.get("/api/talent/saved-searches", headers=h).json() == []


def test_shortlist_with_notes(client):
    recruiter, aditi, rohit = _setup()
    h = _headers(recruiter)

    assert client.put(f"/api/talent/shortlist/{aditi}", json={"note": "Great React work"}, headers=h).status_code == 200
    assert client.put("/api/talent/shortlist/9999", json={}, headers=h).status_code == 404

    listed = client.get("/api/talent/shortlist", headers=h).json()
    assert [(e["name"], e["note"]) for e in listed] == [("Aditi", "Great React work")]
    assert [s["skill"] for s in listed[0]["backed_skills"]] == ["Python", "React"]

    search = client.post("/api/talent/search", json={"skills": ["Python"]}, headers=h).json()
    assert {r["name"]: r["shortlisted"] for r in search} == {"Aditi": True, "Rohit": False}

    client.put(f"/api/talent/shortlist/{aditi}", json={"note": "  "}, headers=h)
    assert client.get("/api/talent/shortlist", headers=h).json()[0]["note"] is None

    assert client.delete(f"/api/talent/shortlist/{aditi}", headers=h).status_code == 204
    assert client.get("/api/talent/shortlist", headers=h).json() == []


def test_compare_two_candidates(client):
    recruiter, aditi, rohit = _setup()
    h = _headers(recruiter)

    body = client.get(f"/api/talent/compare?ids={aditi},{rohit}", headers=h).json()
    assert [c["name"] for c in body["candidates"]] == ["Aditi", "Rohit"]
    assert body["rows"][0]["skill"] == "Python"
    assert body["rows"][0]["cells"] == [{"status": STRONG, "score": 100}, {"status": GOOD, "score": 70}]

    assert client.get(f"/api/talent/compare?ids={aditi}", headers=h).status_code == 422
    assert client.get(f"/api/talent/compare?ids={aditi},9999", headers=h).status_code == 404
