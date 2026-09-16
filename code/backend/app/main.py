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
import base64
import os
import pymupdf as fitz  # PyMuPDF (modern import name; fitz is deprecated)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()


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

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

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
   

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=GITHUB_HEADERS, timeout=10.0)

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


# Per-technology detection rules: which files to look for, and (for
# text-based files) which keywords inside them count as evidence.
# Mirrors the "concrete signals" concept from Section 3.3 of the proposal.
FINGERPRINT_RULES = {
    "Docker": {"files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]},
    "React": {"files": ["package.json"], "keywords": ["\"react\"", "\"react-dom\""]},
    "Express": {"files": ["package.json"], "keywords": ["\"express\""]},
    "Node.js": {"files": ["package.json"], "keywords": []},
    "Flask": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["flask"]},
    "FastAPI": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["fastapi"]},
    "Django": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["django"]},
}


async def fetch_repo_root_files(owner: str, repo: str, client: httpx.AsyncClient) -> list[str]:
    """List filenames in a repository's root directory."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    response = await client.get(url, headers=GITHUB_HEADERS, timeout=10.0)
    if response.status_code != 200:
        return []
    items = response.json()
    return [item["name"] for item in items if item.get("type") == "file"]


async def fetch_file_content(owner: str, repo: str, path: str, client: httpx.AsyncClient) -> str:
    """Fetch and decode a single file's text content from a repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = await client.get(url,headers=GITHUB_HEADERS , timeout=10.0)
    if response.status_code != 200:
        return ""
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""


async def fingerprint_repo(owner: str, repo: str) -> dict:
    """
    Check a single repository for concrete evidence of each technology
    in FINGERPRINT_RULES: presence of a marker file, and (where relevant)
    a matching keyword inside that file's content.

    Returns a dict of technology -> list of evidence strings found.
    An empty list means no evidence was found for that technology.
    """
    evidence: dict[str, list[str]] = {tech: [] for tech in FINGERPRINT_RULES}

    async with httpx.AsyncClient() as client:
        root_files = await fetch_repo_root_files(owner, repo, client)

        for tech, rule in FINGERPRINT_RULES.items():
            matching_files = [f for f in rule["files"] if f in root_files]
            if not matching_files:
                continue

            keywords = rule.get("keywords", [])
            if not keywords:
                # File presence alone is sufficient evidence (e.g. Dockerfile).
                evidence[tech].append(f"{matching_files[0]} present")
                continue

            for filename in matching_files:
                content = await fetch_file_content(owner, repo, filename, client)
                lower_content = content.lower()
                for keyword in keywords:
                    if keyword.lower() in lower_content:
                        evidence[tech].append(f"'{keyword}' found in {filename}")

    return evidence
# Configurable scoring weights (heuristic starting points, per Section 3.4
# of the proposal — not a claim of statistical optimality).
SCORE_WEIGHTS = {
    "fingerprint_match": 40,   # concrete file/keyword evidence found
    "language_match": 20,      # repo's GitHub-reported primary language matches
    "not_fork": 20,            # original work, not a forked repository
    "recent_activity": 20,     # repo updated within the last 12 months
}

STRONG_THRESHOLD = 70
GOOD_THRESHOLD = 40

INTERVIEW_QUESTION_TEMPLATES = {
    "Docker": "How did you use Docker to containerize this application?",
    "React": "Walk me through how you structured components in one of your React projects.",
    "FastAPI": "Can you describe an endpoint you built with FastAPI and why you chose it?",
    "Flask": "Can you walk through how you structured routes in a Flask project?",
    "Django": "What Django features (ORM, admin, etc.) did you rely on in your project?",
}


def default_interview_question(skill: str) -> str:
    return INTERVIEW_QUESTION_TEMPLATES.get(
        skill, f"Can you walk through a specific project where you used {skill}?"
    )


