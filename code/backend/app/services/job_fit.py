"""
"Which of my resumes fits this job best?" A student pastes a job
description and every one of their uploads is scored against the skills
it asks for:

    proven        on the resume and backed by GitHub (strong or good evidence)
    claimed only  on the resume, but not proven (or not checkable on GitHub)
    missing       the job asks for it and the resume doesn't mention it

Fit score (0-100) = average over the job's skills, where proven counts
100, claimed only 40 and missing 0. Pure logic, no database or network;
skills are recognised with the same catalog as the rest of DevProof.
"""
from datetime import datetime, timezone

from ..skills_dictionary import extract_skill_names

# Evidence statuses that count as proven (same as the portfolio page).
VERIFIED_STATUSES = ("Strong Evidence", "Good Evidence")

PROVEN_POINTS = 100
CLAIMED_POINTS = 40


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def score_resume(wanted: list[str], resume: dict) -> dict:
    """How one resume covers the job's skills."""
    by_lower = {s["skill_name"].lower(): s for s in resume.get("skills", [])}
    proven, claimed_only, missing = [], [], []
    for skill in wanted:
        found = by_lower.get(skill.lower())
        if found is None:
            missing.append(skill)
        elif found.get("status") in VERIFIED_STATUSES:
            proven.append(skill)
        else:
            claimed_only.append(skill)
    points = PROVEN_POINTS * len(proven) + CLAIMED_POINTS * len(claimed_only)
    return {
        "candidate_id": resume["candidate_id"],
        "name": resume.get("name"),
        "created_at": resume.get("created_at"),
        "analyzed": bool(resume.get("analyzed")),
        "visible_to_recruiters": bool(resume.get("visible_to_recruiters")),
        "proven": proven,
        "claimed_only": claimed_only,
        "missing": missing,
        "fit": round(points / len(wanted)) if wanted else 0,
    }


def _rank_key(r: dict) -> tuple:
    # Best fit first; then more proven skills, analyzed before not, newest.
    return (-r["fit"], -len(r["proven"]), not r["analyzed"], -_aware(r["created_at"]).timestamp())


def _reason(best: dict, others: list[dict], total: int) -> str:
    parts = [f"Proves {len(best['proven'])} of the {total} skills this job asks for"]
    if best["claimed_only"]:
        parts.append(f"lists {len(best['claimed_only'])} more without GitHub proof")
    sentence = ", ".join(parts) + "."
    if others:
        runner_up = others[0]
        extra = sorted(set(runner_up["missing"]) - set(best["missing"]))
        if extra:
            sentence += f" Your next best resume doesn't mention {', '.join(extra)}."
        elif len(best["proven"]) > len(runner_up["proven"]):
            sentence += " Your other resumes prove fewer of them."
    return sentence


def _tips(best: dict) -> list[str]:
    return [
        f"{s}: on this resume but not proven yet - push a project that uses it, "
        "or be ready to show it in the interview."
        for s in best["claimed_only"]
    ] + [
        f"{s}: the job asks for it and this resume doesn't mention it - add it if you "
        "know it, ideally with a project that proves it."
        for s in best["missing"]
    ]


def fit_resumes(job_description: str, resumes: list[dict]) -> dict:
    """
    Every resume scored against the job, best first. `resumes` items:
    {candidate_id, name, created_at, analyzed, visible_to_recruiters,
     skills: [{skill_name, status}]}.
    """
    wanted = extract_skill_names(job_description or "")
    if not wanted:
        return {"skills": [], "resumes": [], "best_candidate_id": None, "reason": None, "tips": []}

    ranked = sorted((score_resume(wanted, r) for r in resumes), key=_rank_key)
    best = ranked[0] if ranked else None
    for r in ranked:
        r["best"] = best is not None and r["candidate_id"] == best["candidate_id"]
    return {
        "skills": wanted,
        "resumes": ranked,
        "best_candidate_id": best["candidate_id"] if best else None,
        "reason": _reason(best, ranked[1:], len(wanted)) if best else None,
        "tips": _tips(best) if best else [],
    }
