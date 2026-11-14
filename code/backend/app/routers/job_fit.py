"""
Student-only: score each of the student's uploaded resumes against a
pasted job description or a ready-made role, say which one fits best
(app/services/job_fit.py), and give a skill gap roadmap for it
(app/services/roadmap.py). Nothing is saved.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..dependencies import require_role
from ..services.job_fit import fit_resumes
from ..services.roadmap import ROLES, build_roadmap
from ..services.visibility import visible_candidate_id
from ..skills_dictionary import NOT_CHECKABLE, is_checkable

router = APIRouter(prefix="/api/job-fit", tags=["job-fit"])


class JobFitRequest(BaseModel):
    job_description: str | None = Field(default=None, max_length=10000)
    role: str | None = None


@router.get("/roles")
def roles(student: models.User = Depends(require_role("student"))):
    return [{"name": name, "skills": skills} for name, skills in ROLES.items()]


def _repos(candidate: models.Candidate) -> list[dict]:
    out = []
    for r in candidate.repositories:
        detail = r.detail
        out.append({
            "name": r.repo_name,
            "is_fork": r.is_fork,
            "pushed_at": (detail.pushed_at if detail else None) or r.last_updated,
            "technologies": json.loads(detail.technologies) if detail and detail.technologies else [],
        })
    return out


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
            selectinload(models.Candidate.repositories).selectinload(models.Repository.detail),
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
    if body.role:
        if body.role not in ROLES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown role.")
        result = fit_resumes("", resumes, wanted=ROLES[body.role])
    elif body.job_description and body.job_description.strip():
        result = fit_resumes(body.job_description, resumes)
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Paste a job description or pick a role.")

    result["role"] = body.role
    result["roadmap"] = None
    best = next((r for r in result["resumes"] if r["best"]), None)
    if best:
        candidate = next(c for c in uploads if c.candidate_id == best["candidate_id"])
        result["roadmap"] = build_roadmap(best, _repos(candidate))
    return result
