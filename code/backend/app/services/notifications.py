"""
In-app notifications (the bell in the top bar).

Events and who hears about them:
    analysis_ready     student: their GitHub analysis finished
    shortlisted        student: a recruiter shortlisted them
    portfolio_viewed   student: someone opened their public portfolio (at most once a day)
    search_match       recruiter: a student newly matches one of their saved searches
    recruiter_request  admins: a new recruiter is waiting for approval
    recruiter_approved recruiter: an admin approved their account

Helpers add rows to the session; the caller commits.
"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from . import talent_search
from .approval import admin_emails
from .visibility import visible_for_candidate


def notify(
    db: Session,
    user_id: int,
    kind: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
    dedupe_key: str | None = None,
) -> models.Notification | None:
    """Queue a notification; with a dedupe_key, skip it if this user already had one."""
    if dedupe_key and (
        db.query(models.Notification.notification_id).filter_by(user_id=user_id, dedupe_key=dedupe_key).first()
    ):
        return None
    note = models.Notification(
        user_id=user_id, kind=kind, title=title, body=body, link=link, dedupe_key=dedupe_key
    )
    db.add(note)
    db.flush()
    return note


def _display(candidate: models.Candidate) -> str:
    return candidate.name or f"Candidate #{candidate.candidate_id}"


def analysis_ready(db: Session, candidate: models.Candidate) -> None:
    if candidate.user_id is None:
        return
    proven = sum(1 for cs in candidate.skills if cs.status in ("Strong Evidence", "Good Evidence"))
    notify(
        db, candidate.user_id, "analysis_ready", "Your GitHub analysis is ready",
        f"{proven} of {len(candidate.skills)} skills on your resume are backed by GitHub.",
        f"/candidate/{candidate.candidate_id}",
    )


def shortlisted(db: Session, candidate: models.Candidate, recruiter: models.User) -> None:
    if candidate.user_id is None:
        return
    domain = recruiter.email.rsplit("@", 1)[-1]
    notify(
        db, candidate.user_id, "shortlisted", "A recruiter shortlisted you",
        f"A recruiter from {domain} added your resume to their shortlist.",
        f"/candidate/{candidate.candidate_id}",
        dedupe_key=f"shortlisted:{recruiter.user_id}",
    )


def portfolio_viewed(db: Session, candidate: models.Candidate, now: datetime | None = None) -> None:
    """At most one notification per student per day, however many views."""
    if candidate.user_id is None:
        return
    now = now or datetime.now(timezone.utc)
    recent = (
        db.query(models.Notification.notification_id)
        .filter(
            models.Notification.user_id == candidate.user_id,
            models.Notification.kind == "portfolio_viewed",
            models.Notification.created_at >= now - timedelta(days=1),
        )
        .first()
    )
    if recent:
        return
    notify(
        db, candidate.user_id, "portfolio_viewed", "Someone viewed your portfolio",
        "Your public portfolio page was opened.", f"/candidate/{candidate.candidate_id}",
    )


def new_search_matches(db: Session, candidate: models.Candidate) -> int:
    """
    Tell recruiters when this candidate (if it's the resume recruiters
    see) matches one of their saved searches. Each student is announced
    once per saved search. Returns how many notifications were queued.
    """
    if visible_for_candidate(db, candidate) != candidate.candidate_id:
        return 0
    from ..routers.talent import _profile  # imported here to avoid a circular import

    profile = _profile(candidate)
    person = f"user{candidate.user_id}" if candidate.user_id else f"candidate{candidate.candidate_id}"
    sent = 0
    for saved in db.query(models.SavedSearch).all():
        if not talent_search.search([profile], json.loads(saved.query)):
            continue
        if notify(
            db, saved.recruiter_id, "search_match", f"New match for \"{saved.name}\"",
            f"{_display(candidate)} matches your saved search.",
            f"/candidate/{candidate.candidate_id}",
            dedupe_key=f"match:{saved.search_id}:{person}",
        ):
            sent += 1
    return sent


def recruiter_requested(db: Session, recruiter: models.User) -> None:
    emails = admin_emails()
    admins = db.query(models.User).filter(func.lower(models.User.email).in_(emails)).all() if emails else []
    for admin in admins:
        notify(
            db, admin.user_id, "recruiter_request", "New recruiter request",
            f"{recruiter.name or recruiter.email} ({recruiter.email}) is waiting for approval.",
            "/admin", dedupe_key=f"request:{recruiter.user_id}",
        )


def recruiter_approved(db: Session, recruiter: models.User) -> None:
    notify(
        db, recruiter.user_id, "recruiter_approved", "Your recruiter account was approved",
        "You can now search and review student reports.", "/dashboard",
        dedupe_key="approved",
    )


def as_dict(note: models.Notification) -> dict:
    return {
        "notification_id": note.notification_id,
        "kind": note.kind,
        "title": note.title,
        "body": note.body,
        "link": note.link,
        "created_at": note.created_at,
        "read": note.read_at is not None,
    }
