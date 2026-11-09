"""
Recruiter talent search: search candidates by proven skills, save
searches, keep a shortlist with private notes, and compare candidates
side by side. All endpoints are recruiter-only; the matching itself is
in app/services/talent_search.py.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db
from ..dependencies import require_role
from ..services import talent_search
from ..services.visibility import visible_for_candidate, visible_ids
from ..skills_dictionary import category_of

router = APIRouter(prefix="/api/talent", tags=["talent"])

recruiter_only = require_role("recruiter")

MAX_COMPARE = 4


class SearchQuery(BaseModel):
    skills: list[str] = Field(default_factory=list, max_length=20)
    min_level: str = "good"
    match: str = "all"
    has_github: bool = False
    min_repos: int = Field(default=0, ge=0, le=100)
    active_months: int | None = Field(default=None, ge=1, le=60)
    text: str = Field(default="", max_length=100)


class SavedSearchIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    query: SearchQuery


class ShortlistIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


def _profile(candidate: models.Candidate) -> dict:
    """A candidate as the plain dict talent_search works on."""
    return {
        "candidate_id": candidate.candidate_id,
        "user_id": candidate.user_id,
        "name": candidate.name,
        "email": candidate.email,
        "github_username": candidate.github_username,
        "created_at": candidate.created_at,
        "skills": {
            cs.skill.skill_name: {
                "status": cs.status,
                "score": cs.score,
                "category": category_of(cs.skill.skill_name),
            }
            for cs in candidate.skills
        },
        "repos": [
            {
                "name": r.repo_name,
                "is_fork": r.is_fork,
                "pushed_at": (r.detail.pushed_at if r.detail and r.detail.pushed_at else r.last_updated),
            }
            for r in candidate.repositories
        ],
    }


def _load_candidates(db: Session, ids: list[int] | None = None) -> list[models.Candidate]:
    q = db.query(models.Candidate).options(
        selectinload(models.Candidate.skills).selectinload(models.CandidateSkill.skill),
        selectinload(models.Candidate.repositories).selectinload(models.Repository.detail),
    )
    if ids is not None:
        q = q.filter(models.Candidate.candidate_id.in_(ids))
    return q.all()


def _searchable_profiles(db: Session) -> list[dict]:
    """
    One profile per student: the resume they made visible to recruiters.
    Uploads without an account are grouped by person instead.
    """
    shown = visible_ids(db)
    profiles = [_profile(c) for c in _load_candidates(db, list(shown))]
    owned = [p for p in profiles if p["user_id"] is not None]
    loose = [p for p in profiles if p["user_id"] is None]
    return owned + talent_search.latest_per_student(loose)


def _starred(db: Session, recruiter: models.User) -> tuple[set[int], set[int]]:
    """Shortlisted candidate ids, and the students they belong to."""
    rows = (
        db.query(models.ShortlistEntry.candidate_id, models.Candidate.user_id)
        .join(models.Candidate, models.Candidate.candidate_id == models.ShortlistEntry.candidate_id)
        .filter(models.ShortlistEntry.recruiter_id == recruiter.user_id)
        .all()
    )
    return {r.candidate_id for r in rows}, {r.user_id for r in rows if r.user_id is not None}


def _run_search(db: Session, recruiter: models.User, query: dict) -> list[dict]:
    profiles = _searchable_profiles(db)
    owner = {p["candidate_id"]: p["user_id"] for p in profiles}
    results = talent_search.search(profiles, query)
    starred_ids, starred_users = _starred(db, recruiter)
    for r in results:
        # A shortlist follows the student, whichever resume they now show.
        r["shortlisted"] = r["candidate_id"] in starred_ids or owner.get(r["candidate_id"]) in starred_users
    return results


def _same_student_ids(db: Session, candidate: models.Candidate) -> list[int]:
    """All upload ids of this candidate's student (just itself if account-less)."""
    if candidate.user_id is None:
        return [candidate.candidate_id]
    rows = db.query(models.Candidate.candidate_id).filter_by(user_id=candidate.user_id).all()
    return [r.candidate_id for r in rows]


def _saved_dict(saved: models.SavedSearch) -> dict:
    return {
        "search_id": saved.search_id,
        "name": saved.name,
        "query": talent_search.normalize_query(json.loads(saved.query)),
        "created_at": saved.created_at,
        "last_run_at": saved.last_run_at,
    }


def _get_saved(db: Session, recruiter: models.User, search_id: int) -> models.SavedSearch:
    saved = db.query(models.SavedSearch).filter_by(search_id=search_id).first()
    if saved is None or saved.recruiter_id != recruiter.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved search not found.")
    return saved


@router.get("/skills")
def list_skills(db: Session = Depends(get_db), _r: models.User = Depends(recruiter_only)):
    """Skill names that at least one candidate claims, for the search box suggestions."""
    rows = (
        db.query(models.Skill.skill_name)
        .join(models.CandidateSkill, models.CandidateSkill.skill_id == models.Skill.skill_id)
        .distinct()
        .all()
    )
    return sorted((r.skill_name for r in rows), key=str.lower)


