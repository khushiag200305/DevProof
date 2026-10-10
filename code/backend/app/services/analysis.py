"""
GitHub evidence analysis for a stored candidate.

Ties together the GitHub client, fingerprinting and scoring services and
saves the result against the candidate, so the Candidate Detail page can
show each skill's score, its reasons and a suggested interview question
without re-running the analysis on every visit.

Each run replaces the candidate's previous results (repositories,
evidence, interview questions and per-skill scores), so re-analyzing
after a candidate pushes new work simply refreshes the report.
"""
import asyncio
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from .. import models
from .fingerprinting import fingerprint_repo
from .github_client import fetch_github_repos
from .scoring import score_skill

# Most recently updated repositories to fingerprint. Each one costs a few
# GitHub API calls, so this keeps an analysis well under the 60/hour
# unauthenticated limit (set GITHUB_TOKEN for 5000/hour).
MAX_REPOS = 10


class GitHubUnavailableError(RuntimeError):
    """Raised when GitHub can't be reached or refuses the request."""


def _parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _collect_evidence(username: str) -> tuple[list[dict], dict[str, dict]]:
    """Fetch the user's repos and fingerprint the most recent ones in parallel."""
    try:
        repos = await fetch_github_repos(username)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        hint = " (rate limit reached: set GITHUB_TOKEN in .env)" if code in (403, 429) else ""
        raise GitHubUnavailableError(f"GitHub API error {code}{hint}") from exc
    except httpx.RequestError as exc:
        raise GitHubUnavailableError(f"Could not reach GitHub: {exc}") from exc

    repos = repos[:MAX_REPOS]

    try:
        results = await asyncio.gather(
            *(fingerprint_repo(username, repo["name"]) for repo in repos)
        )
    except httpx.RequestError as exc:
        raise GitHubUnavailableError(f"Could not reach GitHub: {exc}") from exc

    fingerprints = {
        repo["name"]: {
            "detected_technologies": {tech: items for tech, items in raw.items() if items}
        }
        for repo, raw in zip(repos, results)
    }
    return repos, fingerprints


async def analyze_candidate(db: Session, candidate: models.Candidate) -> int:
    """
    Run the evidence engine for `candidate` and save the results.

    Returns the number of repositories analyzed. Raises ValueError if the
    candidate has no GitHub username, or GitHubUnavailableError if GitHub
    can't be queried. Nothing is changed in the database if either happens.
    """
    if not candidate.github_username:
        raise ValueError("This candidate has no GitHub username to analyze.")

    repos, fingerprints = await _collect_evidence(candidate.github_username)

    # Replace any previous analysis.
    db.query(models.Evidence).filter_by(candidate_id=candidate.candidate_id).delete()
    db.query(models.InterviewQuestion).filter_by(candidate_id=candidate.candidate_id).delete()
    db.query(models.Repository).filter_by(candidate_id=candidate.candidate_id).delete()

    repo_ids: dict[str, int] = {}
    for repo in repos:
        row = models.Repository(
            candidate_id=candidate.candidate_id,
            repo_name=repo["name"],
            repo_url=repo["url"],
            is_fork=bool(repo.get("is_fork")),
            last_updated=_parse_github_datetime(repo.get("updated_at")),
        )
        db.add(row)
        db.flush()  # assigns row.repo_id
        repo_ids[repo["name"]] = row.repo_id

    for candidate_skill in candidate.skills:
        result = score_skill(candidate_skill.skill.skill_name, repos, fingerprints)
        candidate_skill.score = result["score"]
        candidate_skill.status = result["classification"]

        for item in result["evidence"]:
            db.add(models.Evidence(
                candidate_id=candidate.candidate_id,
                skill_id=candidate_skill.skill_id,
                repo_id=repo_ids.get(item["repo"]),
                evidence_type=item["type"],
                description=f"{item['repo']}: {item['description']}",
                weight=item["weight"],
            ))

        if result.get("interview_question"):
            db.add(models.InterviewQuestion(
                candidate_id=candidate.candidate_id,
                skill_id=candidate_skill.skill_id,
                question=result["interview_question"],
            ))

    db.commit()
    db.refresh(candidate)
    return len(repos)
