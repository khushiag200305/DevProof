"""
Technology fingerprinting: checks a repository for concrete evidence of
each technology (marker files, and where relevant, keyword matches
inside them) rather than trusting GitHub's reported language percentages
alone. See Section 3.3 / Section 6 of the proposal.

Carried over from the pre-refactor prototype (see github_client.py's
module docstring) - the fingerprint rule set moves into a formal
technology fingerprint database as part of Iteration 3.
"""
import httpx

from .github_client import fetch_file_content, fetch_repo_root_files

# Per-technology detection rules: which files to look for, and (for
# text-based files) which keywords inside them count as evidence.
FINGERPRINT_RULES = {
    "Docker": {"files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]},
    "React": {"files": ["package.json"], "keywords": ["\"react\"", "\"react-dom\""]},
    "Express": {"files": ["package.json"], "keywords": ["\"express\""]},
    "Node.js": {"files": ["package.json"], "keywords": []},
    "Flask": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["flask"]},
    "FastAPI": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["fastapi"]},
    "Django": {"files": ["requirements.txt", "pyproject.toml"], "keywords": ["django"]},
}


async def fingerprint_repo(owner: str, repo: str) -> dict:
    """
    Check a single repository for concrete evidence of each technology
    in FINGERPRINT_RULES: presence of a marker file, and (where relevant)
    a matching keyword inside that file's content.

    Returns a dict of technology -> list of evidence strings found.
    An empty list means no evidence was found for that technology.
    """
    evidence: dict[str, list[str]] = {tech: [] for tech in FINGERPRINT_RULES}

    async with httpx.AsyncClient() as client:
        root_files = await fetch_repo_root_files(owner, repo, client)

        for tech, rule in FINGERPRINT_RULES.items():
            matching_files = [f for f in rule["files"] if f in root_files]
            if not matching_files:
                continue

            keywords = rule.get("keywords", [])
            if not keywords:
                # File presence alone is sufficient evidence (e.g. Dockerfile).
                evidence[tech].append(f"{matching_files[0]} present")
                continue

            for filename in matching_files:
                content = await fetch_file_content(owner, repo, filename, client)
                lower_content = content.lower()
                for keyword in keywords:
                    if keyword.lower() in lower_content:
                        evidence[tech].append(f"'{keyword}' found in {filename}")

    return evidence
