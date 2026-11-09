"""POST /api/job-fit: a student's resumes ranked against a job description."""
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


def _upload(owner, days_ago: int, skills: dict, analyzed=True) -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(
            user_id=owner.user_id, name="Khushi",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        db.add(candidate)
        db.flush()
        for name, status in skills.items():
            skill = db.query(models.Skill).filter_by(skill_name=name).first()
            if skill is None:
                skill = models.Skill(skill_name=name)
                db.add(skill)
                db.flush()
            db.add(models.CandidateSkill(candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status=status))
        if analyzed:
            db.add(models.Repository(
                candidate_id=candidate.candidate_id, repo_name="r", repo_url="https://github.com/k/r",
                is_fork=False, commit_count=1,
            ))
        db.commit()
        return candidate.candidate_id


def _h(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


JOB = {"job_description": "Backend intern: Python, PostgreSQL, Docker."}


def test_ranks_the_students_own_resumes_for_a_job(client):
    student = _user("k@thapar.edu", "student")
    other = _user("s@thapar.edu", "student")
    frontend = _upload(student, 1, {"Python": "Good Evidence", "React": "Strong Evidence"})
    backend = _upload(student, 10, {"Python": "Strong Evidence", "PostgreSQL": "Good Evidence", "Docker": "Needs Verification"})
    _upload(other, 1, {"Python": "Strong Evidence", "PostgreSQL": "Strong Evidence", "Docker": "Strong Evidence"})

    body = client.post("/api/job-fit", json=JOB, headers=_h(student)).json()
    assert body["skills"] == ["Docker", "PostgreSQL", "Python"]
    assert [r["candidate_id"] for r in body["resumes"]] == [backend, frontend]
    assert body["best_candidate_id"] == backend
    best = body["resumes"][0]
    assert (best["proven"], best["claimed_only"], best["missing"]) == (["PostgreSQL", "Python"], ["Docker"], [])
    assert best["fit"] == 80
    # Newest upload is visible by default.
    assert {r["candidate_id"]: r["visible_to_recruiters"] for r in body["resumes"]} == {backend: False, frontend: True}


def test_unanalyzed_resume_only_counts_skills_as_claimed(client):
    student = _user("k@thapar.edu", "student")
    _upload(student, 1, {"Python": None}, analyzed=False)
    body = client.post("/api/job-fit", json=JOB, headers=_h(student)).json()
    r = body["resumes"][0]
    assert r["analyzed"] is False and r["claimed_only"] == ["Python"] and r["proven"] == []


def test_recruiters_cannot_use_it_and_an_empty_job_is_rejected(client):
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    assert client.post("/api/job-fit", json=JOB, headers=_h(recruiter)).status_code == 403
    assert client.post("/api/job-fit", json={"job_description": ""}, headers=_h(student)).status_code == 422
