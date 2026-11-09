"""Tests for the pure talent search logic in app/services/talent_search.py."""
from datetime import datetime, timedelta, timezone

from app.services.talent_search import (
    compare,
    latest_per_student,
    mark_new,
    match_profile,
    normalize_query,
    search,
)

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _profile(cid, name, skills, repos=None, github="gh", user_id=None, created=None):
    return {
        "candidate_id": cid,
        "user_id": user_id,
        "name": name,
        "email": f"{name.split()[0].lower()}@thapar.edu",
        "github_username": github,
        "created_at": created or NOW - timedelta(days=cid),
        "skills": {
            s: {"status": status, "score": score, "category": "x"} for s, (status, score) in skills.items()
        },
        "repos": repos if repos is not None else [{"name": "r", "is_fork": False, "pushed_at": NOW - timedelta(days=10)}],
    }


STRONG, GOOD, NEEDS = "Strong Evidence", "Good Evidence", "Needs Verification"

ADITI = _profile(1, "Aditi Sharma", {"Python": (STRONG, 100), "React": (GOOD, 60), "Docker": (NEEDS, 0)})
ROHIT = _profile(2, "Rohit Singhal", {"Python": (GOOD, 70), "React": (STRONG, 92)})
ARJUN = _profile(3, "Arjun Mehta", {"Python": (NEEDS, 0), "Java": (STRONG, 95)})
NEW = _profile(4, "Sneha Kapoor", {"Python": (None, None)})  # uploaded, not analyzed yet


def test_defaults_and_cleanup():
    q = normalize_query({"skills": [" Python ", "python", "", "React"], "min_level": "nonsense"})
    assert q["skills"] == ["Python", "React"]
    assert q["min_level"] == "good" and q["match"] == "all"
    assert q["has_github"] is False and q["min_repos"] == 0 and q["active_months"] is None


def test_all_skills_at_good_level_ranks_stronger_evidence_first():
    results = search([ARJUN, ROHIT, ADITI, NEW], {"skills": ["Python", "React"]}, NOW)
    assert [r["name"] for r in results] == ["Rohit Singhal", "Aditi Sharma"]
    assert results[0]["match_score"] == 81  # (70 + 92) / 2
    assert results[1]["matched"][0] == {"skill": "Python", "status": STRONG, "score": 100}


def test_strong_level_excludes_good_evidence():
    results = search([ADITI, ROHIT], {"skills": ["Python"], "min_level": "strong"}, NOW)
    assert [r["name"] for r in results] == ["Aditi Sharma"]


def test_claimed_level_includes_unproven_and_unanalyzed_skills():
    results = search([ADITI, ARJUN, NEW], {"skills": ["Python"], "min_level": "claimed"}, NOW)
    assert {r["name"] for r in results} == {"Aditi Sharma", "Arjun Mehta", "Sneha Kapoor"}


def test_any_mode_lists_what_is_missing():
    results = search([ADITI, ARJUN], {"skills": ["Java", "React"], "match": "any"}, NOW)
    assert [r["name"] for r in results] == ["Arjun Mehta", "Aditi Sharma"]
    assert results[0]["missing"] == ["React"]
    assert results[0]["match_score"] == 48  # 95 / 2, rounded


def test_skill_names_match_case_insensitively():
    assert match_profile(ADITI, normalize_query({"skills": ["python"]}), NOW)["matched"][0]["skill"] == "Python"


def test_filters_github_repos_activity_and_text():
    no_github = _profile(5, "Kabir Sethi", {"Python": (STRONG, 90)}, github=None, repos=[])
    stale = _profile(
        6, "Priya Nair", {"Python": (STRONG, 90)},
        repos=[{"name": "old", "is_fork": False, "pushed_at": NOW - timedelta(days=400)},
               {"name": "fork", "is_fork": True, "pushed_at": NOW}],
    )
    everyone = [ADITI, no_github, stale]
    q = {"skills": ["Python"]}
    assert len(search(everyone, q, NOW)) == 3
    assert {r["name"] for r in search(everyone, {**q, "has_github": True}, NOW)} == {"Aditi Sharma", "Priya Nair"}
    assert [r["name"] for r in search(everyone, {**q, "active_months": 6}, NOW)] == ["Aditi Sharma"]
    assert {r["name"] for r in search(everyone, {**q, "min_repos": 1}, NOW)} == {"Aditi Sharma", "Priya Nair"}
    assert [r["name"] for r in search(everyone, {**q, "text": "PRIYA"}, NOW)] == ["Priya Nair"]


def test_empty_skill_list_returns_everyone_passing_filters():
    results = search([ADITI, ROHIT], {}, NOW)
    assert len(results) == 2 and all(r["match_score"] == 0 for r in results)


def test_only_latest_upload_per_student_is_searched():
    old = _profile(10, "Khushi Agarwal", {"Python": (GOOD, 60)}, user_id=7, created=NOW - timedelta(days=30))
    latest = _profile(11, "Khushi Agarwal", {"Python": (STRONG, 100)}, user_id=7, created=NOW - timedelta(days=1))
    loose = _profile(12, "No Account", {"Python": (STRONG, 80)})
    kept = latest_per_student([old, latest, loose])
    assert sorted(p["candidate_id"] for p in kept) == [11, 12]


def test_new_matches_since_last_run_are_flagged():
    results = search([ADITI, ROHIT], {"skills": ["Python"]}, NOW)
    flagged = {r["name"]: r["is_new"] for r in mark_new(results, NOW - timedelta(days=1, hours=12))}
    assert flagged == {"Aditi Sharma": True, "Rohit Singhal": False}
    assert not any(r["is_new"] for r in mark_new(results, None))


def test_compare_puts_shared_backed_skills_first():
    view = compare([ADITI, ROHIT])
    assert [c["name"] for c in view["candidates"]] == ["Aditi Sharma", "Rohit Singhal"]
    assert [r["skill"] for r in view["rows"]] == ["Python", "React", "Docker"]
    docker = view["rows"][2]
    assert docker["cells"] == [{"status": NEEDS, "score": 0}, None]
    assert view["candidates"][0]["backed_skills"] == 2
