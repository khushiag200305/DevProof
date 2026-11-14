"""Student quiz practice API: start, answer, submit once, history."""
from datetime import datetime, timedelta, timezone

from app import models
from app.database import SessionLocal
from app.services import quiz
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name="U", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _correct(question: dict) -> int:
    original = quiz.BY_ID[question["id"]]
    return question["options"].index(original["options"][original["answer"]])


def test_practice_round_trip(client):
    student = _user("k@thapar.edu", "student")
    started = client.post("/api/quiz/practice", json={"skills": ["Python", "SQL"], "count": 5}, headers=_h(student))
    assert started.status_code == 201
    attempt = started.json()
    assert attempt["status"] == "in_progress" and len(attempt["questions"]) == 5
    assert all("answer" not in q and "explanation" not in q for q in attempt["questions"])
    assert attempt["time_limit_seconds"] is None

    answers = {q["id"]: _correct(q) for q in attempt["questions"]}
    answers[attempt["questions"][0]["id"]] = (_correct(attempt["questions"][0]) + 1) % 4
    result = client.post(f"/api/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}, headers=_h(student)).json()
    assert (result["status"], result["score"], result["total"]) == ("submitted", 4, 5)
    assert all(q["explanation"] for q in result["questions"])

    again = client.post(f"/api/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": {}}, headers=_h(student))
    assert again.status_code == 409
    assert client.get(f"/api/quiz/attempts/{attempt['attempt_id']}", headers=_h(student)).json()["score"] == 4

    history = client.get("/api/quiz/attempts", headers=_h(student)).json()
    assert [(h["score"], h["total"]) for h in history] == [(4, 5)]


def test_timed_practice_flags_late_submissions(client):
    student = _user("k@thapar.edu", "student")
    attempt = client.post(
        "/api/quiz/practice", json={"skills": ["Docker"], "count": 5, "timed": True}, headers=_h(student)
    ).json()
    assert attempt["time_limit_seconds"] == 300 and attempt["deadline"]
    with SessionLocal() as db:
        row = db.get(models.QuizAttempt, attempt["attempt_id"])
        row.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
    result = client.post(f"/api/quiz/attempts/{attempt['attempt_id']}/submit", json={"answers": {}}, headers=_h(student)).json()
    assert result["over_time"] is True and result["score"] == 0


def test_suggested_skills_are_the_unproven_ones_on_the_visible_resume(client):
    student = _user("k@thapar.edu", "student")
    with SessionLocal() as db:
        c = models.Candidate(user_id=student.user_id, name="K")
        db.add(c)
        db.flush()
        for name, status in [("Python", "Strong Evidence"), ("Docker", "Needs Verification"), ("DBMS", "Not checkable on GitHub")]:
            skill = models.Skill(skill_name=name)
            db.add(skill)
            db.flush()
            db.add(models.CandidateSkill(candidate_id=c.candidate_id, skill_id=skill.skill_id, status=status))
        db.commit()
    body = client.get("/api/quiz/skills", headers=_h(student)).json()
    assert sorted(body["suggested"]) == ["DBMS", "Docker"]
    assert len(body["skills"]) == 46 and body["counts"] == [5, 10, 15]


def test_only_students_and_only_their_own_attempts(client):
    student = _user("k@thapar.edu", "student")
    other = _user("s@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    attempt = client.post("/api/quiz/practice", json={"skills": ["Java"]}, headers=_h(student)).json()
    assert client.get(f"/api/quiz/attempts/{attempt['attempt_id']}", headers=_h(other)).status_code == 404
    assert client.post("/api/quiz/practice", json={"skills": ["Java"]}, headers=_h(recruiter)).status_code == 403
    assert client.post("/api/quiz/practice", json={"skills": ["Nope"]}, headers=_h(student)).status_code == 422
