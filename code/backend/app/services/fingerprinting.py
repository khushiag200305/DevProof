"""
Technology fingerprinting: checks a repository for concrete evidence of
each technology rather than trusting GitHub's reported language alone.
See Section 3.3 / Section 6 of the proposal.

This module does the GitHub fetching; the rules themselves (marker files,
source-file counts, dependency names) live in services/tech_rules.py so
they can be tested without network access.

Cost per repository: one recursive tree request plus at most
MAX_MANIFESTS_PER_REPO file reads (inspect_repo adds one commit-count
request).
"""
import asyncio

import httpx

from .github_client import fetch_commit_count, fetch_file_content, fetch_repo_tree
from .repo_profile import project_signals
from .tech_rules import TECH_RULES, detect_technologies, manifest_paths

# Dependency/config files read per repository (shallowest first). Keeps a
# 10-repo analysis around 50 GitHub API calls.
MAX_MANIFESTS_PER_REPO = 4

# Kept for anything that lists the supported technologies.
FINGERPRINT_RULES = TECH_RULES


async def fingerprint_repo(owner: str, repo: str) -> dict[str, list[str]]:
    """
    Check a single repository for concrete evidence of each technology in
    TECH_RULES, scanning every folder (not just the root).

    Returns technology -> list of evidence strings. Technologies with no
    evidence are left out.
    """
    async with httpx.AsyncClient() as client:
        paths = await fetch_repo_tree(owner, repo, client)
        to_read = manifest_paths(paths, MAX_MANIFESTS_PER_REPO)
        contents = await asyncio.gather(
            *(fetch_file_content(owner, repo, path, client) for path in to_read)
        )

    manifests = {path: text for path, text in zip(to_read, contents) if text}
    return detect_technologies(paths, manifests)


async def inspect_repo(owner: str, repo: str) -> dict:
    """
    Everything the analysis keeps about one repository, from the same
    tree request fingerprint_repo makes plus one commit-count request:

    - "technologies": technology -> evidence strings (as fingerprint_repo)
    - "signals":      tests / CI / README / frontend+backend / size
                      (services/repo_profile.py)
    - "commit_count": commits authored by `owner` on the default branch
    """
    async with httpx.AsyncClient() as client:
        paths = await fetch_repo_tree(owner, repo, client)
        to_read = manifest_paths(paths, MAX_MANIFESTS_PER_REPO)
        results = await asyncio.gather(
            *(fetch_file_content(owner, repo, path, client) for path in to_read),
            fetch_commit_count(owner, repo, client),
        )

    contents, commit_count = results[:-1], results[-1]
    manifests = {path: text for path, text in zip(to_read, contents) if text}
    return {
        "technologies": detect_technologies(paths, manifests),
        "signals": project_signals(paths),
        "commit_count": commit_count,
    }
