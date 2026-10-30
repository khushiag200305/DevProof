"""Tests for the pure resume bullet generator in app/services/resume_bullets.py."""
from datetime import datetime, timezone

from app.services.resume_bullets import (
    MAX_BULLETS,
    bullet_report,
    humanize_repo_name,
    job_match,
    join_words,
    project_bullets,
)

SHOP_API = {
    "name": "shop-api",
    "url": "https://github.com/octocat/shop-api",
    "is_fork": False,
    "description": "REST API for an online shop.",
    "language": "Python",
    "technologies": ["Docker", "FastAPI", "PostgreSQL", "Python"],
    "commit_count": 38,
    "created_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    "pushed_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
    "has_tests": True,
    "has_ci": True,
    "has_compose": True,
    "stars": 0,
}

DASHBOARD = {
    "name": "sales_dashboard",
    "url": "https://github.com/octocat/sales_dashboard",
    "is_fork": False,
    "description": None,
    "language": "Jupyter Notebook",
    "technologies": ["Pandas", "Python"],
    "commit_count": 4,
}

SKILLS = [
    {"skill_name": "Python", "status": "Strong Evidence", "score": 100},
    {"skill_name": "Docker", "status": "Strong Evidence", "score": 80},
    {"skill_name": "React", "status": "Needs Verification", "score": 0},
]


def _texts(bullets):
    return [b["text"] for b in bullets]


def test_humanize_repo_name():
    assert humanize_repo_name("shop-api") == "Shop API"
    assert humanize_repo_name("sales_dashboard") == "Sales Dashboard"
    assert humanize_repo_name("DevProof") == "DevProof"
    assert humanize_repo_name("ml-crm-tool") == "ML CRM Tool"


def test_join_words():
    assert join_words([]) == ""
    assert join_words(["A"]) == "A"
    assert join_words(["A", "B"]) == "A and B"
    assert join_words(["A", "B", "C"]) == "A, B and C"


def test_full_project_gets_specific_evidence_based_lines():
    texts = _texts(project_bullets(SHOP_API, {"Python", "Docker"}))
    assert texts[0] == "Built Shop API, REST API for an online shop using Docker, Python, FastAPI and PostgreSQL."
    assert "Modelled and stored the application's data in PostgreSQL." in texts
    assert "Containerized the application with Docker and Docker Compose for a one-command local setup." in texts
    assert "Wrote automated tests and set up continuous integration to run them on every change." in texts
    assert len(texts) == MAX_BULLETS


def test_commit_line_includes_the_active_period():
    repo = dict(SHOP_API, technologies=[], has_tests=False, has_ci=False)
    texts = _texts(project_bullets(repo, set()))
    assert "Developed the project across 38 commits (Mar 2026 - Oct 2026)." in texts


def test_description_starting_with_an_article_or_verb():
    repo = dict(SHOP_API, description="A chat app for students", technologies=["React"])
    assert _texts(project_bullets(repo, set()))[0] == "Built a chat app for students using React."
    repo = dict(repo, description="Implemented a URL shortener")
    assert _texts(project_bullets(repo, set()))[0] == "Implemented a URL shortener using React."


def test_small_project_without_description():
    texts = _texts(project_bullets(DASHBOARD, {"Python"}))
    assert texts[0] == "Built Sales Dashboard using Python and Pandas."
    assert "Analysed and worked with data using Pandas." in texts
    assert not any("commits" in t for t in texts)  # under 10 commits: not worth a line


def test_job_description_skills_come_first():
    bullets = project_bullets(SHOP_API, {"Python"}, jd_skills={"PostgreSQL"})
    assert bullets[0]["skills"][0] == "PostgreSQL"
    assert bullets[1]["text"].startswith("Modelled and stored")


def test_job_match_splits_proven_claimed_and_missing():
    match = job_match("We use Python, React and Kubernetes; PostgreSQL is a plus.", SKILLS)
    assert set(match["skills"]) == {"PostgreSQL", "Python", "React"}  # Kubernetes isn't in the catalog
    assert match["proven"] == ["Python"]
    assert match["claimed_only"] == ["React"]
    assert match["missing"] == ["PostgreSQL"]
    assert match["readiness"] == 33
    assert any(t.startswith("React: on your resume") for t in match["tips"])
    assert any(t.startswith("PostgreSQL: the job asks") for t in match["tips"])


def test_job_match_with_no_known_skills():
    match = job_match("Great communication and teamwork.", SKILLS)
    assert match["skills"] == []
    assert match["readiness"] is None


def test_report_without_job_description():
    report = bullet_report([DASHBOARD, SHOP_API], SKILLS)
    assert report["job_match"] is None
    assert [p["name"] for p in report["projects"]] == ["shop-api", "sales_dashboard"]
    assert report["projects"][0]["title"] == "Shop API"


def test_report_puts_projects_matching_the_job_first():
    report = bullet_report([SHOP_API, DASHBOARD], SKILLS, "Data analyst skills: Pandas, Excel, SQL")
    assert report["projects"][0]["name"] == "sales_dashboard"
    assert report["projects"][0]["matched_skills"] == ["Pandas"]
    assert set(report["job_match"]["missing"]) == {"Pandas", "Excel", "SQL"}


def test_forks_are_left_out():
    fork = dict(SHOP_API, name="someone-elses-repo", is_fork=True)
    report = bullet_report([fork, DASHBOARD], SKILLS)
    assert [p["name"] for p in report["projects"]] == ["sales_dashboard"]
