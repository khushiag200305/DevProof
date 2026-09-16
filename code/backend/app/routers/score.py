"""
Evidence scoring endpoint (carried over as-is from the prototype;
Iteration 3 persists this against the Evidence table instead of
recomputing on every request - see services/scoring.py's module
docstring).
"""
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.fingerprinting import fingerprint_repo
from ..services.github_client import fetch_github_repos
from ..services.scoring import score_skill

router = APIRouter(tags=["score"])


class ScoreRequest(BaseModel):
    username: str
    skills: list[str]
    max_repos: int = 10


@router.post("/score")
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
