"""
Student quiz practice: pick skills (or "my unproven skills"), take a
multiple-choice quiz, see the score per skill with explanations, and look
back at past attempts. Practice results are private to the student.
"""
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import require_role
from ..services import quiz
from ..services.visibility import visible_candidate_id
from ..skills_dictionary import category_of

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

student_only = require_role("student")

SECONDS_PER_QUESTION = 60
GRACE_SECONDS = 15
PROVEN = ("Strong Evidence", "Good Evidence")


class PracticeIn(BaseModel):
    skills: list[str] = Field(min_length=1, max_length=20)
    count: int = 10
    timed: bool = False


class SubmitIn(BaseModel):
    answers: dict[str, int | None] = Field(default_factory=dict)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _deadline(attempt: models.QuizAttempt) -> datetime | None:
    if not attempt.time_limit_seconds:
        return None
    return _aware(attempt.started_at) + timedelta(seconds=attempt.time_limit_seconds)


def _in_progress(attempt: models.QuizAttempt) -> dict:
    deadline = _deadline(attempt)
    return {
        "attempt_id": attempt.attempt_id,
        "kind": attempt.kind,
        "status": "in_progress",
        "skills": json.loads(attempt.skills),
        "questions": [quiz.public_question(i) for i in json.loads(attempt.questions)],
        "time_limit_seconds": attempt.time_limit_seconds,
        "started_at": attempt.started_at,
        "deadline": deadline,
    }


def _finished(attempt: models.QuizAttempt) -> dict:
    return {
        "attempt_id": attempt.attempt_id,
        "kind": attempt.kind,
        "status": "submitted",
        "skills": json.loads(attempt.skills),
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "over_time": attempt.over_time,
        **json.loads(attempt.result),
    }


def _own_attempt(db: Session, user: models.User, attempt_id: int) -> models.QuizAttempt:
    attempt = db.query(models.QuizAttempt).filter_by(attempt_id=attempt_id).first()
    if attempt is None or attempt.user_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found.")
    return attempt


def start_attempt(db: Session, user: models.User, kind: str, skills: list[str], count: int,
                  time_limit_seconds: int | None) -> models.QuizAttempt:
    """Create an attempt with freshly picked questions (used by practice and skill tests)."""
    chosen = quiz.known_skills(skills)
    if not chosen:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pick at least one skill that has questions.")
    items = quiz.pick_questions(chosen, count)
    attempt = models.QuizAttempt(
        user_id=user.user_id, kind=kind, skills=json.dumps(chosen), questions=json.dumps(items),
        total=len(items), time_limit_seconds=time_limit_seconds,
    )
    db.add(attempt)
    db.flush()
    return attempt


def submit_attempt(attempt: models.QuizAttempt, answers: dict[str, int | None]) -> None:
    """Grade and close an attempt. Answers after the time limit (plus a short grace) are flagged."""
    now = datetime.now(timezone.utc)
    deadline = _deadline(attempt)
    result = quiz.grade(json.loads(attempt.questions), answers)
    attempt.answers = json.dumps(answers)
    attempt.result = json.dumps(result)
    attempt.score = result["score"]
    attempt.submitted_at = now
    attempt.over_time = bool(deadline and now > deadline + timedelta(seconds=GRACE_SECONDS))


@router.get("/skills")
def practice_skills(db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    """Skills that have questions, plus the unproven skills on the student's visible resume."""
    skills = [
        {"name": name, "category": category_of(name), "questions": len(qs)} for name, qs in quiz.BANK.items()
    ]
    suggested: list[str] = []
    visible = visible_candidate_id(db, student)
    if visible:
        candidate = db.get(models.Candidate, visible)
        suggested = quiz.known_skills(
            [cs.skill.skill_name for cs in candidate.skills if cs.status not in PROVEN]
        )
    return {"skills": skills, "suggested": suggested, "counts": list(quiz.COUNTS)}


@router.post("/practice", status_code=status.HTTP_201_CREATED)
def start_practice(body: PracticeIn, db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    count = body.count if body.count in quiz.COUNTS else 10
    attempt = start_attempt(
        db, student, "practice", body.skills, count,
        count * SECONDS_PER_QUESTION if body.timed else None,
    )
    db.commit()
    return _in_progress(attempt)


@router.get("/attempts")
def list_attempts(db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    """The student's practice history, newest first."""
    attempts = (
        db.query(models.QuizAttempt)
        .filter_by(user_id=student.user_id, kind="practice")
        .order_by(models.QuizAttempt.started_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "attempt_id": a.attempt_id,
            "skills": json.loads(a.skills),
            "score": a.score,
            "total": a.total,
            "started_at": a.started_at,
            "submitted_at": a.submitted_at,
        }
        for a in attempts
    ]


@router.get("/attempts/{attempt_id}")
def get_attempt(attempt_id: int, db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    attempt = _own_attempt(db, student, attempt_id)
    return _finished(attempt) if attempt.submitted_at else _in_progress(attempt)


@router.post("/attempts/{attempt_id}/submit")
def submit(attempt_id: int, body: SubmitIn, db: Session = Depends(get_db), student: models.User = Depends(student_only)):
    attempt = _own_attempt(db, student, attempt_id)
    if attempt.submitted_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz was already submitted.")
    submit_attempt(attempt, body.answers)
    if attempt.kind == "test":
        from .skill_tests import on_test_submitted  # imported here to avoid a circular import

        on_test_submitted(db, attempt)
    db.commit()
    return _finished(attempt)
