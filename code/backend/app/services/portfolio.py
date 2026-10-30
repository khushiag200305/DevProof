"""
Student portfolio page: turns a candidate's analyzed resume + GitHub data
into a shareable page of verified skills and their best projects.

build_portfolio() is pure (plain dicts in, a dict out) so it is tested
without a database; portfolio_from_candidate() only converts the ORM rows
into those dicts.
"""
import json
import re
import secrets
from collections import Counter
from datetime import datetime

from .. import models
from ..skills_dictionary import NOT_CHECKABLE, category_of, category_rank, is_checkable

# Projects shown on the page, best first.
MAX_PROJECTS = 6

VERIFIED_STATUSES = ("Strong Evidence", "Good Evidence")

# Project signal -> label shown as a highlight chip on a project card.
HIGHLIGHTS = [
    ("has_frontend_and_backend", "Frontend + backend"),
    ("has_tests", "Automated tests"),
    ("has_ci", "Continuous integration"),
    ("has_compose", "Docker Compose setup"),
    ("has_docs", "Documentation"),
]


def make_slug(name: str | None, candidate_id: int) -> str:
    """
    The public link's path segment: a readable part from the name plus a
    random part, so links can't be guessed by counting ids
    ("khushi-agarwal-7f3k2q").
    """
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40] or f"candidate-{candidate_id}"
    return f"{base}-{secrets.token_hex(3)}"


def _month(value: datetime | None) -> str | None:
    return value.strftime("%b %Y") if value else None


def active_period(created: datetime | None, pushed: datetime | None) -> str | None:
    """'Mar 2026 - Oct 2026', or a single month when both fall in the same one."""
    start, end = _month(created), _month(pushed)
    if start and end and start != end:
        return f"{start} - {end}"
    return end or start


def project_card(repo: dict) -> dict:
    """One project card from a repository dict (see portfolio_from_candidate)."""
    return {
        "name": repo["name"],
        "url": repo["url"],
        "description": repo.get("description"),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "homepage": repo.get("homepage"),
        "stars": repo.get("stars", 0),
        "technologies": repo.get("technologies", []),
        "highlights": [label for key, label in HIGHLIGHTS if repo.get(key)],
        "commit_count": repo.get("commit_count", 0),
        "active": active_period(repo.get("created_at"), repo.get("pushed_at")),
    }


def rank_projects(repos: list[dict], claimed: set[str]) -> list[dict]:
    """
    Original (non-fork) repositories, best first: most claimed skills shown
    in the repo, then most commits by the candidate, then most recent push.
    """
    own = [r for r in repos if not r.get("is_fork")]

    def key(repo: dict):
        shows = len(set(repo.get("technologies", [])) & claimed)
        pushed = repo.get("pushed_at")
        return (-shows, -repo.get("commit_count", 0), -(pushed.timestamp() if pushed else 0))

    return sorted(own, key=key)


def build_portfolio(candidate: dict, skills: list[dict], repos: list[dict], headline: str | None) -> dict:
    """
    The portfolio page's content.

    candidate: name, github_username
    skills:    skill_name, status, score  (one per claimed skill)
    repos:     analyzed repositories with their details (may be empty)
    """
    claimed = {s["skill_name"] for s in skills}

    verified = sorted(
        (s for s in skills if s.get("status") in VERIFIED_STATUSES),
        key=lambda s: (category_rank(s["skill_name"]), -(s.get("score") or 0), s["skill_name"].lower()),
    )
    groups: list[dict] = []
    for s in verified:
        category = category_of(s["skill_name"])
        if not groups or groups[-1]["category"] != category:
            groups.append({"category": category, "skills": []})
        groups[-1]["skills"].append(
            {"name": s["skill_name"], "score": s.get("score"), "status": s["status"]}
        )

    verified_names = {s["skill_name"] for s in verified}
    also_listed = sorted(
        (s["skill_name"] for s in skills
         if s["skill_name"] not in verified_names
         and (not is_checkable(s["skill_name"]) or s.get("status") == NOT_CHECKABLE)),
        key=lambda n: (category_rank(n), n.lower()),
    )

    ranked = rank_projects(repos, claimed)
    own = [r for r in repos if not r.get("is_fork")]
    languages = Counter(r["language"] for r in own if r.get("language"))

    username = candidate.get("github_username")
    return {
        "name": candidate.get("name") or username or "DevProof candidate",
        "headline": headline,
        "github_username": username,
        "github_url": f"https://github.com/{username}" if username else None,
        "analyzed": bool(repos),
        "skill_groups": groups,
        "also_listed": also_listed,
        "projects": [project_card(r) for r in ranked[:MAX_PROJECTS]],
        "stats": {
            "verified_skills": len(verified),
            "original_repos": len(own),
            "commits": sum(r.get("commit_count", 0) for r in own),
            "top_languages": [lang for lang, _ in languages.most_common(3)],
        },
    }


def _repo_dict(repo: models.Repository) -> dict:
    detail = repo.detail
    data = {
        "name": repo.repo_name,
        "url": repo.repo_url,
        "is_fork": repo.is_fork,
        "commit_count": repo.commit_count or 0,
        "pushed_at": repo.last_updated,
    }
    if detail is not None:
        data.update(
            description=detail.description,
            language=detail.language,
            topics=[t for t in (detail.topics or "").split(",") if t],
            homepage=detail.homepage,
            stars=detail.stars or 0,
            created_at=detail.created_at,
            pushed_at=detail.pushed_at or repo.last_updated,
            technologies=json.loads(detail.technologies or "[]"),
            has_tests=detail.has_tests,
            has_ci=detail.has_ci,
            has_readme=detail.has_readme,
            has_docs=detail.has_docs,
            has_frontend_and_backend=detail.has_frontend_and_backend,
            has_compose=detail.has_compose,
            source_files=detail.source_files,
        )
    return data


def repo_dicts(candidate: models.Candidate) -> list[dict]:
    """The candidate's analyzed repositories as plain dicts (details included)."""
    return [_repo_dict(r) for r in candidate.repositories]


def skill_dicts(candidate: models.Candidate) -> list[dict]:
    """The candidate's claimed skills with their status and score."""
    return [
        {
            "skill_name": cs.skill.skill_name,
            "status": cs.status if is_checkable(cs.skill.skill_name) else NOT_CHECKABLE,
            "score": cs.score,
        }
        for cs in candidate.skills
    ]


def portfolio_from_candidate(candidate: models.Candidate) -> dict:
    skills = skill_dicts(candidate)
    headline = candidate.portfolio.headline if candidate.portfolio else None
    return build_portfolio(
        {"name": candidate.name, "github_username": candidate.github_username},
        skills,
        repo_dicts(candidate),
        headline,
    )
