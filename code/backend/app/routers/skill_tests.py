"""
Recruiter skill tests: a recruiter sends a short timed quiz on chosen
skills to a student, the student takes it once, and the score shows up
for the recruiter next to the GitHub evidence. Built on the same quiz
engine and attempts as student practice (app/routers/quiz.py).
"""
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import require_role
from ..services import notifications, quiz
from .quiz import GRACE_SECONDS, _aware, _finished, _in_progress, start_attempt

router = APIRouter(prefix="/api/skill-tests", tags=["skill-tests"])

recruiter_only = require_role("recruiter")
student_only = require_role("student")

EXPIRES_AFTER_DAYS = 7


class SkillTestIn(BaseModel):
    candidate_id: int
    skills: list[str] = Field(min_length=1, max_length=10)
    question_count: int = 10
    time_limit_minutes: int = Field(default=15, ge=5, le=60)
    message: str | None = Field(default=None, max_length=500)


def test_status(test: models.SkillTest, attempt: models.QuizAttempt | None, now: datetime | None = None) -> str:
    """waiting | in_progress | done | late | timed_out | expired"""
    now = now or datetime.now(timezone.utc)
    if attempt is None:
        return "expired" if now > _aware(test.expires_at) else "waiting"
    if attempt.submitted_at:
        return "late" if attempt.over_time else "done"
    deadline = _aware(attempt.started_at) + timedelta(seconds=attempt.time_limit_seconds or 0)
    if now > deadline + timedelta(seconds=GRACE_SECONDS):
        return "timed_out"
    return "in_progress"


def _summary(db: Session, test: models.SkillTest, for_recruiter: bool) -> dict:
    attempt = db.get(models.QuizAttempt, test.attempt_id) if test.attempt_id else None
    out = {
        "test_id": test.test_id,
        "skills": json.loads(test.skills),
        "question_count": test.question_count,
        "time_limit_minutes": test.time_limit_minutes,
        "message": test.message,
        "created_at": test.created_at,
        "expires_at": test.expires_at,
        "status": test_status(test, attempt),
        "score": attempt.score if attempt and attempt.submitted_at else None,
        "total": attempt.total if attempt else test.question_count,
        "submitted_at": attempt.submitted_at if attempt else None,
        "attempt_id": test.attempt_id,
    }
    if attempt and attempt.submitted_at:
        out["per_skill"] = json.loads(attempt.result)["per_skill"]
    if for_recruiter:
        student = db.get(models.User, test.student_id)
        candidate = db.get(models.Candidate, test.candidate_id) if test.candidate_id else None
        out["student_name"] = (candidate.name if candidate else None) or (student.name if student else None)
        out["candidate_id"] = test.candidate_id
    else:
        recruiter = db.get(models.User, test.recruiter_id)
        out["from_domain"] = recruiter.email.rsplit("@", 1)[-1] if recruiter else None
    return out


def _own_sent(db: Session, recruiter: models.User, test_id: int) -> models.SkillTest:
    test = db.get(models.SkillTest, test_id)
    if test is None or test.recruiter_id != recruiter.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill test not found.")
    return test


def _own_received(db: Session, student: models.User, test_id: int) -> models.SkillTest:
    test = db.get(models.SkillTest, test_id)
    if test is None or test.student_id != student.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill test not found.")
    return test


# --- Recruiter ------------------------------------------------------------


@router.get("/skills")
def testable_skills(recruiter: models.User = Depends(recruiter_only)):
    """Skills that have questions in the bank."""
    return {"skills": list(quiz.BANK), "counts": list(quiz.COUNTS)}


