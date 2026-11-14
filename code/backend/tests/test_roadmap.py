"""Skill gap roadmap (pure logic)."""
from app.services.roadmap import PROJECT_IDEAS, PROOF_HINTS, ROLES, build_roadmap, how_to_prove
from app.skills_dictionary import SKILLS

REPOS = [
    {"name": "shop-api", "technologies": ["Python", "FastAPI"], "is_fork": False, "pushed_at": "2026-11-01T00:00:00Z"},
    {"name": "old-fork", "technologies": ["Python", "Flask"], "is_fork": True, "pushed_at": None},
    {"name": "notes-ui", "technologies": ["JavaScript", "React"], "is_fork": False, "pushed_at": None},
]


def test_every_skill_has_an_idea_and_every_checkable_skill_a_hint():
    assert set(PROJECT_IDEAS) == set(SKILLS)
    assert set(PROOF_HINTS) == {n for n, s in SKILLS.items() if s["check"] == "github"}
    for skills in ROLES.values():
        assert set(skills) <= set(SKILLS)
    assert how_to_prove("Excel") is None and "Dockerfile" in how_to_prove("Docker")


def test_roadmap_points_each_gap_at_a_fitting_original_repo():
    from datetime import datetime

    repos = [{**r, "pushed_at": datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) if r["pushed_at"] else None} for r in REPOS]
    fit = {"candidate_id": 3, "fit": 40, "proven": ["React"], "claimed_only": ["Docker", "Excel"], "missing": ["PostgreSQL", "Tableau"]}
    road = build_roadmap(fit, repos)

    assert road["proven"] == [{"skill": "React", "repo": "notes-ui"}]
    docker, excel = road["claimed"]
    assert docker["repo"] == "shop-api" and docker["checkable"]
    assert excel["repo"] is None and not excel["checkable"] and "interview" in excel["step"]
    postgres, tableau = road["missing"]
    assert postgres["repo"] == "shop-api" and postgres["proof"]
    assert tableau["repo"] is None and "Tableau" in tableau["idea"]
    assert road["practice"] == ["Docker", "Excel", "PostgreSQL", "Tableau"]
