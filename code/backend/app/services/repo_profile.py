"""
Project signals for a repository: facts about how a project is built that
are worth showing on a portfolio or turning into resume lines - does it
have tests, continuous integration, a README, a separate frontend and
backend? - plus helpers for the candidate's own commit count.

Pure logic, like tech_rules.py: it works on the file paths that
fingerprinting already fetched with one recursive tree request, so it
costs no extra GitHub API calls.
"""
import posixpath
import re

from .tech_rules import is_ignored

# Extensions counted as "source files" for the project-size signal.
SOURCE_EXTENSIONS = {
    ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".c", ".h",
    ".cpp", ".cc", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
    ".dart", ".sql", ".r", ".scala", ".vue", ".svelte", ".html", ".css", ".scss",
}

FRONTEND_DIRS = {"frontend", "client", "web", "ui", "webapp"}
BACKEND_DIRS = {"backend", "server", "api", "service"}
DOCS_DIRS = {"docs", "doc", "documentation"}

_TEST_FILE = re.compile(
    r"(^test_.+\.py$)|(.+_test\.(py|go)$)|(.+\.(test|spec)\.(js|jsx|ts|tsx)$)|(.+Tests?\.(java|kt|cs)$)"
)
_TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs"}


def _parts(path: str) -> list[str]:
    return path.lower().split("/")


def is_test_file(path: str) -> bool:
    """A test file by name (test_x.py, x.test.ts, FooTest.java) or folder (tests/)."""
    name = posixpath.basename(path)
    if _TEST_FILE.match(name):
        return True
    return any(part in _TEST_DIRS for part in _parts(path)[:-1])


def project_signals(paths: list[str]) -> dict:
    """
    Facts about a repository from its file paths. Files inside ignored
    folders (node_modules, venv, dist, ...) are skipped, so copied
    libraries never count as the candidate's own work.
    """
    own = [p for p in paths if not is_ignored(p)]
    lowered = [p.lower() for p in own]
    top_dirs = {p.split("/")[0] for p in lowered if "/" in p}

    return {
        "has_tests": any(is_test_file(p) for p in own),
        "has_ci": any(
            p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))
            for p in lowered
        ) or ".gitlab-ci.yml" in lowered or ".travis.yml" in lowered,
        "has_readme": any(posixpath.basename(p).startswith("readme") for p in lowered if "/" not in p),
        "has_docs": bool(top_dirs & DOCS_DIRS),
        "has_frontend_and_backend": bool(top_dirs & FRONTEND_DIRS) and bool(top_dirs & BACKEND_DIRS),
        "has_compose": any(
            posixpath.basename(p) in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
            for p in lowered
        ),
        "source_files": sum(
            1 for p in lowered if posixpath.splitext(p)[1] in SOURCE_EXTENSIONS
        ),
    }


_LAST_PAGE = re.compile(r'[?&]page=(\d+)[^>]*>;\s*rel="last"')


def commit_count_from_page(link_header: str | None, items_on_page: int) -> int:
    """
    Number of commits from a `per_page=1` commits request: GitHub's Link
    header names the last page, which equals the total count. With no
    Link header there is only one page, so the count is what came back.
    """
    if link_header:
        match = _LAST_PAGE.search(link_header)
        if match:
            return int(match.group(1))
    return items_on_page
