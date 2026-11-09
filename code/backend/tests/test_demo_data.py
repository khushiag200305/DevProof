"""The demo data script adds 20 clearly marked students and removes only them."""
from app import demo_data, models
from app.database import SessionLocal
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name="Real", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def test_add_is_marked_searchable_and_idempotent(client):
    recruiter = _user("hr@acme.com", "recruiter")
    with SessionLocal() as db:
        assert demo_data.add(db) == 20
        assert demo_data.add(db) == 0  # already there

    listed = client.get("/api/candidates", headers=_h(recruiter)).json()
    assert len(listed) == 20
    assert all(c["name"].endswith("(Demo)") and c["email"].endswith("@demo.devproof") for c in listed)
    assert all(c["github_username"] is None for c in listed)

    found = client.post(
        "/api/talent/search", json={"skills": ["Python", "FastAPI"]}, headers=_h(recruiter)
    ).json()
    assert found and found[0]["name"] == "Aarav Mehta (Demo)"

    # Every demo report opens, with projects linked to their repositories.
    for c in listed:
        report = client.get(f"/api/candidates/{c['candidate_id']}", headers=_h(recruiter))
        assert report.status_code == 200
        body = report.json()
        assert body["analyzed"] and body["visible_to_recruiters"]
        assert all(p["repo"] for p in body["projects"])


def test_remove_deletes_only_demo_students(client):
    recruiter = _user("hr@acme.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    with SessionLocal() as db:
        real = models.Candidate(user_id=student.user_id, name="Khushi")
        db.add(real)
        db.commit()
        real_id = real.candidate_id
        demo_data.add(db)

    demo_id = next(
        c["candidate_id"] for c in client.get("/api/candidates", headers=_h(recruiter)).json()
        if c["name"].endswith("(Demo)")
    )
    client.put(f"/api/talent/shortlist/{demo_id}", json={"note": "demo"}, headers=_h(recruiter))

    with SessionLocal() as db:
        assert demo_data.remove(db) == 20
        assert db.query(models.User).filter(models.User.email.like("%@demo.devproof")).count() == 0

    assert [c["candidate_id"] for c in client.get("/api/candidates", headers=_h(recruiter)).json()] == [real_id]
    assert client.get("/api/talent/shortlist", headers=_h(recruiter)).json() == []
