"""
FastAPI dependencies for authenticated routes: resolving the current
user from a Bearer session token, and gating routes by role.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .services.approval import APPROVED, effective_status, is_admin_email
from .services.auth import InvalidTokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid session: {exc}") from exc

    user = db.query(models.User).filter_by(user_id=int(payload["sub"])).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")
    return user


def ensure_approved(user: models.User) -> None:
    """403s for a recruiter an admin hasn't approved yet (or rejected)."""
    if user.role == "recruiter" and effective_status(user) != APPROVED:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your recruiter account is waiting for approval."
            if effective_status(user) == "pending"
            else "Your recruiter account was not approved.",
        )


def get_approved_user(user: models.User = Depends(get_current_user)) -> models.User:
    """The current user, refusing recruiters who aren't approved yet."""
    ensure_approved(user)
    return user


def require_role(role: str):
    """Dependency factory: 403s unless the current user has `role` (recruiters must be approved)."""

    def _check(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != role:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"This action requires the '{role}' role."
            )
        ensure_approved(user)
        return user

    return _check


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """403s unless the current user's email is in ADMIN_EMAILS."""
    if not is_admin_email(user.email):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This action requires an admin.")
    return user
