"""A student can delete one of their own uploads, with its report and PDF."""
from app import models
from app.database import SessionLocal
from app.services.auth import create_access_token


def _user(email: str, role: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(google_sub=f"sub-{email}", email=email, name="U", role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expunge(user)
        return user


def _headers(user: models.User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def _upload(owner: models.User, pdf_path: str | None = None) -> int:
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=owner.user_id, name="Khushi", resume_path=pdf_path)
        db.add(candidate)
        db.flush()
        skill = models.Skill(skill_name="Python")
        db.add(skill)
        db.flush()
        db.add(models.CandidateSkill(candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status="Strong Evidence", score=100))
        db.add(models.Project(candidate_id=candidate.candidate_id, project_name="DevProof"))
        repo = models.Repository(candidate_id=candidate.candidate_id, repo_name="devproof", repo_url="https://github.com/k/devproof", is_fork=False, commit_count=3)
        db.add(repo)
        db.flush()
        db.add(models.Evidence(candidate_id=candidate.candidate_id, skill_id=skill.skill_id, repo_id=repo.repo_id, evidence_type="source_files", description="12 Python files", weight=40))
        db.commit()
        return candidate.candidate_id


def test_student_deletes_own_upload_with_its_report_and_pdf(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.candidates.UPLOAD_DIR", str(tmp_path))
    pdf = tmp_path / "abc_resume.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    student = _user("k@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    candidate_id = _upload(student, str(pdf))
    client.put(f"/api/talent/shortlist/{candidate_id}", json={"note": "good"}, headers=_headers(recruiter))

    assert client.delete(f"/api/candidates/{candidate_id}", headers=_headers(student)).status_code == 204

    assert client.get(f"/api/candidates/{candidate_id}", headers=_headers(student)).status_code == 404
    assert client.get("/api/candidates/me", headers=_headers(student)).json() == []
    assert client.get("/api/talent/shortlist", headers=_headers(recruiter)).json() == []
    assert not pdf.exists()
    with SessionLocal() as db:
        assert db.query(models.Evidence).count() == 0
        assert db.query(models.Repository).count() == 0
        assert db.query(models.Project).count() == 0


def test_only_the_owner_can_delete(client):
    owner = _user("k@thapar.edu", "student")
    other = _user("s@thapar.edu", "student")
    recruiter = _user("hr@acme.com", "recruiter")
    candidate_id = _upload(owner)

    assert client.delete(f"/api/candidates/{candidate_id}", headers=_headers(other)).status_code == 403
    assert client.delete(f"/api/candidates/{candidate_id}", headers=_headers(recruiter)).status_code == 403
    assert client.delete("/api/candidates/9999", headers=_headers(owner)).status_code == 404
    assert client.get(f"/api/candidates/{candidate_id}", headers=_headers(owner)).status_code == 200


def test_files_outside_the_uploads_folder_are_never_removed(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.candidates.UPLOAD_DIR", str(tmp_path / "uploads"))
    outside = tmp_path / "important.pdf"
    outside.write_bytes(b"%PDF-1.4")
    student = _user("k@thapar.edu", "student")
    candidate_id = _upload(student, str(outside))

    assert client.delete(f"/api/candidates/{candidate_id}", headers=_headers(student)).status_code == 204
    assert outside.exists()