@router.post("/search")
def search(
    body: SearchQuery,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    """Candidates matching the query, best match first."""
    return _run_search(db, recruiter, body.model_dump())


# --- Saved searches -------------------------------------------------------


@router.get("/saved-searches")
def list_saved(db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    """This recruiter's saved searches, each with how many new candidates match since it last ran."""
    saved = (
        db.query(models.SavedSearch)
        .filter_by(recruiter_id=recruiter.user_id)
        .order_by(models.SavedSearch.created_at.desc())
        .all()
    )
    if not saved:
        return []
    profiles = _searchable_profiles(db)
    out = []
    for s in saved:
        item = _saved_dict(s)
        results = talent_search.mark_new(talent_search.search(profiles, item["query"]), s.last_run_at)
        item["match_count"] = len(results)
        item["new_count"] = sum(1 for r in results if r["is_new"])
        out.append(item)
    return out


@router.post("/saved-searches", status_code=status.HTTP_201_CREATED)
def create_saved(
    body: SavedSearchIn,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    saved = models.SavedSearch(
        recruiter_id=recruiter.user_id,
        name=body.name.strip(),
        query=json.dumps(body.query.model_dump()),
        last_run_at=datetime.now(timezone.utc),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    item = _saved_dict(saved)
    item["match_count"] = len(_run_search(db, recruiter, item["query"]))
    item["new_count"] = 0
    return item


@router.post("/saved-searches/{search_id}/run")
def run_saved(
    search_id: int,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    """Re-run a saved search. Candidates new since the last run are flagged `is_new`."""
    saved = _get_saved(db, recruiter, search_id)
    item = _saved_dict(saved)
    results = talent_search.mark_new(_run_search(db, recruiter, item["query"]), saved.last_run_at)
    saved.last_run_at = datetime.now(timezone.utc)
    db.commit()
    return {"search": _saved_dict(saved), "results": results}


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved(
    search_id: int,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    db.delete(_get_saved(db, recruiter, search_id))
    db.commit()


# --- Shortlist ------------------------------------------------------------


@router.get("/shortlist")
def list_shortlist(db: Session = Depends(get_db), recruiter: models.User = Depends(recruiter_only)):
    entries = (
        db.query(models.ShortlistEntry)
        .filter_by(recruiter_id=recruiter.user_id)
        .order_by(models.ShortlistEntry.created_at.desc())
        .all()
    )
    # Show each shortlisted student's currently visible resume.
    shown_for = {
        e.candidate_id: visible_for_candidate(db, e.candidate) or e.candidate_id for e in entries
    }
    by_id = {c.candidate_id: c for c in _load_candidates(db, list(set(shown_for.values())))}
    out = []
    seen: set[int] = set()
    for e in entries:
        candidate = by_id.get(shown_for[e.candidate_id])
        if candidate is None or candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        profile = _profile(candidate)
        backed = [
            {"skill": name, "status": info["status"], "score": info["score"]}
            for name, info in sorted(profile["skills"].items(), key=lambda kv: -(kv[1]["score"] or 0))
            if info["status"] in (talent_search.STRONG, talent_search.GOOD)
        ]
        out.append(
            {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "github_username": candidate.github_username,
                "note": e.note,
                "added_at": e.created_at,
                "skill_count": len(profile["skills"]),
                "backed_skills": backed,
            }
        )
    return out


@router.put("/shortlist/{candidate_id}")
def add_to_shortlist(
    candidate_id: int,
    body: ShortlistIn,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    """
    Star a candidate, or update the note on one already starred. The
    shortlist is per student: starring another resume of the same student
    moves the existing entry (and its note) instead of adding a second.
    """
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    existing = (
        db.query(models.ShortlistEntry)
        .filter(
            models.ShortlistEntry.recruiter_id == recruiter.user_id,
            models.ShortlistEntry.candidate_id.in_(_same_student_ids(db, candidate)),
        )
        .all()
    )
    for old in existing:
        db.delete(old)
    db.flush()
    entry = models.ShortlistEntry(
        recruiter_id=recruiter.user_id,
        candidate_id=candidate_id,
        created_at=min((e.created_at for e in existing), default=datetime.now(timezone.utc)),
    )
    entry.note = (body.note or "").strip() or None
    db.add(entry)
    db.commit()
    return {"candidate_id": candidate_id, "note": entry.note, "shortlisted": True}


@router.delete("/shortlist/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_shortlist(
    candidate_id: int,
    db: Session = Depends(get_db),
    recruiter: models.User = Depends(recruiter_only),
):
    candidate = db.query(models.Candidate).filter_by(candidate_id=candidate_id).first()
    ids = _same_student_ids(db, candidate) if candidate else [candidate_id]
    db.query(models.ShortlistEntry).filter(
        models.ShortlistEntry.recruiter_id == recruiter.user_id,
        models.ShortlistEntry.candidate_id.in_(ids),
    ).delete(synchronize_session=False)
    db.commit()


# --- Compare --------------------------------------------------------------


@router.get("/compare")
def compare(
    ids: str = Query(..., description="Comma-separated candidate ids, 2 to 4"),
    db: Session = Depends(get_db),
    _r: models.User = Depends(recruiter_only),
):
    """Skills of 2-4 candidates side by side."""
    try:
        wanted = list(dict.fromkeys(int(i) for i in ids.split(",") if i.strip()))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ids must be numbers.") from exc
    if not 2 <= len(wanted) <= MAX_COMPARE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Pick between 2 and {MAX_COMPARE} candidates."
        )
    by_id = {c.candidate_id: c for c in _load_candidates(db, wanted)}
    missing = [i for i in wanted if i not in by_id]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Candidate {missing[0]} not found.")
    return talent_search.compare([_profile(by_id[i]) for i in wanted])
