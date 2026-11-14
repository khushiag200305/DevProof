"""Recruiter skill tests: send, take once within the time limit, results back to the recruiter."""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.routers.skill_tests import test_status as status_of
from app.services import quiz
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name=email.split("@")[0], role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _candidate(owner) -> int:
    with SessionLocal() as db:
        c = models.Candidate(user_id=owner.user_id if owner else None, name="Khushi Agarwal")
        db.add(c)
        db.commit()
        return c.candidate_id


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _right(question: dict) -> int:
    original = quiz.BY_ID[question["id"]]
    return question["options"].index(original["options"][original["answer"]])


def _titles(client, user):
    return [n["title"] for n in client.get("/api/notifications", headers=_h(user)).json()["items"]]


def test_send_take_and_see_the_result(client):
    recruiter = _user("hr@acme.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)

    sent = client.post(
        "/api/skill-tests",
        json={"candidate_id": candidate_id, "skills": ["docker", "SQL"], "question_count": 5, "time_limit_minutes": 10, "message": "Good luck"},
        headers=_h(recruiter),
    )
    assert sent.status_code == 201
    test = sent.json()
    assert (test["skills"], test["status"], test["student_name"]) == (["Docker", "SQL"], "waiting", "Khushi Agarwal")
    assert _titles(client, student) == ["You have a new skill test"]

    mine = client.get("/api/skill-tests/mine", headers=_h(student)).json()
    assert [(t["test_id"], t["status"], t["from_domain"], t["message"]) for t in mine] == [(test["test_id"], "waiting", "acme.com", "Good luck")]

    attempt = client.post(f"/api/skill-tests/{test['test_id']}/start", headers=_h(student)).json()
    assert attempt["kind"] == "test" and attempt["time_limit_seconds"] == 600 and len(attempt["questions"]) == 5
    # Reloading the page while taking it returns the same attempt.
    assert client.post(f"/api/skill-tests/{test['test_id']}/start", headers=_h(student)).json()["attempt_id"] == attempt["attempt_id"]
    assert client.get(f"/api/skill-tests/{test['test_id']}/result", headers=_h(recruiter)).status_code == 409

    answers = {q["id"]: _right(q) for q in attempt["questions"]}
    done = client.post(f"/api/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}, headers=_h(student)).json()
    assert done["score"] == 5

    assert client.post(f"/api/skill-tests/{test['test_id']}/start", headers=_h(student)).status_code == 409
    listed = client.get(f"/api/skill-tests/candidate/{candidate_id}", headers=_h(recruiter)).json()
    assert [(t["status"], t["score"], t["total"]) for t in listed] == [("done", 5, 5)]
    assert sum(s["total"] for s in listed[0]["per_skill"]) == 5
    full = client.get(f"/api/skill-tests/{test['test_id']}/result", headers=_h(recruiter)).json()
    assert len(full["result"]["questions"]) == 5
    assert _titles(client, recruiter) == ["Khushi Agarwal finished your skill test"]

    # Practice history only shows practice, not tests.
    assert client.get("/api/quiz/attempts", headers=_h(student)).json() == []


def test_only_the_right_people_can_see_or_take_a_test(client):
    recruiter = _user("hr@acme.com", "recruiter")
    other_recruiter = _user("hr@other.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    other_student = _user("s@thapar.edu", "student")
    test = client.post(
        "/api/skill-tests", json={"candidate_id": _candidate(student), "skills": ["Python"]}, headers=_h(recruiter)
    ).json()

    assert client.post(f"/api/skill-tests/{test['test_id']}/start", headers=_h(other_student)).status_code == 404
    assert client.get(f"/api/skill-tests/{test['test_id']}/result", headers=_h(other_recruiter)).status_code == 404
    assert client.get("/api/skill-tests/sent", headers=_h(other_recruiter)).json() == []
    assert client.post("/api/skill-tests", json={"candidate_id": _candidate(None), "skills": ["Python"]}, headers=_h(recruiter)).status_code == 422
    assert client.post("/api/skill-tests", json={"candidate_id": 9999, "skills": ["Python"]}, headers=_h(recruiter)).status_code == 404
    assert client.post("/api/skill-tests", json={"candidate_id": test["candidate_id"], "skills": ["Nope"]}, headers=_h(recruiter)).status_code == 422


def test_cancel_only_before_it_starts_and_expiry(client):
    recruiter = _user("hr@acme.com", "recruiter")
    student = _user("k@thapar.edu", "student")
    candidate_id = _candidate(student)
    first = client.post("/api/skill-tests", json={"candidate_id": candidate_id, "skills": ["Java"]}, headers=_h(recruiter)).json()
    assert client.delete(f"/api/skill-tests/{first['test_id']}", headers=_h(recruiter)).status_code == 204

    second = client.post("/api/skill-tests", json={"candidate_id": candidate_id, "skills": ["Java"]}, headers=_h(recruiter)).json()
    client.post(f"/api/skill-tests/{second['test_id']}/start", headers=_h(student))
    assert client.delete(f"/api/skill-tests/{second['test_id']}", headers=_h(recruiter)).status_code == 409

    third = client.post("/api/skill-tests", json={"candidate_id": candidate_id, "skills": ["Java"]}, headers=_h(recruiter)).json()
    with SessionLocal() as db:
        db.get(models.SkillTest, third["test_id"]).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.post(f"/api/skill-tests/{third['test_id']}/start", headers=_h(student)).status_code == 409
    statuses = {t["test_id"]: t["status"] for t in client.get("/api/skill-tests/sent", headers=_h(recruiter)).json()}
    assert statuses == {second["test_id"]: "in_progress", third["test_id"]: "expired"}


def test_status_when_time_runs_out():
    now = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
    test = models.SkillTest(expires_at=now + timedelta(days=7))
    started = models.QuizAttempt(started_at=now - timedelta(minutes=20), time_limit_seconds=600, submitted_at=None, over_time=False)
    assert status_of(test, started, now) == "timed_out"
    started.started_at = now - timedelta(minutes=5)
    assert status_of(test, started, now) == "in_progress"
    started.submitted_at, started.over_time = now, True
    assert status_of(test, started, now) == "late"
    assert status_of(test, None, now) == "waiting"


def test_recruiter_sees_testable_skills_and_whether_a_resume_has_an_account(client):
    recruiter = _user("hr3@acme.com", "recruiter")
    student = _user("s3@thapar.edu", "student")
    skills = client.get("/api/skill-tests/skills", headers=_h(recruiter)).json()["skills"]
    assert "Python" in skills and "C++" in skills
    assert client.get("/api/skill-tests/skills", headers=_h(student)).status_code == 403

    owned, orphan = _candidate(student), _candidate(None)
    assert client.get(f"/api/candidates/{owned}", headers=_h(recruiter)).json()["has_account"] is True
    assert client.get(f"/api/candidates/{orphan}", headers=_h(recruiter)).json()["has_account"] is False


def test_a_test_avoids_questions_the_student_already_practised(client):
    recruiter = _user("hr4@acme.com", "recruiter")
    student = _user("s4@thapar.edu", "student")
    candidate_id = _candidate(student)
    practice = client.post("/api/quiz/practice", json={"skills": ["Docker"], "count": 5}, headers=_h(student)).json()
    seen = {q["id"] for q in practice["questions"]}

    test = client.post(
        "/api/skill-tests", json={"candidate_id": candidate_id, "skills": ["Docker"], "question_count": 5}, headers=_h(recruiter)
    ).json()
    asked = {q["id"] for q in client.post(f"/api/skill-tests/{test['test_id']}/start", headers=_h(student)).json()["questions"]}
    assert len(asked) == 5 and not asked & seen
