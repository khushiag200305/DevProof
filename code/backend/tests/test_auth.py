"""
Tests for Google sign-in, role derivation, and session JWTs.

Google ID token verification itself isn't tested against real Google
servers (that would require a live account and network access); instead
`app.routers.auth.verify_google_id_token` is monkeypatched to return
fixed claims, the way it would after a real token was verified, so the
rest of the sign-in flow (role assignment, user creation, JWT issuance)
is exercised for real.
"""
import pytest

from app.services.auth import create_access_token, decode_access_token, derive_role


def test_derive_role_thapar_email_is_student():
    assert derive_role("someone@thapar.edu") == "student"
    assert derive_role("Someone.Else@THAPAR.EDU") == "student"


def test_derive_role_other_email_is_recruiter():
    assert derive_role("recruiter@acme.com") == "recruiter"
    assert derive_role("someone@gmail.com") == "recruiter"


def test_jwt_roundtrip():
    token = create_access_token(user_id=42, role="student")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "student"


def _fake_claims(email: str, sub: str = "google-sub-123"):
    return {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }


def test_google_sign_in_assigns_student_role_for_thapar_email(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: _fake_claims("test.student@thapar.edu"),
    )
    response = client.post("/api/auth/google", json={"credential": "fake"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "student"
    assert body["user"]["email"] == "test.student@thapar.edu"
    assert body["access_token"]


def test_google_sign_in_assigns_recruiter_role_for_non_thapar_email(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: _fake_claims("recruiter@acme.com"),
    )
    response = client.post("/api/auth/google", json={"credential": "fake"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "recruiter"


def test_google_sign_in_is_idempotent_for_the_same_google_account(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: _fake_claims("test.student@thapar.edu", sub="same-sub"),
    )
    first = client.post("/api/auth/google", json={"credential": "fake"})
    second = client.post("/api/auth/google", json={"credential": "fake"})
    assert first.json()["user"]["user_id"] == second.json()["user"]["user_id"]


def test_get_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_returns_current_user(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: _fake_claims("test.student@thapar.edu"),
    )
    token = client.post("/api/auth/google", json={"credential": "fake"}).json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test.student@thapar.edu"


@pytest.mark.parametrize("bad_token", ["not-a-jwt", ""])
def test_get_me_rejects_invalid_token(client, bad_token):
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401
