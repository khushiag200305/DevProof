"""Tests for the pure project-signal rules in app/services/repo_profile.py."""
from app.services.repo_profile import commit_count_from_page, is_test_file, project_signals

FULL_STACK_REPO = [
    "README.md",
    ".github/workflows/ci.yml",
    "docker-compose.yml",
    "backend/app/main.py",
    "backend/app/models.py",
    "backend/tests/test_api.py",
    "frontend/src/App.tsx",
    "frontend/src/App.test.tsx",
    "frontend/node_modules/react/index.js",
    "docs/setup.md",
]


def test_full_stack_repo_signals():
    signals = project_signals(FULL_STACK_REPO)
    assert signals["has_tests"] is True
    assert signals["has_ci"] is True
    assert signals["has_readme"] is True
    assert signals["has_docs"] is True
    assert signals["has_frontend_and_backend"] is True
    assert signals["has_compose"] is True
    # node_modules is skipped; the 5 own .py/.tsx files count.
    assert signals["source_files"] == 5


def test_small_script_repo_has_no_signals():
    signals = project_signals(["main.py", "notes.txt"])
    assert signals == {
        "has_tests": False,
        "has_ci": False,
        "has_readme": False,
        "has_docs": False,
        "has_frontend_and_backend": False,
        "has_compose": False,
        "source_files": 1,
    }


def test_readme_only_counts_at_repo_root():
    assert project_signals(["lib/README.md"])["has_readme"] is False
    assert project_signals(["readme.rst"])["has_readme"] is True


def test_test_files_are_recognised_by_name_or_folder():
    assert is_test_file("test_scoring.py")
    assert is_test_file("src/scoring_test.go")
    assert is_test_file("src/Button.spec.tsx")
    assert is_test_file("src/main/java/ScoringTest.java")
    assert is_test_file("tests/helpers.py")
    assert not is_test_file("src/testimonials.py")
    assert not is_test_file("src/contest.py")


def test_tests_inside_node_modules_do_not_count():
    assert project_signals(["node_modules/lib/test/index.js"])["has_tests"] is False


def test_commit_count_from_link_header():
    link = (
        '<https://api.github.com/repositories/1/commits?author=octocat&per_page=1&page=2>; rel="next", '
        '<https://api.github.com/repositories/1/commits?author=octocat&per_page=1&page=38>; rel="last"'
    )
    assert commit_count_from_page(link, 1) == 38


def test_commit_count_without_link_header_is_the_items_returned():
    assert commit_count_from_page(None, 1) == 1
    assert commit_count_from_page(None, 0) == 0
