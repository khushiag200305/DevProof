"""
Recruiter approval. Students (@thapar.edu) are trusted automatically, but
any other Google account becomes a recruiter, so recruiters must be
approved by an admin before they can see students' data.

Settings (backend .env, comma-separated, read on every check):
    ADMIN_EMAILS                   who can approve recruiters, e.g. you@gmail.com
    RECRUITER_AUTO_APPROVE_DOMAINS company domains approved automatically, e.g. acme.com

users.recruiter_status is "pending", "approved" or "rejected". It is
empty for recruiters who signed up before approval existed; they count
as approved so existing setups keep working. Admins are always approved.
"""
import os

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
STATUSES = (PENDING, APPROVED, REJECTED)


def _setting(name: str) -> set[str]:
    return {part.strip().lower() for part in os.getenv(name, "").split(",") if part.strip()}


def admin_emails() -> set[str]:
    return _setting("ADMIN_EMAILS")


def auto_approve_domains() -> set[str]:
    return {d.lstrip("@") for d in _setting("RECRUITER_AUTO_APPROVE_DOMAINS")}


def is_admin_email(email: str | None) -> bool:
    return bool(email) and email.lower() in admin_emails()


def initial_status(email: str, role: str) -> str | None:
    """Status for a newly created user: students need none."""
    if role != "recruiter":
        return None
    domain = email.lower().rsplit("@", 1)[-1]
    if is_admin_email(email) or domain in auto_approve_domains():
        return APPROVED
    return PENDING


def effective_status(user) -> str | None:
    """None for students; otherwise the recruiter's status (admins and old accounts: approved)."""
    if user.role != "recruiter":
        return None
    if is_admin_email(user.email):
        return APPROVED
    return user.recruiter_status or APPROVED
