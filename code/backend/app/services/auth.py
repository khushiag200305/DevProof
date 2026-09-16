"""
Authentication: verifying Google ID tokens, deriving a user's role from
their email domain, and issuing/reading DevProof's own short-lived
session JWTs (so the backend doesn't need to re-verify a Google token
on every request).

Role assignment is a simple, explainable rule (matches the project's
"no black-box logic" principle elsewhere): an email ending in
@thapar.edu is a student; anything else is a recruiter. This runs once,
at first sign-in - role is then stored on the User row, not
re-derived on every login (so it survives a student later signing in
from a non-Thapar address, etc.).
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

# Loaded here too (not just in app/main.py): this module reads
# GOOGLE_CLIENT_ID/JWT_SECRET from the environment below, at import
# time, and it's imported transitively by several routers - relying on
# main.py's own load_dotenv() running first is fragile to import
# reordering (it broke exactly this way once already).
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7

STUDENT_EMAIL_DOMAIN = "@thapar.edu"


class GoogleTokenError(ValueError):
    """Raised when a Google ID token fails verification."""


def verify_google_id_token(credential: str) -> dict:
    """
    Verifies a Google Identity Services ID token (the `credential` the
    frontend's GoogleLogin button receives) against our OAuth client ID,
    and returns the decoded claims (email, name, picture, sub, ...).
    """
    if not GOOGLE_CLIENT_ID:
        raise GoogleTokenError(
            "GOOGLE_CLIENT_ID is not configured on the backend (set it in .env)."
        )
    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise GoogleTokenError(f"Invalid Google ID token: {exc}") from exc

    if not claims.get("email_verified", False):
        raise GoogleTokenError("Google account email is not verified.")

    return claims


def derive_role(email: str) -> str:
    """@thapar.edu -> student, everything else -> recruiter."""
    return "student" if email.lower().endswith(STUDENT_EMAIL_DOMAIN) else "recruiter"


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


class InvalidTokenError(ValueError):
    """Raised when a DevProof session token is missing/expired/invalid."""


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
