"""
DevProof backend entrypoint.

Iteration 1 (Weeks 1-2) scope:
- FastAPI app with a health check
- Resume upload endpoint: extracts raw text (PyMuPDF), then pulls out
  candidate skills (against a curated mapping) and any GitHub links.

Run with:
    uvicorn app.main:app --reload
"""
import httpx
import re
import pymupdf as fitz  # PyMuPDF (modern import name; fitz is deprecated)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DevProof API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Curated mapping: variant phrasing -> normalized skill name.
# Matches Section 3.1 of the proposal (initial supported technology set).
SKILL_ALIASES = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express",
    "expressjs": "Express",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "django": "Django",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
}

GITHUB_URL_PATTERN = re.compile(
    r"(?<![\w.])(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)?",
    re.IGNORECASE,
)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF's bytes using PyMuPDF."""
    text_parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def extract_skills(text: str) -> list[str]:
    """
    Find mentions of known skills in resume text.

    Uses lookaround assertions instead of \b, since \b is unreliable
    right after punctuation characters (e.g. it fails to correctly
    bound "C++", which ends in non-word characters). This checks that
    the alias isn't immediately preceded/followed by another letter,
    digit, or underscore, which achieves a correct "whole token" match
    regardless of what the alias itself contains.
    """
    lower_text = text.lower()
    found = set()
    for alias, normalized in SKILL_ALIASES.items():
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, lower_text):
            found.add(normalized)
    return sorted(found)


def extract_github_links(text: str) -> list[str]:
    """Find GitHub profile/repo URLs mentioned in resume text."""
    matches = GITHUB_URL_PATTERN.findall(text)
    # findall with a non-capturing outer group still returns full matches
    # here since there's no capturing group inside; dedupe just in case.
    return sorted(set(GITHUB_URL_PATTERN.findall(text))) if False else sorted(
        set(m for m in GITHUB_URL_PATTERN.findall(text))
    )
def extract_github_username(github_link: str) -> str | None:
    """
    Pull the username out of a github.com link.

    Handles links with or without a protocol/www prefix, e.g.:
    'github.com/khushiag200305' -> 'khushiag200305'
    'https://github.com/khushiag200305/DevProof' -> 'khushiag200305'
    """
    match = re.search(r"github\.com/([A-Za-z0-9_-]+)", github_link, re.IGNORECASE)
    return match.group(1) if match else None


async def fetch_github_repos(username: str) -> list[dict]:
    """
    Fetch a user's public repositories from the GitHub REST API.

    Returns a simplified list with just the fields DevProof's evidence
    engine needs: name, primary language, fork status, and last-updated
    date. No auth token is used, which caps requests at 60/hour per IP
    (GitHub's unauthenticated rate limit) - fine for pilot-scale use.
    """
    url = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": 100, "sort": "updated"}
    headers = {"Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)

    if response.status_code == 404:
        return []
    response.raise_for_status()

    repos = response.json()
    return [
        {
            "name": repo["name"],
            "language": repo["language"],
            "is_fork": repo["fork"],
            "stars": repo["stargazers_count"],
            "updated_at": repo["updated_at"],
            "url": repo["html_url"],
        }
        for repo in repos
    ]


@app.get("/health")
def health_check():
    """Basic liveness check used by CI and manual smoke testing."""
    return {"status": "ok", "service": "devproof-backend"}


@app.post("/resumes/upload")
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts a resume PDF, extracts text, and returns detected skills
    and GitHub links found in that text.
    """
    contents = await file.read()

    try:
        text = extract_text_from_pdf(contents)
    except Exception as exc:
        return {
            "filename": file.filename,
            "status": "error",
            "error": f"Could not parse PDF: {exc}",
        }

    skills = extract_skills(text)
    github_links = extract_github_links(text)

    return {
        "filename": file.filename,
        "size_bytes": len(contents),
        "status": "parsed",
        "extracted_skills": skills,
        "github_links": github_links,
        "text_preview": text[:300],
    }
@app.get("/github/{username}/repos")
async def get_github_repos(username: str):
    """
    Returns simplified public repository evidence for a GitHub username.
    Used by the frontend to show repo-level evidence for a candidate
    after their resume has been parsed.
    """
    try:
        repos = await fetch_github_repos(username)
    except httpx.HTTPStatusError as exc:
        return {
            "username": username,
            "status": "error",
            "error": f"GitHub API error: {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return {
            "username": username,
            "status": "error",
            "error": f"Network error contacting GitHub: {exc}",
        }

    return {
        "username": username,
        "status": "ok",
        "repo_count": len(repos),
        "repos": repos,
    }