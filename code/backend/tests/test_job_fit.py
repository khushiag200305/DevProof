"""Tests for "which resume fits this job best" (app/services/job_fit.py)."""
from datetime import datetime, timezone

from app.services.job_fit import fit_resumes, score_resume

STRONG, GOOD, NEEDS = "Strong Evidence", "Good Evidence", "Needs Verification"
JOB = "We need a backend intern with Python, PostgreSQL and Docker. React is a plus."


def _resume(cid, day, skills, analyzed=True, visible=False):
    return {
        "candidate_id": cid,
        "name": "Khushi Agarwal",
        "created_at": datetime(2026, 11, day, tzinfo=timezone.utc),
        "analyzed": analyzed,
        "visible_to_recruiters": visible,
        "skills": [{"skill_name": n, "status": s} for n, s in skills.items()],
    }


def test_job_skills_are_split_into_proven_claimed_and_missing():
    r = score_resume(["Docker", "Python", "React"], _resume(1, 1, {"Python": STRONG, "React": NEEDS}))
    assert (r["proven"], r["claimed_only"], r["missing"]) == (["Python"], ["React"], ["Docker"])
    assert r["fit"] == 47  # (100 + 40 + 0) / 3


def test_best_resume_is_the_one_proving_most_of_the_job():
    backend = _resume(1, 1, {"Python": STRONG, "PostgreSQL": GOOD, "Docker": NEEDS})
    frontend = _resume(2, 5, {"Python": GOOD, "React": STRONG}, visible=True)
    result = fit_resumes(JOB, [frontend, backend])

    assert result["skills"] == ["Docker", "PostgreSQL", "Python", "React"]
    assert [r["candidate_id"] for r in result["resumes"]] == [1, 2]
    assert result["best_candidate_id"] == 1
    assert result["resumes"][0]["best"] and not result["resumes"][1]["best"]
    assert result["resumes"][0]["fit"] == 60  # (100 + 100 + 40 + 0) / 4
    assert result["reason"].startswith("Proves 2 of the 4 skills this job asks for")
    assert "doesn't mention Docker, PostgreSQL" in result["reason"]
    assert any(t.startswith("Docker: on this resume but not proven") for t in result["tips"])
    assert any(t.startswith("React: the job asks for it") for t in result["tips"])


def test_ties_prefer_analyzed_then_newest():
    old = _resume(1, 1, {"Python": None}, analyzed=False)
    new = _resume(2, 9, {"Python": None}, analyzed=False)
    analyzed = _resume(3, 3, {"Python": NEEDS})
    result = fit_resumes("Python developer", [old, new, analyzed])
    assert [r["candidate_id"] for r in result["resumes"]] == [3, 2, 1]


def test_job_description_without_known_skills():
    result = fit_resumes("Friendly team player, good communication", [_resume(1, 1, {"Python": STRONG})])
    assert result == {"skills": [], "resumes": [], "best_candidate_id": None, "reason": None, "tips": []}


def test_no_resumes_yet():
    result = fit_resumes(JOB, [])
    assert result["skills"] and result["resumes"] == [] and result["best_candidate_id"] is None
