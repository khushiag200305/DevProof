"""Tests for the pure portfolio builder in app/services/portfolio.py."""
from datetime import datetime, timezone

from app.services.portfolio import (
    MAX_PROJECTS,
    active_period,
    build_portfolio,
    make_slug,
    rank_projects,
)


def _dt(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=timezone.utc)


SKILLS = [
    {"skill_name": "Python", "status": "Strong Evidence", "score": 100},
    {"skill_name": "Docker", "status": "Good Evidence", "score": 60},
    {"skill_name": "React", "status": "Needs Verification", "score": 0},
    {"skill_name": "Object-Oriented Programming", "status": "Not checkable on GitHub", "score": None},
]

SHOP_API = {
    "name": "shop-api",
    "url": "https://github.com/octocat/shop-api",
    "is_fork": False,
    "description": "REST API for an online shop",
    "language": "Python",
    "topics": ["fastapi"],
    "stars": 4,
    "technologies": ["Docker", "Python"],
    "commit_count": 38,
    "created_at": _dt(2026, 3),
    "pushed_at": _dt(2026, 10),
    "has_tests": True,
    "has_ci": True,
    "has_frontend_and_backend": False,
}

NOTES = {
    "name": "notes",
    "url": "https://github.com/octocat/notes",
    "is_fork": False,
    "language": "Python",
    "technologies": ["Python"],
    "commit_count": 5,
    "pushed_at": _dt(2026, 9),
}

FORKED = {
    "name": "react",
    "url": "https://github.com/octocat/react",
    "is_fork": True,
    "language": "JavaScript",
    "technologies": ["React"],
    "commit_count": 0,
    "pushed_at": _dt(2026, 10),
}


def _build(repos=None, headline=None):
    return build_portfolio(
        {"name": "Aditi Sharma", "github_username": "octocat"},
        SKILLS,
        [SHOP_API, NOTES, FORKED] if repos is None else repos,
        headline,
    )


def test_only_verified_skills_are_shown_grouped_by_category():
    page = _build()
    shown = [s["name"] for g in page["skill_groups"] for s in g["skills"]]
    assert shown == ["Python", "Docker"]
    assert [g["category"] for g in page["skill_groups"]] == ["Programming Languages", "Cloud & DevOps"]
    assert page["stats"]["verified_skills"] == 2


def test_concept_skills_are_listed_separately_and_unbacked_ones_are_hidden():
    page = _build()
    assert page["also_listed"] == ["Object-Oriented Programming"]
    assert "React" not in page["also_listed"]


def test_projects_skip_forks_and_put_the_strongest_first():
    page = _build()
    assert [p["name"] for p in page["projects"]] == ["shop-api", "notes"]
    card = page["projects"][0]
    assert card["highlights"] == ["Automated tests", "Continuous integration"]
    assert card["active"] == "Mar 2026 - Oct 2026"
    assert card["commit_count"] == 38


def test_stats_and_links():
    page = _build(headline="Backend developer")
    assert page["headline"] == "Backend developer"
    assert page["github_url"] == "https://github.com/octocat"
    assert page["stats"]["original_repos"] == 2
    assert page["stats"]["commits"] == 43
    assert page["stats"]["top_languages"] == ["Python"]
    assert page["analyzed"] is True


def test_page_before_analysis_has_no_projects():
    page = _build(repos=[])
    assert page["analyzed"] is False
    assert page["projects"] == []


def test_at_most_max_projects_are_shown():
    repos = [dict(NOTES, name=f"repo-{i}") for i in range(MAX_PROJECTS + 3)]
    assert len(_build(repos=repos)["projects"]) == MAX_PROJECTS


def test_rank_prefers_repos_showing_more_claimed_skills():
    ranked = rank_projects([NOTES, SHOP_API], {"Python", "Docker"})
    assert ranked[0]["name"] == "shop-api"


def test_active_period_single_month():
    assert active_period(_dt(2026, 5), _dt(2026, 5)) == "May 2026"
    assert active_period(None, _dt(2026, 5)) == "May 2026"
    assert active_period(None, None) is None


def test_slug_is_readable_and_unguessable():
    slug = make_slug("Khushi Agarwal", 7)
    assert slug.startswith("khushi-agarwal-")
    assert len(slug.rsplit("-", 1)[1]) == 6
    assert make_slug("Khushi Agarwal", 7) != slug
    assert make_slug(None, 7).startswith("candidate-7-")
