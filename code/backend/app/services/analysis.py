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
import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from .fingerprinting import inspect_repo
from .github_client import fetch_github_repos
from .scoring import score_skill

# Most recently updated repositories to fingerprint. Each one costs a few
# GitHub API calls, so this keeps an analysis well under the 60/hour
# unauthenticated limit (set GITHUB_TOKEN for 5000/hour).
MAX_REPOS = 10


# Evidence rows of this type record another repository that also supports
# a skill (description = repo name, weight = that repo's score), as
# opposed to the itemised evidence from the best repository.
SUPPORTING_REPO = "supporting_repo"


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
    """
    Fetch the user's repos and inspect the most recent ones in parallel.

    Returns the repos and, per repo name, its detected technologies (as
    scoring expects under "detected_technologies") plus its project
    signals and the candidate's commit count.
    """
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
            *(inspect_repo(username, repo["name"]) for repo in repos)
        )
    except httpx.RequestError as exc:
        raise GitHubUnavailableError(f"Could not reach GitHub: {exc}") from exc

    fingerprints = {
        repo["name"]: {
            "detected_technologies": {
                tech: items for tech, items in result["technologies"].items() if items
            },
            "signals": result.get("signals", {}),
            "commit_count": result.get("commit_count", 0),
        }
        for repo, result in zip(repos, results)
    }
    return repos, fingerprints


def _repo_detail(repo_id: int, repo: dict, fingerprint: dict) -> models.RepositoryDetail:
    signals = fingerprint.get("signals", {})
    return models.RepositoryDetail(
        repo_id=repo_id,
        description=repo.get("description"),
        language=repo.get("language"),
        topics=",".join(repo.get("topics") or []),
        homepage=repo.get("homepage"),
        stars=repo.get("stars") or 0,
        created_at=_parse_github_datetime(repo.get("created_at")),
        pushed_at=_parse_github_datetime(repo.get("pushed_at")),
        technologies=json.dumps(sorted(fingerprint.get("detected_technologies", {}))),
        has_tests=bool(signals.get("has_tests")),
        has_ci=bool(signals.get("has_ci")),
        has_readme=bool(signals.get("has_readme")),
        has_docs=bool(signals.get("has_docs")),
        has_frontend_and_backend=bool(signals.get("has_frontend_and_backend")),
        has_compose=bool(signals.get("has_compose")),
        source_files=int(signals.get("source_files") or 0),
    )


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
    old_repo_ids = select(models.Repository.repo_id).where(
        models.Repository.candidate_id == candidate.candidate_id
    )
    db.query(models.RepositoryDetail).filter(
        models.RepositoryDetail.repo_id.in_(old_repo_ids)
    ).delete(synchronize_session=False)
    db.query(models.Repository).filter_by(candidate_id=candidate.candidate_id).delete()

    repo_ids: dict[str, int] = {}
    for repo in repos:
        row = models.Repository(
            candidate_id=candidate.candidate_id,
            repo_name=repo["name"],
            repo_url=repo["url"],
            is_fork=bool(repo.get("is_fork")),
            commit_count=fingerprints.get(repo["name"], {}).get("commit_count", 0),
            last_updated=_parse_github_datetime(repo.get("updated_at")),
        )
        db.add(row)
        db.flush()  # assigns row.repo_id
        repo_ids[repo["name"]] = row.repo_id
        db.add(_repo_detail(row.repo_id, repo, fingerprints.get(repo["name"], {})))

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

        for supporting in result["supporting_repos"]:
            db.add(models.Evidence(
                candidate_id=candidate.candidate_id,
                skill_id=candidate_skill.skill_id,
                repo_id=repo_ids.get(supporting["repo"]),
                evidence_type=SUPPORTING_REPO,
                description=supporting["repo"],
                weight=supporting["score"],
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
