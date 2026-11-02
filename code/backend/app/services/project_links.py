"""
Links each project on the resume to the GitHub repository it most likely
is, by comparing the words in the project's name with the words in the
repository's name:

    "Credit Card Fraud Detection & Transaction Analytics"  -> credit-card-fraud-detection
    "Energy Consumption Analysis in Smart Buildings"      -> Smart-building-energy-analysis

A repository matches when at least half of its meaningful words appear
in the project name (plurals folded, generic words like "project" or
"app" ignored). Pure logic, no network calls.
"""
import re

# Words too generic to identify a project on their own.
GENERIC_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "using", "via", "by",
    "my", "project", "projects", "app", "application", "system", "website", "web", "site", "tool",
    "platform", "simple", "basic", "demo", "test", "final", "mini", "main", "repo", "code", "new",
}

MIN_SHARE = 0.5


def _stem(word: str) -> str:
    """Fold simple plurals so 'buildings' matches 'building'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "is", "us", "os")):
        return word[:-1]
    return word


def name_words(name: str) -> set[str]:
    """Meaningful lower-case words in a project or repository name ('smartBuilding' -> smart, building)."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    words = re.findall(r"[a-z0-9]+", spaced.lower())
    return {_stem(w) for w in words if w not in GENERIC_WORDS and len(w) > 1}


def match_score(project_name: str, repo_name: str) -> float:
    """Share of the repository's words that appear in the project name (0-1)."""
    repo = name_words(repo_name)
    if not repo:
        return 0.0
    return len(repo & name_words(project_name)) / len(repo)


def match_repo(project_name: str, repos: list[dict]) -> dict | None:
    """
    The repository (from `repos`, each with "name" and "url") that best
    matches a resume project, or None. Forks are ignored. Ties go to the
    repository sharing more words with the project.
    """
    project = name_words(project_name)
    best, best_key = None, (0.0, 0)
    for repo in repos:
        if repo.get("is_fork"):
            continue
        words = name_words(repo["name"])
        if not words:
            continue
        shared = len(words & project)
        score = shared / len(words)
        if shared and score >= MIN_SHARE and (score, shared) > best_key:
            best, best_key = repo, (score, shared)
    return best
