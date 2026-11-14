"""
Recruiter approval: new recruiters wait for an admin (ADMIN_EMAILS)
before they can see students' data; trusted company domains are
approved automatically; students and old accounts are unaffected.
"""
from app import models
from app.database import SessionLocal

ADMIN = "khushi@gmail.com"


def _sign_in(client, monkeypatch, email: str, sub: str) -> dict:
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda credential: {"sub": sub, "email": email, "email_verified": True, "name": email.split("@")[0], "picture": None},
    )
    body = client.post("/api/auth/google", json={"credential": "fake"}).json()
    return {"user": body["user"], "h": {"Authorization": f"Bearer {body['access_token']}"}}


def test_new_recruiter_waits_until_an_admin_approves(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", ADMIN)
    recruiter = _sign_in(client, monkeypatch, "hr@acme.com", "sub-hr")
    assert recruiter["user"]["recruiter_status"] == "pending"
    assert recruiter["user"]["is_admin"] is False

    # Blocked from student data, but can still check their own status.
    assert client.get("/api/candidates", headers=recruiter["h"]).status_code == 403
    assert client.post("/api/talent/search", json={}, headers=recruiter["h"]).status_code == 403
    me = client.get("/api/auth/me", headers=recruiter["h"]).json()
    assert me["recruiter_status"] == "pending"

    admin = _sign_in(client, monkeypatch, ADMIN, "sub-admin")
    assert admin["user"]["is_admin"] is True and admin["user"]["recruiter_status"] == "approved"

    listed = client.get("/api/admin/recruiters", headers=admin["h"]).json()
    assert [(r["email"], r["status"], r["domain"]) for r in listed] == [("hr@acme.com", "pending", "acme.com")]

    rid = listed[0]["user_id"]
    assert client.put(f"/api/admin/recruiters/{rid}", json={"status": "approved"}, headers=admin["h"]).status_code == 200
    assert client.get("/api/candidates", headers=recruiter["h"]).status_code == 200

    client.put(f"/api/admin/recruiters/{rid}", json={"status": "rejected"}, headers=admin["h"])
    response = client.get("/api/candidates", headers=recruiter["h"])
    assert response.status_code == 403
    assert "not approved" in response.json()["detail"]


def test_only_admins_can_manage_recruiters(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", ADMIN)
    recruiter = _sign_in(client, monkeypatch, "hr@acme.com", "sub-hr")
    student = _sign_in(client, monkeypatch, "k@thapar.edu", "sub-student")
    assert client.get("/api/admin/recruiters", headers=recruiter["h"]).status_code == 403
    assert client.get("/api/admin/recruiters", headers=student["h"]).status_code == 403

    admin = _sign_in(client, monkeypatch, ADMIN, "sub-admin")
    rid = recruiter["user"]["user_id"]
    assert client.put(f"/api/admin/recruiters/{rid}", json={"status": "maybe"}, headers=admin["h"]).status_code == 422
    assert client.put("/api/admin/recruiters/9999", json={"status": "approved"}, headers=admin["h"]).status_code == 404
    assert client.put(
        f"/api/admin/recruiters/{admin['user']['user_id']}", json={"status": "rejected"}, headers=admin["h"]
    ).status_code in (400, 404)


def test_trusted_company_domains_are_approved_automatically(client, monkeypatch):
    monkeypatch.setenv("RECRUITER_AUTO_APPROVE_DOMAINS", "acme.com, @infosys.com")
    acme = _sign_in(client, monkeypatch, "hr@acme.com", "sub-acme")
    other = _sign_in(client, monkeypatch, "hr@infosys.com", "sub-infosys")
    gmail = _sign_in(client, monkeypatch, "someone@gmail.com", "sub-gmail")
    assert acme["user"]["recruiter_status"] == "approved"
    assert other["user"]["recruiter_status"] == "approved"
    assert gmail["user"]["recruiter_status"] == "pending"


def test_students_and_existing_recruiters_are_unaffected(client, monkeypatch):
    student = _sign_in(client, monkeypatch, "k@thapar.edu", "sub-student")
    assert student["user"]["recruiter_status"] is None
    assert client.get("/api/candidates/me", headers=student["h"]).status_code == 200

    # A recruiter created before approval existed (no status stored) counts as approved.
    with SessionLocal() as db:
        db.add(models.User(google_sub="sub-old", email="old@acme.com", name="Old", role="recruiter"))
        db.commit()
    old = _sign_in(client, monkeypatch, "old@acme.com", "sub-old")
    assert old["user"]["recruiter_status"] == "approved"
    assert client.get("/api/candidates", headers=old["h"]).status_code == 200


def test_legacy_endpoints_need_an_approved_recruiter(client):
    assert client.post("/score", json={"username": "octocat", "skills": ["Python"]}).status_code == 401
    assert client.get("/github/octocat/repos").status_code == 401
