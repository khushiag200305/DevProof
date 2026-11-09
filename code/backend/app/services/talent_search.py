"""
Talent search for recruiters: find candidates by the skills their GitHub
work actually proves, not just the keywords on their resume.

Pure logic, no database or network: the router turns candidates into
plain "profile" dicts and calls match_profile / search / compare here.

A profile looks like:

    {
        "candidate_id": 7, "name": "...", "email": "...", "github_username": "...",
        "created_at": datetime,
        "skills": {"Python": {"status": "Strong Evidence", "score": 100, "category": "..."}},
        "repos": [{"name": "...", "is_fork": False, "pushed_at": datetime | None}],
    }

and a query:

    {
        "skills": ["Python", "React"],     # what the recruiter is looking for
        "min_level": "good",               # "strong" | "good" | "claimed"
        "match": "all",                    # "all" skills required, or "any"
        "has_github": False,               # only candidates with a GitHub profile
        "min_repos": 0,                    # minimum original (non-fork) repositories
        "active_months": None,             # pushed to an original repo in the last N months
        "text": "",                        # name / email / GitHub username contains
    }
"""
from datetime import datetime, timedelta, timezone

STRONG = "Strong Evidence"
GOOD = "Good Evidence"

LEVELS = ("strong", "good", "claimed")
MATCH_MODES = ("all", "any")

# Strength of each status, used to rank equally-matching candidates.
STATUS_RANK = {STRONG: 3, GOOD: 2}


def normalize_query(raw: dict | None) -> dict:
    """Fill in defaults and clean up a query sent by the frontend."""
    raw = raw or {}
    skills: list[str] = []
    for name in raw.get("skills") or []:
        name = str(name).strip()
        if name and name.lower() not in {s.lower() for s in skills}:
            skills.append(name)
    level = raw.get("min_level") if raw.get("min_level") in LEVELS else "good"
    match = raw.get("match") if raw.get("match") in MATCH_MODES else "all"
    active = raw.get("active_months")
    return {
        "skills": skills,
        "min_level": level,
        "match": match,
        "has_github": bool(raw.get("has_github")),
        "min_repos": max(0, int(raw.get("min_repos") or 0)),
        "active_months": int(active) if active else None,
        "text": str(raw.get("text") or "").strip(),
    }


def meets_level(status: str | None, level: str) -> bool:
    """Does a skill with this evidence status count at the required level?"""
    if level == "strong":
        return status == STRONG
    if level == "good":
        return status in (STRONG, GOOD)
    return True  # "claimed": being on the resume is enough


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def original_repos(profile: dict) -> list[dict]:
    return [r for r in profile.get("repos", []) if not r.get("is_fork")]


def last_active(profile: dict) -> datetime | None:
    """Most recent push to one of the candidate's original repositories."""
    dates = [_as_aware(r.get("pushed_at")) for r in original_repos(profile)]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def match_profile(profile: dict, query: dict, now: datetime | None = None) -> dict | None:
    """
    How one candidate matches a (normalized) query, or None if they don't.
    The result lists which searched skills matched (with their evidence)
    and which are missing, plus a 0-100 match score for ranking.
    """
    now = now or datetime.now(timezone.utc)

    text = query["text"].lower()
    if text and not any(
        text in (profile.get(field) or "").lower() for field in ("name", "email", "github_username")
    ):
        return None
    if query["has_github"] and not profile.get("github_username"):
        return None
    if len(original_repos(profile)) < query["min_repos"]:
        return None
    if query["active_months"]:
        active = last_active(profile)
        if active is None or active < now - timedelta(days=30 * query["active_months"]):
            return None

    by_lower = {name.lower(): (name, info) for name, info in profile.get("skills", {}).items()}
    matched, missing = [], []
    for wanted in query["skills"]:
        found = by_lower.get(wanted.lower())
        if found and meets_level(found[1].get("status"), query["min_level"]):
            name, info = found
            matched.append({"skill": name, "status": info.get("status"), "score": info.get("score")})
        else:
            missing.append(wanted)

    if query["skills"]:
        if query["match"] == "all" and missing:
            return None
        if not matched:
            return None
        # Average evidence score over everything searched for, so a missing
        # skill counts as 0 and candidates proving more skills rank higher.
        score = round(sum(m["score"] or 0 for m in matched) / len(query["skills"]))
    else:
        score = 0

    return {
        "candidate_id": profile["candidate_id"],
        "name": profile.get("name"),
        "email": profile.get("email"),
        "github_username": profile.get("github_username"),
        "created_at": profile.get("created_at"),
        "skill_count": len(profile.get("skills", {})),
        "original_repos": len(original_repos(profile)),
        "last_active": last_active(profile),
        "matched": matched,
        "missing": missing,
        "match_score": score,
    }


def _rank_key(result: dict) -> tuple:
    strength = sum(STATUS_RANK.get(m["status"], 1) for m in result["matched"])
    created = _as_aware(result.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
    return (-len(result["matched"]), -result["match_score"], -strength, -created.timestamp())


def search(profiles: list[dict], raw_query: dict | None, now: datetime | None = None) -> list[dict]:
    """Every matching candidate, best match first."""
    query = normalize_query(raw_query)
    results = [r for p in profiles if (r := match_profile(p, query, now)) is not None]
    return sorted(results, key=_rank_key)


def latest_per_student(profiles: list[dict]) -> list[dict]:
    """
    A student can upload several resumes; search only their most recent
    one so the same person doesn't appear several times. Profiles without
    a user (uploaded before sign-in existed) are all kept.
    """
    latest: dict[int, dict] = {}
    loose: list[dict] = []
    for p in profiles:
        user_id = p.get("user_id")
        if user_id is None:
            loose.append(p)
            continue
        current = latest.get(user_id)
        created = _as_aware(p.get("created_at"))
        if current is None or (created and created > (_as_aware(current.get("created_at")) or created)):
            latest[user_id] = p
    return list(latest.values()) + loose


def mark_new(results: list[dict], since: datetime | None) -> list[dict]:
    """Flag results for candidates who uploaded after `since` (the last time a saved search ran)."""
    since = _as_aware(since)
    for r in results:
        created = _as_aware(r.get("created_at"))
        r["is_new"] = bool(since and created and created > since)
    return results


def compare(profiles: list[dict]) -> dict:
    """
    Side-by-side view of 2-4 candidates: one row per skill any of them
    claims, ordered by how many of them have it, then by name.
    """
    names: dict[str, str] = {}
    for p in profiles:
        for name in p.get("skills", {}):
            names.setdefault(name.lower(), name)

    def cell(p: dict, lower: str) -> dict | None:
        for name, info in p.get("skills", {}).items():
            if name.lower() == lower:
                return {"status": info.get("status"), "score": info.get("score")}
        return None

    rows = []
    for lower, name in names.items():
        cells = [cell(p, lower) for p in profiles]
        backed = sum(1 for c in cells if c and c["status"] in (STRONG, GOOD))
        claimed = sum(1 for c in cells if c)
        rows.append({"skill": name, "cells": cells, "_key": (-backed, -claimed, name.lower())})
    rows.sort(key=lambda r: r.pop("_key"))

    return {
        "candidates": [
            {
                "candidate_id": p["candidate_id"],
                "name": p.get("name"),
                "github_username": p.get("github_username"),
                "original_repos": len(original_repos(p)),
                "last_active": last_active(p),
                "backed_skills": sum(
                    1 for i in p.get("skills", {}).values() if i.get("status") in (STRONG, GOOD)
                ),
                "skill_count": len(p.get("skills", {})),
            }
            for p in profiles
        ],
        "rows": rows,
    }
