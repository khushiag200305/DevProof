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

import httpx
from dotenv import load_dotenv

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
        }
        for repo in repos
    ]


async def fetch_repo_root_files(owner: str, repo: str, client: httpx.AsyncClient) -> list[str]:
    """List filenames in a repository's root directory."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    response = await client.get(url, headers=GITHUB_HEADERS, timeout=10.0)
    if response.status_code != 200:
        return []
    items = response.json()
    return [item["name"] for item in items if item.get("type") == "file"]


async def fetch_file_content(owner: str, repo: str, path: str, client: httpx.AsyncClient) -> str:
    """Fetch and decode a single file's text content from a repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    response = await client.get(url, headers=GITHUB_HEADERS, timeout=10.0)
    if response.status_code != 200:
        return ""
    data = response.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""
