"""Tests for linking resume projects to repositories (app/services/project_links.py)."""
from app.services.project_links import match_repo, match_score, name_words

REPOS = [
    {"name": "credit-card-fraud-detection", "url": "https://github.com/k/credit-card-fraud-detection"},
    {"name": "Smart-building-energy-analysis", "url": "https://github.com/k/Smart-building-energy-analysis"},
    {"name": "Emergency_request_project", "url": "https://github.com/k/Emergency_request_project"},
    {"name": "DevProof", "url": "https://github.com/k/DevProof"},
    {"name": "DSA-assignment", "url": "https://github.com/k/DSA-assignment"},
    {"name": "fraud-detection-tutorial", "url": "https://github.com/k/fraud-detection-tutorial", "is_fork": True},
]


def _match(name):
    repo = match_repo(name, REPOS)
    return repo["name"] if repo else None


def test_name_words_splits_and_folds_plurals():
    assert name_words("Smart-building-energy-analysis") == {"smart", "building", "energy", "analysis"}
    assert name_words("Energy Consumption Analysis in Smart Buildings") == {
        "energy", "consumption", "analysis", "smart", "building"
    }
    assert name_words("smartAttendanceApp") == {"smart", "attendance"}


def test_resume_projects_match_their_repositories():
    assert _match("Credit Card Fraud Detection & Transaction Analytics") == "credit-card-fraud-detection"
    assert _match("Energy Consumption Analysis in Smart Buildings") == "Smart-building-energy-analysis"
    assert _match("Emergency Management Database System") == "Emergency_request_project"
    assert _match("DevProof - Evidence-Based Skill Assessment") == "DevProof"


def test_unrelated_projects_do_not_match():
    assert _match("Portfolio Website") is None
    assert _match("Movie Recommendation Engine") is None


def test_forks_are_ignored():
    repos = [r for r in REPOS if r["name"] != "credit-card-fraud-detection"]
    assert match_repo("Fraud Detection Tutorial", repos) is None


def test_match_score():
    assert match_score("Credit Card Fraud Detection", "credit-card-fraud-detection") == 1.0
    assert match_score("Anything", "project") == 0.0
