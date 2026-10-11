"""
Google sign-in endpoint and current-user lookup.

The frontend's Google Identity Services button returns an ID token
("credential") directly to the browser - the backend never sees a
Google password or OAuth client secret. We verify that token's
signature against our OAuth client ID, resolve or create a User (role
derived from email domain on first sign-in only), and return our own
short-lived session JWT for the frontend to use on subsequent requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..services.auth import (
    GoogleTokenError,
    create_access_token,
    derive_role,
    verify_google_id_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class GoogleSignInRequest(BaseModel):
    credential: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    name: str | None
    picture_url: str | None
    role: str


class SignInResponse(BaseModel):
    access_token: str
    user: UserOut


@router.post("/google", response_model=SignInResponse)
def sign_in_with_google(body: GoogleSignInRequest, db: Session = Depends(get_db)):
    try:
        claims = verify_google_id_token(body.credential)
    except GoogleTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    google_sub = claims["sub"]
    email = claims["email"]

    user = db.query(models.User).filter_by(google_sub=google_sub).first()
    if user is None:
        user = models.User(
            google_sub=google_sub,
            email=email,
            name=claims.get("name"),
            picture_url=claims.get("picture"),
            role=derive_role(email),
        )
        db.add(user)
    else:
        # Keep display fields fresh; role is intentionally left as-is
        # once assigned (see module docstring).
        user.name = claims.get("name")
        user.picture_url = claims.get("picture")

    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id, user.role)
    return SignInResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
