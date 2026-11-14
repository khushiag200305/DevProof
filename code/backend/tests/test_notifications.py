"""In-app notifications: who hears about what, read state, and no duplicates."""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.services import notifications
from app.services.auth import create_access_token


def _user(email: str, role: str, status=None) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name=email.split("@")[0], role=role, recruiter_status=status)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _candidate(owner, name="Khushi", python=("Strong Evidence", 100)) -> int:
    with SessionLocal() as db:
        c = models.Candidate(user_id=owner.user_id if owner else None, name=name, github_username=name.lower())
        db.add(c)
        db.flush()
        skill = db.query(models.Skill).filter_by(skill_name="Python").first() or models.Skill(skill_name="Python")
        db.add(skill)
        db.flush()
        db.add(models.CandidateSkill(candidate_id=c.candidate_id, skill_id=skill.skill_id, status=python[0], score=python[1]))
        db.commit()
        return c.candidate_id


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _titles(client, user) -> list[str]:
    return [n["title"] for n in client.get("/api/notifications", headers=_h(user)).json()["items"]]


def test_list_read_and_read_all(client):
    student = _user("k@thapar.edu", "student")
    with SessionLocal() as db:
        notifications.notify(db, student.user_id, "x", "First", link="/upload")
        notifications.notify(db, student.user_id, "x", "Second")
        db.commit()

    body = client.get("/api/notifications", headers=_h(student)).json()
    assert body["unread"] == 2
    assert [n["title"] for n in body["items"]] == ["Second", "First"]

    first = body["items"][1]["notification_id"]
    assert client.post(f"/api/notifications/{first}/read", headers=_h(student)).json()["read"] is True
    assert client.get("/api/notifications", headers=_h(student)).json()["unread"] == 1

    client.post("/api/notifications/read-all", headers=_h(student))
    assert client.get("/api/notifications", headers=_h(student)).json()["unread"] == 0

    other = _user("s@thapar.edu", "student")
    assert client.post(f"/api/notifications/{first}/read", headers=_h(other)).status_code == 404
    assert client.get("/api/notifications").status_code == 401


def test_recruiter_hears_about_new_matches_for_saved_searches_once(client):
    recruiter = _user("hr@acme.com", "recruiter")
    client.post(
        "/api/talent/saved-searches", json={"name": "Python devs", "query": {"skills": ["Python"]}}, headers=_h(recruiter)
    )
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)

    # The student makes this resume visible: one match notification.
    client.put(f"/api/candidates/{candidate_id}/visible", headers=_h(student))
    client.put(f"/api/candidates/{candidate_id}/visible", headers=_h(student))
    items = client.get("/api/notifications", headers=_h(recruiter)).json()["items"]
    assert [n["title"] for n in items] == ['New match for "Python devs"']
    assert items[0]["link"] == f"/candidate/{candidate_id}"


def test_non_matching_or_hidden_resumes_send_nothing(client):
    recruiter = _user("hr@acme.com", "recruiter")
    client.post(
        "/api/talent/saved-searches", json={"name": "Strong Python", "query": {"skills": ["Python"], "min_level": "strong"}},
        headers=_h(recruiter),
    )
    student = _user("k@thapar.edu", "student")
    weak = _candidate(student, python=("Needs Verification", 10))
    client.put(f"/api/candidates/{weak}/visible", headers=_h(student))
    assert _titles(client, recruiter) == []

    with SessionLocal() as db:
        strong_but_hidden = db.get(models.Candidate, _candidate(student))
        assert notifications.new_search_matches(db, strong_but_hidden) == 0


def test_student_hears_when_shortlisted_once_per_recruiter(client):
    recruiter = _user("hr@acme.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)

    client.put(f"/api/talent/shortlist/{candidate_id}", json={"note": "a"}, headers=_h(recruiter))
    client.put(f"/api/talent/shortlist/{candidate_id}", json={"note": "edited"}, headers=_h(recruiter))
    items = client.get("/api/notifications", headers=_h(student)).json()["items"]
    assert [n["title"] for n in items] == ["A recruiter shortlisted you"]
    assert "acme.com" in items[0]["body"]


def test_portfolio_views_notify_at_most_once_a_day(client):
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)
    with SessionLocal() as db:
        db.add(models.Portfolio(candidate_id=candidate_id, slug="khushi-abc123", is_public=True))
        db.commit()

    for _ in range(3):
        assert client.get("/api/portfolio/khushi-abc123").status_code == 200
    assert _titles(client, student) == ["Someone viewed your portfolio"]

    with SessionLocal() as db:
        candidate = db.get(models.Candidate, candidate_id)
        notifications.portfolio_viewed(db, candidate, now=datetime.now(timezone.utc) + timedelta(days=2))
        db.commit()
    assert len(_titles(client, student)) == 2


def test_admins_hear_about_recruiter_requests_and_recruiters_about_approval(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "Admin@Gmail.com")
    admin = _user("admin@gmail.com", "recruiter")
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: {"sub": "sub-new", "email": "hr@acme.com", "email_verified": True, "name": "Neha", "picture": None},
    )
    new = client.post("/api/auth/google", json={"credential": "fake"}).json()
    assert _titles(client, admin) == ["New recruiter request"]

    client.put(f"/api/admin/recruiters/{new['user']['user_id']}", json={"status": "approved"}, headers=_h(admin))
    titles = client.get("/api/notifications", headers={"Authorization": f"Bearer {new['access_token']}"}).json()
    assert [n["title"] for n in titles["items"]] == ["Your recruiter account was approved"]


def test_analysis_finished_notifies_the_student(client, monkeypatch):
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)

    async def fake_analysis(db, candidate):
        return None

    monkeypatch.setattr("app.routers.candidates.analyze_candidate", fake_analysis)
    assert client.post(f"/api/candidates/{candidate_id}/analyze", headers=_h(student)).status_code == 200
    items = client.get("/api/notifications", headers=_h(student)).json()["items"]
    assert items[0]["title"] == "Your GitHub analysis is ready"
    assert items[0]["body"] == "1 of 1 skills on your resume are backed by GitHub."
