"""
Candidate listing/detail endpoints (Section 5 of the proposal).

Access is role-gated per the product's "students self-upload, recruiters
browse" design: recruiters can list and open any candidate; a student
can only see their own uploads.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


def _candidate_summary(candidate: models.Candidate) -> dict:
    return {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "email": candidate.email,
        "github_username": candidate.github_username,
        "created_at": candidate.created_at,
        "skill_count": len(candidate.skills),
    }


def _candidate_detail(candidate: models.Candidate) -> dict:
    return {
        **_candidate_summary(candidate),
        "skills": [
            {
                "skill_name": cs.skill.skill_name,
                "status": cs.status,
                "score": cs.score,
            }
            for cs in candidate.skills
        ],
        "projects": [
            {"project_name": p.project_name, "description": p.description}
            for p in candidate.projects
        ],
    }


@router.get("")
def list_candidates(
    db: Session = Depends(get_db),
    _recruiter: models.User = Depends(require_role("recruiter")),
):
    """Recruiter-only: every candidate who has uploaded a resume."""
    candidates = db.query(models.Candidate).order_by(models.Candidate.created_at.desc()).all()
    return [_candidate_summary(c) for c in candidates]


@router.get("/me")
def list_my_candidates(
    db: Session = Depends(get_db),
    student: models.User = Depends(require_role("student")),
):
    """Student-only: this student's own upload history, most recent first."""
    candidates = (
        db.query(models.Candidate)
        .filter_by(user_id=student.user_id)
        .order_by(models.Candidate.created_at.desc())
        .all()
    )
    return [_candidate_summary(c) for c in candidates]


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Recruiters can open any candidate; a student can only open their own.
    """
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")

    is_owner = candidate.user_id == current_user.user_id
    if current_user.role != "recruiter" and not is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your candidate record.")

    return _candidate_detail(candidate)
