"""
A student chooses which of their resumes is visible to recruiters:
recruiters' lists and talent search show only that one, shortlists
follow the student, and deleting the visible one falls back to the
newest remaining upload.
"""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name="U", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _upload(owner: models.User, name: str, days_ago: int, python=("Strong Evidence", 100)) -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(
            user_id=owner.user_id, name=name, github_username="khushi",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        db.add(candidate)
        db.flush()
        skill = db.query(models.Skill).filter_by(skill_name="Python").first()
        if skill is None:
            skill = models.Skill(skill_name="Python")
            db.add(skill)
            db.flush()
        db.add(models.CandidateSkill(
            candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status=python[0], score=python[1]
        ))
        db.commit()
        return candidate.candidate_id


def _h(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _recruiter_sees(client, recruiter) -> list[int]:
    return [c["candidate_id"] for c in client.get("/api/candidates", headers=_h(recruiter)).json()]


def test_student_chooses_which_resume_recruiters_see(client):
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    older = _upload(student, "Khushi", days_ago=10)
    newer = _upload(student, "Khushi", days_ago=1)

    # No choice yet: the newest upload is visible.
    assert _recruiter_sees(client, recruiter) == [newer]
    mine = client.get("/api/candidates/me", headers=_h(student)).json()
    assert {c["candidate_id"]: c["visible_to_recruiters"] for c in mine} == {newer: True, older: False}

    assert client.put(f"/api/candidates/{older}/visible", headers=_h(student)).status_code == 200
    assert _recruiter_sees(client, recruiter) == [older]

    report = client.get(f"/api/candidates/{newer}", headers=_h(recruiter)).json()
    assert report["visible_to_recruiters"] is False
    assert report["visible_candidate_id"] == older

    search = client.post("/api/talent/search", json={"skills": ["Python"]}, headers=_h(recruiter)).json()
    assert [r["candidate_id"] for r in search] == [older]


def test_only_the_owner_can_choose(client):
    owner = _user("k@thapar.edu", "student")
    other = _user("s@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    upload = _upload(owner, "Khushi", days_ago=1)

    assert client.put(f"/api/candidates/{upload}/visible", headers=_h(other)).status_code == 403
    assert client.put(f"/api/candidates/{upload}/visible", headers=_h(recruiter)).status_code == 403
    assert client.put("/api/candidates/9999/visible", headers=_h(owner)).status_code == 404


def test_deleting_the_visible_resume_shows_the_newest_remaining(client):
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    first = _upload(student, "Khushi", days_ago=10)
    second = _upload(student, "Khushi", days_ago=5)
    third = _upload(student, "Khushi", days_ago=1)
    client.put(f"/api/candidates/{first}/visible", headers=_h(student))

    assert client.delete(f"/api/candidates/{first}", headers=_h(student)).status_code == 204
    assert _recruiter_sees(client, recruiter) == [third]
    assert second not in _recruiter_sees(client, recruiter)


def test_shortlist_follows_the_student_to_their_visible_resume(client):
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    older = _upload(student, "Khushi", days_ago=10)
    newer = _upload(student, "Khushi", days_ago=1)

    client.put(f"/api/talent/shortlist/{newer}", json={"note": "Call back"}, headers=_h(recruiter))
    client.put(f"/api/candidates/{older}/visible", headers=_h(student))

    listed = client.get("/api/talent/shortlist", headers=_h(recruiter)).json()
    assert [(e["candidate_id"], e["note"]) for e in listed] == [(older, "Call back")]
    search = client.post("/api/talent/search", json={}, headers=_h(recruiter)).json()
    assert [(r["candidate_id"], r["shortlisted"]) for r in search] == [(older, True)]

    # Starring the visible resume again moves the entry, keeping one per student.
    client.put(f"/api/talent/shortlist/{older}", json={"note": "Call back"}, headers=_h(recruiter))
    assert len(client.get("/api/talent/shortlist", headers=_h(recruiter)).json()) == 1

    # Unstarring removes the student, whichever resume the entry was on.
    assert client.delete(f"/api/talent/shortlist/{newer}", headers=_h(recruiter)).status_code == 204
    assert client.get("/api/talent/shortlist", headers=_h(recruiter)).json() == []


def test_a_new_upload_does_not_replace_the_visible_resume(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.routers.resume.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.routers.resume.extract_text_from_pdf", lambda _b: "Khushi Agarwal\nSkills: Python")
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")

    def upload():
        return client.post(
            "/api/resume/upload",
            headers=_h(student),
            files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        ).json()

    first = upload()
    assert first["visible_to_recruiters"] is True
    second = upload()
    assert second["visible_to_recruiters"] is False
    assert _recruiter_sees(client, recruiter) == [first["candidate_id"]]
