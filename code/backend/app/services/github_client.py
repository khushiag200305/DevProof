"""
GitHub REST API client.

Iteration 1 note: this module (and fingerprinting.py / scoring.py) is
carried over largely unchanged from the pre-refactor prototype so the
existing repo-evidence and scoring behavior keeps working while the
project moves to a modular, DB-backed structure. Iteration 2 ("GitHub
Evidence") is where this gets a DB-backed caching layer (Repository
table) so re-opening a candidate doesn't re-hit the GitHub API, and
Iteration 3 formalizes the scoring rules against the Evidence table.
"""
import base64
import math
import os
import time
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from .repo_profile import commit_count_from_page

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


# --- Small in-memory cache -------------------------------------------------
# GitHub allows 60 requests an hour without a token (5,000 with one), and a
# single analysis can use 50+. The repo list is kept for a few minutes; a
# repo's inspection is kept until that repo is pushed to again.
REPO_LIST_TTL = int(os.getenv("GITHUB_REPO_LIST_CACHE_SECONDS", "600"))
INSPECTION_TTL = int(os.getenv("GITHUB_INSPECTION_CACHE_SECONDS", str(7 * 24 * 3600)))
MAX_CACHE_ENTRIES = 2000
_cache: dict[tuple, tuple[float, object]] = {}


def cache_get(key: tuple):
    hit = _cache.get(key)
    if hit is None:
        return None
    expires, value = hit
    if expires < time.monotonic():
        _cache.pop(key, None)
        return None
    return value


def cache_put(key: tuple, value, ttl: int) -> None:
    if len(_cache) >= MAX_CACHE_ENTRIES:
        # Drop the entries closest to expiring.
        for old in sorted(_cache, key=lambda k: _cache[k][0])[: MAX_CACHE_ENTRIES // 10]:
            _cache.pop(old, None)
    _cache[key] = (time.monotonic() + ttl, value)


def cache_clear() -> None:
    _cache.clear()


class GitHubRateLimitError(Exception):
    """GitHub refused the request because the hourly limit was used up."""

    def __init__(self, reset_at: float | None):
        self.reset_at = reset_at
        super().__init__("GitHub rate limit reached")

    @property
    def minutes_left(self) -> int | None:
        if not self.reset_at:
            return None
        return max(1, math.ceil((self.reset_at - time.time()) / 60))


def check_rate_limit(response: httpx.Response) -> None:
    """Raise GitHubRateLimitError for a rate-limited response (403 with 0 left, or 429)."""
    if response.status_code == 429 or (
        response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
    ):
        reset = response.headers.get("x-ratelimit-reset")
        raise GitHubRateLimitError(float(reset) if reset and reset.isdigit() else None)


async def fetch_github_repos(username: str) -> list[dict]:
    """
    Fetch a user's public repositories from the GitHub REST API.

    Returns a simplified list with just the fields DevProof's evidence
    engine needs: name, primary language, fork status, and last-updated
    date.
    """
    key = ("repos", username.lower())
    cached = cache_get(key)
    if cached is not None:
        return cached

    url = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": 100, "sort": "updated"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=GITHUB_HEADERS, timeout=10.0)

    check_rate_limit(response)
    if response.status_code == 404:
        return []
    response.raise_for_status()

    repos = response.json()
    result = [
        {
            "name": repo["name"],
            "language": repo["language"],
            "is_fork": repo["fork"],
            "stars": repo["stargazers_count"],
            "updated_at": repo["updated_at"],
            "url": repo["html_url"],
            # Shown on the portfolio page and used for resume lines.
            "description": repo.get("description"),
            "topics": repo.get("topics") or [],
            "homepage": repo.get("homepage") or None,
            "created_at": repo.get("created_at"),
            "pushed_at": repo.get("pushed_at"),
        }
        for repo in repos
    ]
    cache_put(key, result, REPO_LIST_TTL)
    return result


async def fetch_commit_count(owner: str, repo: str, client: httpx.AsyncClient) -> int:
    """
    How many commits on the default branch were authored by `owner`, from
    a single `per_page=1` request (the Link header's last page is the
    total). Returns 0 for an empty or unreadable repository.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    response = await client.get(
        url, params={"author": owner, "per_page": 1}, headers=GITHUB_HEADERS, timeout=10.0
    )
    check_rate_limit(response)
    if response.status_code != 200:
        return 0
    return commit_count_from_page(response.headers.get("link"), len(response.json()))


async def fetch_repo_tree(owner: str, repo: str, client: httpx.AsyncClient) -> list[str]:
    """
    Every file path in a repository's default branch, from one recursive
    git tree request (so files inside subfolders such as backend/ or
    frontend/ are found too). Returns [] for an empty or unreadable repo.

    GitHub cuts very large trees short ("truncated"); the paths it did
    return are still used.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
    response = await client.get(
        url, params={"recursive": "1"}, headers=GITHUB_HEADERS, timeout=15.0
    )
    check_rate_limit(response)
    if response.status_code != 200:
        return []
    return [
        item["path"]
        for item in response.json().get("tree", [])
        if item.get("type") == "blob"
    ]


async def fetch_file_content(owner: str, repo: str, path: str, client: httpx.AsyncClient) -> str:
    """Fetch and decode a single file's text content from a repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quote(path)}"
    response = await client.get(url, headers=GITHUB_HEADERS, timeout=10.0)
    check_rate_limit(response)
    if response.status_code != 200:
        return ""
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""
