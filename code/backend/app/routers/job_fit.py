"""
Student-only: score each of the student's uploaded resumes against a
pasted job description and say which one fits best (see
app/services/job_fit.py). Nothing is saved.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..dependencies import require_role
from ..services.job_fit import fit_resumes
from ..services.visibility import visible_candidate_id
from ..skills_dictionary import NOT_CHECKABLE, is_checkable

router = APIRouter(prefix="/api/job-fit", tags=["job-fit"])


class JobFitRequest(BaseModel):
    job_description: str = Field(min_length=1, max_length=10000)


@router.post("")
def job_fit(
    body: JobFitRequest,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_role("student")),
):
    uploads = (
        db.query(models.Candidate)
        .options(
            selectinload(models.Candidate.skills).selectinload(models.CandidateSkill.skill),
            selectinload(models.Candidate.repositories),
        )
        .filter(models.Candidate.user_id == student.user_id)
        .all()
    )
    visible = visible_candidate_id(db, student)
    resumes = [
        {
            "candidate_id": c.candidate_id,
            "name": c.name,
            "created_at": c.created_at,
            "analyzed": len(c.repositories) > 0,
            "visible_to_recruiters": c.candidate_id == visible,
            "skills": [
                {
                    "skill_name": cs.skill.skill_name,
                    "status": cs.status if is_checkable(cs.skill.skill_name) else NOT_CHECKABLE,
                }
                for cs in c.skills
            ],
        }
        for c in uploads
    ]
    return fit_resumes(body.job_description, resumes)
