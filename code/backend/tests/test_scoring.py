"""
Unit tests for the rule-based evidence scoring in app/services/scoring.py.

Pure functions only: no database or GitHub calls, so repos and
fingerprints are plain dicts shaped like the ones the GitHub client and
fingerprinting service return.
"""
from datetime import datetime, timedelta, timezone

from app.services.scoring import GOOD_THRESHOLD, STRONG_THRESHOLD, score_skill

RECENT = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
OLD = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()


def _repo(name: str, language: str | None = None, is_fork: bool = False, updated_at: str = RECENT):
    return {"name": name, "language": language, "is_fork": is_fork, "updated_at": updated_at}


def _fingerprints(**detected_by_repo: dict[str, list[str]]) -> dict[str, dict]:
    return {repo: {"detected_technologies": detected} for repo, detected in detected_by_repo.items()}


def test_unrelated_active_repo_gives_no_evidence():
    # Regression test: an original, recently updated repo used to add 40
    # points to every claimed skill, even ones it had nothing to do with.
    repos = [_repo("todo-app", language="Python")]

    result = score_skill("Docker", repos, _fingerprints())

    assert result["score"] == 0
    assert result["classification"] == "Needs Verification"
    assert result["evidence"] == []
    assert "interview_question" in result


def test_fingerprint_on_original_recent_repo_is_strong():
    repos = [_repo("shop-api", language="Python")]
    fingerprints = _fingerprints(**{"shop-api": {"Docker": ["Dockerfile present"]}})

    result = score_skill("Docker", repos, fingerprints)

    assert result["score"] == 80
    assert result["score"] >= STRONG_THRESHOLD
    assert result["classification"] == "Strong Evidence"
    assert [item["type"] for item in result["evidence"]] == [
        "fingerprint_match",
        "not_fork",
        "recent_activity",
    ]
    assert "interview_question" not in result


def test_language_match_alone_is_good_evidence():
    repos = [_repo("algorithms", language="Python")]

    result = score_skill("Python", repos, _fingerprints())

    assert result["score"] == 60
    assert GOOD_THRESHOLD <= result["score"] < STRONG_THRESHOLD
    assert result["classification"] == "Good Evidence"
    assert result["reasons"][0] == "algorithms: primary language matches (Python)"


def test_language_match_is_case_insensitive():
    repos = [_repo("scripts", language="JavaScript")]

    result = score_skill("javascript", repos, _fingerprints())

    assert result["score"] == 60


def test_fork_and_old_repo_earn_no_bonus_points():
    repos = [_repo("forked-react-app", is_fork=True, updated_at=OLD)]
    fingerprints = _fingerprints(**{"forked-react-app": {"React": ["'\"react\"' found in package.json"]}})

    result = score_skill("React", repos, fingerprints)

    assert result["score"] == 40
    assert result["classification"] == "Good Evidence"
    assert [item["type"] for item in result["evidence"]] == ["fingerprint_match"]


def test_best_single_repo_wins_rather_than_a_sum():
    repos = [
        _repo("small-script", language="Python", is_fork=True, updated_at=OLD),
        _repo("main-project", language="Python"),
    ]
    fingerprints = _fingerprints(**{"main-project": {"Flask": ["'flask' found in requirements.txt"]}})

    python = score_skill("Python", repos, fingerprints)
    flask = score_skill("Flask", repos, fingerprints)

    assert python["score"] == 60
    assert all(item["repo"] == "main-project" for item in python["evidence"])
    assert flask["score"] == 80


def test_all_signals_cap_at_100():
    repos = [_repo("python-tool", language="Python")]
    fingerprints = _fingerprints(**{"python-tool": {"Python": ["setup.py present"]}})

    result = score_skill("Python", repos, fingerprints)

    assert result["score"] == 100


def test_no_repos_needs_verification_with_explanation():
    result = score_skill("Django", [], {})

    assert result["score"] == 0
    assert result["reasons"] == ["No supporting evidence found in analyzed repositories"]
    assert result["interview_question"].startswith("What Django features")


def test_missing_updated_at_does_not_crash():
    repos = [{"name": "legacy", "language": "Java", "is_fork": False, "updated_at": None}]

    result = score_skill("Java", repos, _fingerprints())

    assert result["score"] == 40


def test_other_repos_with_evidence_are_listed_as_supporting():
    repos = [
        _repo("old-scripts", language="Python", is_fork=True, updated_at=OLD),
        _repo("main-project", language="Python"),
        _repo("ml-notebooks", language="Python", updated_at=OLD),
        _repo("frontend", language="TypeScript"),
    ]
    fingerprints = _fingerprints(**{"main-project": {"Python": ["requirements.txt found at requirements.txt"]}})

    result = score_skill("Python", repos, fingerprints)

    # Score still comes from the single best repo...
    assert result["score"] == 100
    assert all(item["repo"] == "main-project" for item in result["evidence"])
    # ...and the others are listed, strongest first, without the best one
    # or repos with no evidence for the skill.
    assert result["supporting_repos"] == [
        {"repo": "ml-notebooks", "score": 40},
        {"repo": "old-scripts", "score": 20},
    ]


def test_no_supporting_repos_when_only_one_repo_has_evidence():
    repos = [_repo("only-one", language="Java"), _repo("unrelated", language="Go")]

    assert score_skill("Java", repos, _fingerprints())["supporting_repos"] == []
