"""
GitHub evidence endpoints (Iteration 1 carries these over as-is from the
prototype; Iteration 2 formalizes them under /api/candidates and adds
DB-backed caching so re-opening a candidate doesn't re-hit the GitHub
API - see services/github_client.py's module docstring).
"""
import httpx
from fastapi import APIRouter

from ..services.fingerprinting import fingerprint_repo
from ..services.github_client import fetch_github_repos

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/{username}/repos")
async def get_github_repos(username: str):
    """
    Returns simplified public repository evidence for a GitHub username.
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


@router.get("/{username}/{repo}/fingerprint")
async def get_repo_fingerprint(username: str, repo: str):
    """
    Runs technology fingerprinting on a single repository: checks for
    marker files (Dockerfile, package.json, requirements.txt) and, where
    relevant, keyword matches inside them.
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
