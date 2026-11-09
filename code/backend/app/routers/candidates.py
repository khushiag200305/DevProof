"""
Candidate listing/detail endpoints (Section 5 of the proposal).

Access is role-gated per the product's "students self-upload, recruiters
browse" design: recruiters can list and open any candidate; a student
can only see their own uploads.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..services.analysis import SUPPORTING_REPO, GitHubUnavailableError, analyze_candidate
from ..services.project_links import match_repo
from ..services.resume_parser import extract_project_details, read_resume_text
from ..services.scoring import default_interview_question
from ..services.visibility import visible_candidate_id, visible_for_candidate, visible_ids
from ..skills_dictionary import (
    NOT_CHECKABLE,
    category_of,
    category_rank,
    get_skill,
    is_checkable,
)
from .resume import UPLOAD_DIR, project_row

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


def _project_detail(project: models.Project, repos: list[dict]) -> dict:
    """A resume project with its tech stack, points and (if found) its GitHub repository."""
    repo = match_repo(project.project_name, repos)
    return {
        "project_name": project.project_name,
        "description": project.description,
        "tech_stack": [t.strip() for t in (project.tech_stack or "").split(",") if t.strip()],
        "period": project.period,
        "bullets": [line.strip() for line in (project.description or "").splitlines() if line.strip()],
        "repo": {"name": repo["name"], "url": repo["url"]} if repo else None,
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
    repos = [
        {"name": r.repo_name, "url": r.repo_url, "is_fork": r.is_fork}
        for r in candidate.repositories
    ]

    skills = []
    ordered = sorted(
        candidate.skills,
        key=lambda cs: (category_rank(cs.skill.skill_name), cs.skill.skill_name.lower()),
    )
    for cs in ordered:
        name = cs.skill.skill_name
        checkable = is_checkable(name)

        if checkable:
            status, score = cs.status, cs.score
            reasons = reasons_by_skill.get(cs.skill_id, [])
            if status is not None and not reasons:
                reasons = ["No supporting evidence found in analyzed repositories"]
            question = question_by_skill.get(cs.skill_id)
        else:
            # Concept/offline skills: nothing to analyze, so show the
            # catalog's reason and question even before any analysis.
            status, score = NOT_CHECKABLE, None
            reasons = [get_skill(name)["reason"]]
            question = question_by_skill.get(cs.skill_id) or default_interview_question(name)

        skills.append(
            {
                "skill_name": name,
                "category": category_of(name),
                "checkable": checkable,
                "status": status,
                "score": score,
                "reasons": reasons,
                "interview_question": question,
                "supporting_repos": supporting_by_skill.get(cs.skill_id, []),
            }
        )

    return {
        **_candidate_summary(candidate),
        "repos_analyzed": len(candidate.repositories),
        "analyzed": analyzed,
        "skills": skills,
        "projects": [
            _project_detail(p, repos)
            for p in sorted(candidate.projects, key=lambda p: p.project_id)
        ],
    }


def _detail_for(db: Session, candidate: models.Candidate) -> dict:
    """The report, plus which of the student's resumes recruiters see."""
    visible = visible_for_candidate(db, candidate)
    return {
        **_candidate_detail(candidate),
        "visible_to_recruiters": visible == candidate.candidate_id,
        "visible_candidate_id": visible,
    }


@router.get("")
def list_candidates(
    db: Session = Depends(get_db),
    _recruiter: models.User = Depends(require_role("recruiter")),
):
    """
    Recruiter-only: every student who has uploaded a resume, each with the
    one resume they made visible to recruiters.
    """
    shown = visible_ids(db)
    candidates = (
        db.query(models.Candidate)
        .filter(models.Candidate.candidate_id.in_(shown))
        .order_by(models.Candidate.created_at.desc())
        .all()
    )
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
    visible = visible_candidate_id(db, student)
    return [
        {**_candidate_summary(c), "visible_to_recruiters": c.candidate_id == visible}
        for c in candidates
    ]


@router.put("/{candidate_id}/visible")
def make_visible(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """A student chooses which of their uploads recruiters see."""
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    if candidate.user_id is None or candidate.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only choose between your own uploads.")
    student = db.get(models.User, current_user.user_id)
    student.visible_candidate_id = candidate_id
    db.commit()
    return {"visible_candidate_id": candidate_id}


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
    return _detail_for(db, _get_visible_candidate(candidate_id, db, current_user))


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    A student deletes one of their own uploads: the resume, its report
    (skills, projects, repositories, evidence, questions, portfolio) and
    the stored PDF. Recruiters can't delete students' uploads.
    """
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    if candidate.user_id is None or candidate.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only delete your own uploads.")

    pdf = resolve_resume_path(candidate.resume_path)
    student = db.get(models.User, current_user.user_id)
    if student.visible_candidate_id == candidate_id:
        student.visible_candidate_id = None  # the newest remaining upload becomes visible
    db.query(models.ShortlistEntry).filter_by(candidate_id=candidate_id).delete()
    db.delete(candidate)
    db.commit()

    # Only remove files inside the uploads folder.
    if pdf and os.path.realpath(pdf).startswith(os.path.realpath(UPLOAD_DIR) + os.sep):
        try:
            os.remove(pdf)
        except OSError:
            pass


def resolve_resume_path(stored: str | None, upload_dir: str | None = None) -> str | None:
    """
    Where a candidate's resume PDF is now. The database keeps the full
    path from upload time, which breaks if the project folder is moved or
    re-cloned; in that case the same file name is looked up in the
    current uploads folder. None if the file can't be found.
    """
    if not stored:
        return None
    if os.path.exists(stored):
        return stored
    moved = os.path.join(upload_dir or UPLOAD_DIR, os.path.basename(stored))
    return moved if os.path.exists(moved) else None


def refresh_projects_from_resume(db: Session, candidate: models.Candidate) -> bool:
    """
    Re-read the projects from the candidate's stored resume PDF with the
    current parser, so records uploaded before a parser improvement get
    fixed by re-running the analysis. Does nothing if the file is missing
    or no projects are found. Returns True if the projects were replaced.
    """
    path = resolve_resume_path(candidate.resume_path)
    if not path:
        return False
    text = read_resume_text(path)
    projects = extract_project_details(text) if text else []
    if not projects:
        return False
    db.query(models.Project).filter_by(candidate_id=candidate.candidate_id).delete()
    for project in projects:
        db.add(project_row(candidate.candidate_id, project))
    db.flush()
    db.expire(candidate, ["projects"])
    return True


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
    refresh_projects_from_resume(db, candidate)

    try:
        await analyze_candidate(db, candidate)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except GitHubUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return _detail_for(db, candidate)
