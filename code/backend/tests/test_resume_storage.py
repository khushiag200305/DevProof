"""Resume PDFs live in the database, so a wiped uploads folder loses nothing."""
import os

from app import models
from app.services.auth import create_access_token
from app.database import SessionLocal
from app.routers.candidates import resume_pdf_bytes


def _student(email: str) -> models.User:
    with SessionLocal() as db:
        user = models.User(email=email, google_sub=f"sub-{email}", role="student")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _h(user):
    return {"Authorization": f"Bearer {create_access_token(user.user_id, user.role)}"}


def test_upload_keeps_the_pdf_in_the_database_not_on_disk(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.routers.resume.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.routers.resume.extract_text_from_pdf", lambda _b: "Khushi Agarwal\nSkills: Python")
    student = _student("store@thapar.edu")
    pdf = b"%PDF-1.4 my resume"
    body = client.post("/api/resume/upload", headers=_h(student), files={"file": ("cv.pdf", pdf, "application/pdf")}).json()

    assert os.listdir(tmp_path) == []
    with SessionLocal() as db:
        candidate = db.get(models.Candidate, body["candidate_id"])
        assert candidate.resume_pdf == pdf and candidate.resume_path is None


def test_too_large_pdf_is_refused(client, monkeypatch):
    monkeypatch.setattr("app.routers.resume.MAX_PDF_BYTES", 10)
    student = _student("big@thapar.edu")
    body = client.post(
        "/api/resume/upload", headers=_h(student), files={"file": ("cv.pdf", b"%PDF-1.4 " + b"x" * 20, "application/pdf")}
    ).json()
    assert body["status"] == "error" and "larger than" in body["error"]


def test_older_file_uploads_are_copied_into_the_database(tmp_path):
    path = tmp_path / "old_resume.pdf"
    path.write_bytes(b"%PDF-1.4 old")
    student = _student("old@thapar.edu")
    with SessionLocal() as db:
        candidate = models.Candidate(user_id=student.user_id, name="Old", resume_path=str(path))
        db.add(candidate)
        db.commit()
        assert resume_pdf_bytes(candidate) == b"%PDF-1.4 old"
        db.commit()
        cid = candidate.candidate_id

    path.unlink()  # e.g. the hosting platform wiped the folder
    with SessionLocal() as db:
        assert resume_pdf_bytes(db.get(models.Candidate, cid)) == b"%PDF-1.4 old"