@router.post("", status_code=status.HTTP_201_CREATED)
def send_test(body: SkillTestIn, db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    candidate = db.get(models.Candidate, body.candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    if candidate.user_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "This candidate has no student account to send a test to.")
    skills = quiz.known_skills(body.skills)
    if not skills:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pick at least one skill that has questions.")
    count = body.question_count if body.question_count in quiz.COUNTS else 10
    test = models.SkillTest(
        recruiter_id=recruiter.user_id, student_id=candidate.user_id, candidate_id=candidate.candidate_id,
        skills=json.dumps(skills), question_count=count, time_limit_minutes=body.time_limit_minutes,
        message=(body.message or "").strip() or None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=EXPIRES_AFTER_DAYS),
    )
    db.add(test)
    db.flush()
    domain = recruiter.email.rsplit("@", 1)[-1]
    notifications.notify(
        db, candidate.user_id, "skill_test", "You have a new skill test",
        f"A recruiter from {domain} sent you a test on {', '.join(skills)} "
        f"({count} questions, {body.time_limit_minutes} min). Take it within {EXPIRES_AFTER_DAYS} days.",
        "/practice",
    )
    db.commit()
    return _summary(db, test, for_recruiter=True)


@router.get("/sent")
def sent_tests(db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    tests = (
        db.query(models.SkillTest)
        .filter_by(recruiter_id=recruiter.user_id)
        .order_by(models.SkillTest.created_at.desc())
        .all()
    )
    return [_summary(db, t, for_recruiter=True) for t in tests]


@router.get("/candidate/{candidate_id}")
def tests_for_candidate(candidate_id: int, db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    """Tests this recruiter sent to the student behind this resume."""
    candidate = db.get(models.Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    if candidate.user_id is None:
        return []
    tests = (
        db.query(models.SkillTest)
        .filter_by(recruiter_id=recruiter.user_id, student_id=candidate.user_id)
        .order_by(models.SkillTest.created_at.desc())
        .all()
    )
    return [_summary(db, t, for_recruiter=True) for t in tests]


@router.get("/{test_id}/result")
def test_result(test_id: int, db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    """The full graded test, question by question."""
    test = _own_sent(db, recruiter, test_id)
    attempt = db.get(models.QuizAttempt, test.attempt_id) if test.attempt_id else None
    if attempt is None or not attempt.submitted_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "The student hasn't finished this test yet.")
    return {**_summary(db, test, for_recruiter=True), "result": _finished(attempt)}


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_test(test_id: int, db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    test = _own_sent(db, recruiter, test_id)
    if test.attempt_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "The student has already started this test.")
    db.delete(test)
    db.commit()


# --- Student --------------------------------------------------------------


@router.get("/mine")
def my_tests(db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    tests = (
        db.query(models.SkillTest)
        .filter_by(student_id=student.user_id)
        .order_by(models.SkillTest.created_at.desc())
        .all()
    )
    return [_summary(db, t, for_recruiter=False) for t in tests]


@router.post("/{test_id}/start")
def start_test(test_id: int, db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    """Start the test (once). Returns the questions; the timer runs on the server."""
    test = _own_received(db, student, test_id)
    if test.attempt_id:
        attempt = db.get(models.QuizAttempt, test.attempt_id)
        state = test_status(test, attempt)
        if state == "in_progress":
            return _in_progress(attempt)  # e.g. the page was reloaded
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already taken this test.")
    if test_status(test, None) == "expired":
        raise HTTPException(status.HTTP_409_CONFLICT, "This test has expired.")
    attempt = start_attempt(
        db, student, "test", json.loads(test.skills), test.question_count, test.time_limit_minutes * 60
    )
    test.attempt_id = attempt.attempt_id
    db.commit()
    return _in_progress(attempt)


def on_test_submitted(db: Session, attempt: models.QuizAttempt) -> None:
    """Called by the quiz router after a test attempt is graded: tell the recruiter."""
    test = db.query(models.SkillTest).filter_by(attempt_id=attempt.attempt_id).first()
    if test is None:
        return
    candidate = db.get(models.Candidate, test.candidate_id) if test.candidate_id else None
    student = db.get(models.User, test.student_id)
    name = (candidate.name if candidate else None) or (student.name if student else "A student")
    notifications.notify(
        db, test.recruiter_id, "skill_test_done", f"{name} finished your skill test",
        f"Score {attempt.score}/{attempt.total} on {', '.join(json.loads(test.skills))}"
        + (" (submitted after the time limit)." if attempt.over_time else "."),
        f"/candidate/{test.candidate_id}" if test.candidate_id else "/talent",
    )
