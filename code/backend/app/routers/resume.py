"""
Resume upload endpoint (Iteration 1).

Accepts a resume PDF plus an optional manual GitHub URL override (the
upload page always shows this field, since PDF text extraction from
multi-column/graphic-heavy resumes is unreliable - see Section 7 of the
proposal). Parses the PDF, extracts name/skills/projects/GitHub URL, and
persists a Candidate row (with its Skills/Projects) so later iterations
have something to attach GitHub evidence and scores to.
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.resume_parser import (
    extract_github_url,
    extract_github_username,
    extract_name,
    extract_projects,
    extract_skills,
    extract_text_from_pdf,
)

router = APIRouter(prefix="/api/resume", tags=["resume"])

# app/routers/resume.py -> app/routers -> app -> backend -> backend/uploads
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_or_create_skill(db: Session, skill_name: str) -> models.Skill:
    skill = db.query(models.Skill).filter_by(skill_name=skill_name).first()
    if skill is None:
        skill = models.Skill(skill_name=skill_name)
        db.add(skill)
        db.flush()
    return skill


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    github_url_override: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Parses an uploaded resume PDF and persists a new Candidate record.

    `github_url_override` takes precedence over whatever GitHub URL (if
    any) is found in the resume text itself.
    """
    contents = await file.read()

    try:
        text = extract_text_from_pdf(contents)
    except Exception as exc:
        return {
            "filename": file.filename,
            "status": "error",
            "error": f"Could not parse PDF: {exc}",
        }

    name = extract_name(text)
    skills = extract_skills(text)
    projects = extract_projects(text)

    github_url = (github_url_override or "").strip() or extract_github_url(text)
    github_username = extract_github_username(github_url) if github_url else None

    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    resume_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(resume_path, "wb") as out_file:
        out_file.write(contents)

    candidate = models.Candidate(
        name=name,
        resume_path=resume_path,
        github_username=github_username,
    )
    db.add(candidate)
    db.flush()  # assigns candidate.candidate_id

    for project_name in projects:
        db.add(models.Project(candidate_id=candidate.candidate_id, project_name=project_name))

    for skill_name in skills:
        skill = _get_or_create_skill(db, skill_name)
        db.add(models.CandidateSkill(candidate_id=candidate.candidate_id, skill_id=skill.skill_id))

    db.commit()

    return {
        "candidate_id": candidate.candidate_id,
        "filename": file.filename,
        "status": "parsed",
        "name": name,
        "extracted_skills": skills,
        "projects": projects,
        "github_url": github_url,
        "github_username": github_username,
    }
