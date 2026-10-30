"""
POST /api/candidates/{id}/resume-bullets

Suggested resume lines for the candidate's best projects, optionally
tailored to a job description. Same access rule as the candidate report
(the owner student or any recruiter); needs a GitHub analysis first,
since the lines are built from what the analysis found.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..services.portfolio import repo_dicts, skill_dicts
from ..services.resume_bullets import bullet_report
from .candidates import _get_visible_candidate

router = APIRouter(tags=["resume bullets"])


class BulletRequest(BaseModel):
    job_description: str | None = Field(default=None, max_length=10000)


@router.post("/api/candidates/{candidate_id}/resume-bullets")
def resume_bullets(
    candidate_id: int,
    body: BulletRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    candidate = _get_visible_candidate(candidate_id, db, current_user)
    if not candidate.repositories:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Run the GitHub analysis first - resume lines are built from your repositories.",
        )
    return bullet_report(repo_dicts(candidate), skill_dicts(candidate), body.job_description)
