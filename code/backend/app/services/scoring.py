"""
Explainable, rule-based evidence scoring (Section 6 of the proposal).

Every point added to a skill's score is tied to a concrete, listable
reason - never a black-box ML output. Carried over from the pre-refactor
prototype (see github_client.py's module docstring); Iteration 3 is
where this gets persisted against the Evidence table instead of being
recomputed on every request.
"""
from datetime import datetime, timedelta, timezone

# Configurable scoring weights (heuristic starting points, per Section 3.4
# of the proposal - not a claim of statistical optimality).
SCORE_WEIGHTS = {
    "fingerprint_match": 40,   # concrete file/keyword evidence found
    "language_match": 20,      # repo's GitHub-reported primary language matches
    "not_fork": 20,            # original work, not a forked repository
    "recent_activity": 20,     # repo updated within the last 12 months
}

STRONG_THRESHOLD = 70
GOOD_THRESHOLD = 40

INTERVIEW_QUESTION_TEMPLATES = {
    "Docker": "How did you use Docker to containerize this application?",
    "React": "Walk me through how you structured components in one of your React projects.",
    "FastAPI": "Can you describe an endpoint you built with FastAPI and why you chose it?",
    "Flask": "Can you walk through how you structured routes in a Flask project?",
    "Django": "What Django features (ORM, admin, etc.) did you rely on in your project?",
}


def default_interview_question(skill: str) -> str:
    return INTERVIEW_QUESTION_TEMPLATES.get(
        skill, f"Can you walk through a specific project where you used {skill}?"
    )


def is_recently_updated(updated_at: str, months: int = 12) -> bool:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    return updated >= cutoff


def _repo_evidence(skill: str, repo: dict, fingerprints: dict[str, dict]) -> list[dict]:
    """
    Evidence items one repository provides for one skill, each with the
    points it is worth.

    The "original work" and "recent activity" bonuses only count once the
    repo shows evidence of the skill itself (a fingerprint match or a
    matching primary language). Without that rule, any recently updated,
    non-forked repo would add 40 points to every claimed skill, even ones
    it has nothing to do with.
    """
    name = repo["name"]
    items: list[dict] = []

    detected = fingerprints.get(name, {}).get("detected_technologies", {})
    if detected.get(skill):
        items.append({
            "repo": name,
            "type": "fingerprint_match",
            "description": "; ".join(detected[skill]),
            "weight": SCORE_WEIGHTS["fingerprint_match"],
        })

    language = repo.get("language")
    if language and language.lower() == skill.lower():
        items.append({
            "repo": name,
            "type": "language_match",
            "description": f"primary language matches ({language})",
            "weight": SCORE_WEIGHTS["language_match"],
        })

    if not items:
        return []

    if not repo.get("is_fork"):
        items.append({
            "repo": name,
            "type": "not_fork",
            "description": "original repository, not a fork",
            "weight": SCORE_WEIGHTS["not_fork"],
        })

    if is_recently_updated(repo.get("updated_at") or ""):
        items.append({
            "repo": name,
            "type": "recent_activity",
            "description": "updated within the last 12 months",
            "weight": SCORE_WEIGHTS["recent_activity"],
        })

    return items


def score_skill(skill: str, repos: list[dict], fingerprints: dict[str, dict]) -> dict:
    """
    Computes an explainable 0-100 evidence score for a single claimed
    skill, by checking every repo for supporting signals and taking the
    strongest single repo's score (rather than summing across repos,
    which would unfairly reward having many mediocre repos).

    Returns the score, its classification, human-readable `reasons`, and
    the same evidence as structured `evidence` items (repo, type,
    description, weight) for storing in the Evidence table.
    """
    best_score = 0
    best_evidence: list[dict] = []

    for repo in repos:
        evidence = _repo_evidence(skill, repo, fingerprints)
        score = sum(item["weight"] for item in evidence)
        if score > best_score:
            best_score = score
            best_evidence = evidence

    best_reasons = [f"{item['repo']}: {item['description']}" for item in best_evidence]
    score = min(best_score, 100)

    if score >= STRONG_THRESHOLD:
        classification = "Strong Evidence"
    elif score >= GOOD_THRESHOLD:
        classification = "Good Evidence"
    else:
        classification = "Needs Verification"

    result = {
        "skill": skill,
        "score": score,
        "classification": classification,
        "reasons": best_reasons if best_reasons else ["No supporting evidence found in analyzed repositories"],
        "evidence": best_evidence,
    }

    if classification == "Needs Verification":
        result["interview_question"] = default_interview_question(skill)

    return result
