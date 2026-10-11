"""
FastAPI dependencies for authenticated routes: resolving the current
user from a Bearer session token, and gating routes by role.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
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


def require_role(role: str):
    """Dependency factory: 403s unless the current user has `role`."""

    def _check(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != role:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"This action requires the '{role}' role."
            )
        return user

    return _check
