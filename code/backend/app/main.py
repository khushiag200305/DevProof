"""
DevProof backend entrypoint.

Iteration 1 (Weeks 1-2) scope:
- Basic FastAPI app with a health check
- Resume upload endpoint (to be wired to pdfplumber parsing)
- GitHub URL / skill extraction (stub)

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DevProof API", version="0.1.0")

# Allow the local Vite dev server to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Basic liveness check used by CI and manual smoke testing."""
    return {"status": "ok", "service": "devproof-backend"}


@app.post("/resumes/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts a resume PDF and (eventually) runs extraction.

    TODO (Iteration 1):
    - Save/parse the PDF with pdfplumber
    - Extract candidate name, GitHub link(s), and raw skill mentions
    - Normalize skill names against the curated mapping
    """
    contents = await file.read()
    return {
        "filename": file.filename,
        "size_bytes": len(contents),
        "status": "received - parsing not yet implemented",
    }
