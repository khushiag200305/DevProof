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
from ..services.analysis import SUPPORTING_REPO, GitHubUnavailableError, analyze_candidate

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
    reasons_by_skill: dict[int, list[str]] = {}
    supporting_by_skill: dict[int, list[dict]] = {}
    for evidence in sorted(candidate.evidence, key=lambda e: e.evidence_id):
        if evidence.evidence_type == SUPPORTING_REPO:
            supporting_by_skill.setdefault(evidence.skill_id, []).append(
                {"repo": evidence.description, "score": evidence.weight}
            )
        else:
            reasons_by_skill.setdefault(evidence.skill_id, []).append(evidence.description)

    question_by_skill = {q.skill_id: q.question for q in candidate.questions}
    analyzed = len(candidate.repositories) > 0

    skills = []
    for cs in candidate.skills:
        reasons = reasons_by_skill.get(cs.skill_id, [])
        if cs.status is not None and not reasons:
            reasons = ["No supporting evidence found in analyzed repositories"]
        skills.append(
            {
                "skill_name": cs.skill.skill_name,
                "status": cs.status,
                "score": cs.score,
                "reasons": reasons,
                "interview_question": question_by_skill.get(cs.skill_id),
                "supporting_repos": supporting_by_skill.get(cs.skill_id, []),
            }
        )

    return {
        **_candidate_summary(candidate),
        "repos_analyzed": len(candidate.repositories),
        "analyzed": analyzed,
        "skills": skills,
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


def _get_visible_candidate(
    candidate_id: int, db: Session, current_user: models.User
) -> models.Candidate:
    """
    Load a candidate the current user is allowed to see: recruiters can
    see any candidate, a student only their own.
    """
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")

    is_owner = candidate.user_id == current_user.user_id
    if current_user.role != "recruiter" and not is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your candidate record.")

    return candidate


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Recruiters can open any candidate; a student can only open their own.
    """
    return _candidate_detail(_get_visible_candidate(candidate_id, db, current_user))


@router.post("/{candidate_id}/analyze")
async def analyze(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Runs the GitHub evidence engine (repos -> fingerprinting -> scoring)
    for a candidate, saves the scores, reasons and interview questions,
    and returns the updated candidate detail. Same access rule as GET.
    """
    candidate = _get_visible_candidate(candidate_id, db, current_user)

    try:
        await analyze_candidate(db, candidate)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except GitHubUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return _candidate_detail(candidate)
