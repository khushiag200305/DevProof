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
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from .repo_profile import commit_count_from_page

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    GITHUB_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


async def fetch_github_repos(username: str) -> list[dict]:
    """
    Fetch a user's public repositories from the GitHub REST API.

    Returns a simplified list with just the fields DevProof's evidence
    engine needs: name, primary language, fork status, and last-updated
    date.
    """
    url = f"https://api.github.com/users/{username}/repos"
    params = {"per_page": 100, "sort": "updated"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=GITHUB_HEADERS, timeout=10.0)

    if response.status_code == 404:
        return []
    response.raise_for_status()

    repos = response.json()
    return [
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
    if response.status_code != 200:
        return ""
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""
