"""
Which of a student's resumes recruiters see.

A student can upload several resumes but only one is "visible to
recruiters" at a time. The choice is stored on the user
(users.visible_candidate_id). If it's unset, or points to an upload that
was deleted, the student's newest upload is the visible one. Uploads
without an account (from before sign-in existed) are always visible.
"""
from sqlalchemy.orm import Session

from .. import models


def resolve_visible(chosen_id: int | None, uploads: list[tuple[int, object]]) -> int | None:
    """
    Pure rule: given the stored choice and a user's uploads as
    (candidate_id, created_at) pairs, the id recruiters see.
    """
    if not uploads:
        return None
    ids = {cid for cid, _ in uploads}
    if chosen_id in ids:
        return chosen_id
    return max(uploads, key=lambda u: (u[1], u[0]))[0]


def visible_candidate_id(db: Session, user: models.User) -> int | None:
    uploads = (
        db.query(models.Candidate.candidate_id, models.Candidate.created_at)
        .filter(models.Candidate.user_id == user.user_id)
        .all()
    )
    return resolve_visible(user.visible_candidate_id, [(u.candidate_id, u.created_at) for u in uploads])


def visible_ids(db: Session) -> set[int]:
    """Every candidate id recruiters should see: one per student, plus account-less uploads."""
    rows = db.query(
        models.Candidate.candidate_id, models.Candidate.user_id, models.Candidate.created_at
    ).all()
    chosen = dict(db.query(models.User.user_id, models.User.visible_candidate_id).all())

    by_user: dict[int, list[tuple[int, object]]] = {}
    out: set[int] = set()
    for r in rows:
        if r.user_id is None:
            out.add(r.candidate_id)
        else:
            by_user.setdefault(r.user_id, []).append((r.candidate_id, r.created_at))
    for user_id, uploads in by_user.items():
        visible = resolve_visible(chosen.get(user_id), uploads)
        if visible is not None:
            out.add(visible)
    return out


def visible_for_candidate(db: Session, candidate: models.Candidate) -> int | None:
    """The upload recruiters see for this candidate's student (itself if account-less)."""
    if candidate.user_id is None:
        return candidate.candidate_id
    user = db.get(models.User, candidate.user_id)
    return visible_candidate_id(db, user) if user else candidate.candidate_id