def is_recently_updated(updated_at: str, months: int = 12) -> bool:
    from datetime import datetime, timezone, timedelta
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    return updated >= cutoff


def score_skill(skill: str, repos: list[dict], fingerprints: dict[str, dict]) -> dict:
    """
    Computes an explainable 0-100 evidence score for a single claimed
    skill, by checking every repo for supporting signals and taking the
    strongest single repo's score (rather than summing across repos,
    which would unfairly reward having many mediocre repos).
    """
    best_score = 0
    best_reasons: list[str] = []

    for repo in repos:
        score = 0
        reasons = []

        detected = fingerprints.get(repo["name"], {}).get("detected_technologies", {})
        if skill in detected and detected[skill]:
            score += SCORE_WEIGHTS["fingerprint_match"]
            reasons.append(f"{repo['name']}: " + "; ".join(detected[skill]))

        if repo.get("language") and repo["language"].lower() == skill.lower():
            score += SCORE_WEIGHTS["language_match"]
            reasons.append(f"{repo['name']}: primary language matches ({repo['language']})")

        if not repo.get("is_fork"):
            score += SCORE_WEIGHTS["not_fork"]
            reasons.append(f"{repo['name']}: original repository, not a fork")

        if is_recently_updated(repo.get("updated_at", "")):
            score += SCORE_WEIGHTS["recent_activity"]
            reasons.append(f"{repo['name']}: updated within the last 12 months")

        if score > best_score:
            best_score = score
            best_reasons = reasons

    score = min(best_score, 100)

    if score >= STRONG_THRESHOLD:
        classification = "Strong Evidence"
    elif score >= GOOD_THRESHOLD:
        classification = "Good Evidence"
    else:
        classification = "Needs Verification"

    result = {
        "skill": skill,
        "score": score,
        "classification": classification,
        "reasons": best_reasons if best_reasons else ["No supporting evidence found in analyzed repositories"],
    }

    if classification == "Needs Verification":
        result["interview_question"] = default_interview_question(skill)

    return result

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
@app.get("/github/{username}/{repo}/fingerprint")
async def get_repo_fingerprint(username: str, repo: str):
    """
    Runs technology fingerprinting on a single repository: checks for
    marker files (Dockerfile, package.json, requirements.txt) and, where
    relevant, keyword matches inside them, per FINGERPRINT_RULES.
    """
    try:
        evidence = await fingerprint_repo(username, repo)
    except httpx.RequestError as exc:
        return {"status": "error", "error": f"Network error contacting GitHub: {exc}"}

    detected = {tech: items for tech, items in evidence.items() if items}
    return {
        "username": username,
        "repo": repo,
        "status": "ok",
        "detected_technologies": detected,
    }
from pydantic import BaseModel


class ScoreRequest(BaseModel):
    username: str
    skills: list[str]
    max_repos: int = 10


@app.post("/score")
async def score_candidate(request: ScoreRequest):
    """
    Computes an explainable evidence score for each claimed skill by
    fetching the candidate's repos, fingerprinting the most recently
    updated ones, then scoring each skill against that combined evidence.
    """
    try:
        repos = await fetch_github_repos(request.username)
    except httpx.HTTPStatusError as exc:
        return {"status": "error", "error": f"GitHub API error: {exc.response.status_code}"}
    except httpx.RequestError as exc:
        return {"status": "error", "error": f"Network error contacting GitHub: {exc}"}

    repos_to_check = repos[: request.max_repos]

    fingerprints = {}
    for repo in repos_to_check:
        raw_evidence = await fingerprint_repo(request.username, repo["name"])
        fingerprints[repo["name"]] = {
            "detected_technologies": {tech: items for tech, items in raw_evidence.items() if items}
        }

    scores = [score_skill(skill, repos_to_check, fingerprints) for skill in request.skills]

    return {
        "username": request.username,
        "status": "ok",
        "repos_analyzed": len(repos_to_check),
        "skill_scores": scores,
    }