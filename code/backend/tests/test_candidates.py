"""
Tests for role-gated candidate access: recruiters can list/open any
candidate, a student can only see their own.
"""
from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token


def _make_user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(
            google_sub=f"sub-{email}",
            email=email,
            name=email.split("@")[0],
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _make_candidate(user_id: int, name: str) -> models.Candidate:
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=user_id, name=name, github_username="octocat")
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        db.expunge(candidate)
        return candidate


def _auth_headers(user: models.User) -> dict:
    token = create_access_token(user.user_id, user.role)
    return {"Authorization": f"Bearer {token}"}


def test_recruiter_can_list_all_candidates(client):
    student = _make_user("s1@thapar.edu", "student")
    recruiter = _make_user("r1@acme.com", "recruiter")
    _make_candidate(student.user_id, "Aditi Sharma")

    response = client.get("/api/candidates", headers=_auth_headers(recruiter))
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "Aditi Sharma" in names


def test_student_cannot_list_all_candidates(client):
    student = _make_user("s2@thapar.edu", "student")
    response = client.get("/api/candidates", headers=_auth_headers(student))
    assert response.status_code == 403


def test_student_sees_only_their_own_candidates_via_me(client):
    student_a = _make_user("a@thapar.edu", "student")
    student_b = _make_user("b@thapar.edu", "student")
    _make_candidate(student_a.user_id, "Student A Resume")
    _make_candidate(student_b.user_id, "Student B Resume")

    response = client.get("/api/candidates/me", headers=_auth_headers(student_a))
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["Student A Resume"]


def test_recruiter_cannot_use_me_endpoint(client):
    recruiter = _make_user("r2@acme.com", "recruiter")
    response = client.get("/api/candidates/me", headers=_auth_headers(recruiter))
    assert response.status_code == 403


def test_recruiter_can_open_any_candidate_detail(client):
    student = _make_user("s3@thapar.edu", "student")
    recruiter = _make_user("r3@acme.com", "recruiter")
    candidate = _make_candidate(student.user_id, "Candidate Three")

    response = client.get(
        f"/api/candidates/{candidate.candidate_id}", headers=_auth_headers(recruiter)
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Candidate Three"


def test_student_cannot_open_another_students_candidate(client):
    owner = _make_user("owner@thapar.edu", "student")
    other = _make_user("other@thapar.edu", "student")
    candidate = _make_candidate(owner.user_id, "Owner's Candidate")

    response = client.get(
        f"/api/candidates/{candidate.candidate_id}", headers=_auth_headers(other)
    )
    assert response.status_code == 403


def test_student_can_open_their_own_candidate(client):
    owner = _make_user("owner2@thapar.edu", "student")
    candidate = _make_candidate(owner.user_id, "Owner Two's Candidate")

    response = client.get(
        f"/api/candidates/{candidate.candidate_id}", headers=_auth_headers(owner)
    )
    assert response.status_code == 200


def test_get_candidate_404_for_missing_id(client):
    recruiter = _make_user("r4@acme.com", "recruiter")
    response = client.get("/api/candidates/999999", headers=_auth_headers(recruiter))
    assert response.status_code == 404


def test_upload_requires_student_role(client):
    recruiter = _make_user("r5@acme.com", "recruiter")
    response = client.post(
        "/api/resume/upload",
        headers=_auth_headers(recruiter),
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 403


def test_upload_requires_authentication(client):
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 401
