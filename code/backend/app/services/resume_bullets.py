"""
Resume bullet generator: suggests specific, evidence-based resume lines
for a candidate's projects, from what the analysis found in each
repository (description, detected technologies, tests, CI, commits, ...).

Optionally tailored to a job description: the skills it asks for are
found with the same catalog used for resumes, projects that show those
skills come first, bullets that mention them come first, and the report
says which of them the candidate can already prove, has only claimed, or
is missing.

Template-based and deterministic (no AI model), so every line can be
traced back to something in the repository. Pure logic: plain dicts in,
dicts out.
"""
import re

from ..skills_dictionary import extract_skill_names
from .portfolio import VERIFIED_STATUSES, active_period, rank_projects

MAX_PROJECTS = 5
MAX_BULLETS = 5

DATABASES = ["PostgreSQL", "MySQL", "MongoDB", "SQL"]
DATA_TOOLS = ["Machine Learning", "Pandas", "NumPy", "Data Visualization", "Tableau"]
_ACRONYMS = {"api", "ui", "ux", "ml", "ai", "db", "cli", "sql", "crm", "erp", "iot", "nlp", "llm", "cv", "os"}
_VERBS = ("built", "created", "developed", "implemented", "designed", "made", "wrote", "engineered")


def humanize_repo_name(name: str) -> str:
    """'shop-api' -> 'Shop API', 'devProof' stays 'devProof'."""
    if any(c.isupper() for c in name) and "-" not in name and "_" not in name:
        return name
    words = [w for w in re.split(r"[-_\s]+", name) if w]
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.capitalize() for w in words)


def join_words(items: list[str]) -> str:
    """['A'] -> 'A', ['A', 'B'] -> 'A and B', ['A', 'B', 'C'] -> 'A, B and C'."""
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _clean_description(text: str) -> str:
    text = text.strip().rstrip(".").strip()
    first = text.split(" ", 1)[0]
    # Lower-case the first letter unless the first word is an acronym ("REST").
    is_acronym = len(first) > 1 and first.isupper()
    if first[:1].isupper() and not is_acronym:
        text = text[0].lower() + text[1:]
    return text


def _order_skills(skills: list[str], priority: set[str], claimed: set[str]) -> list[str]:
    """Job-description skills first, then claimed ones, then the rest."""
    return sorted(skills, key=lambda s: (s not in priority, s not in claimed, s.lower()))


def project_bullets(repo: dict, claimed: set[str], jd_skills: set[str] | None = None) -> list[dict]:
    """
    Suggested resume lines for one repository, best first. Each bullet is
    {"text": str, "skills": [skills it mentions]}.
    """
    jd_skills = jd_skills or set()
    name = humanize_repo_name(repo["name"])
    techs = _order_skills(list(repo.get("technologies", [])), jd_skills, claimed)
    stack = techs[:4]
    bullets: list[dict] = []

    # 1. What was built, with what.
    description = (repo.get("description") or "").strip()
    using = f" using {join_words(stack)}" if stack else ""
    if description:
        cleaned = _clean_description(description)
        if cleaned.lower().startswith(_VERBS):
            main = cleaned[0].upper() + cleaned[1:]
        elif cleaned.lower().startswith(("a ", "an ", "the ")):
            main = f"Built {cleaned}"
        else:
            main = f"Built {name}, {cleaned}"
        text = f"{main}{using}."
    elif stack:
        text = f"Built {name}{using}."
    elif repo.get("language"):
        text = f"Built {name} in {repo['language']}."
    else:
        text = f"Built {name}."
    bullets.append({"text": text, "skills": stack})

    # 2. Architecture.
    if repo.get("has_frontend_and_backend"):
        bullets.append({
            "text": "Designed and developed both the frontend and the backend as separate modules.",
            "skills": [],
        })

    # 3. Data layer.
    dbs = [d for d in DATABASES if d in techs]
    if "SQL" in dbs and len(dbs) > 1:
        dbs.remove("SQL")
    if dbs:
        bullets.append({
            "text": f"Modelled and stored the application's data in {join_words(dbs)}.",
            "skills": dbs,
        })

    # 4. Data / ML work.
    data_tools = [t for t in DATA_TOOLS if t in techs]
    if data_tools:
        bullets.append({
            "text": f"Analysed and worked with data using {join_words(data_tools)}.",
            "skills": data_tools,
        })

    # 5. Containers.
    if "Docker" in techs:
        compose = " and Docker Compose for a one-command local setup" if repo.get("has_compose") else ""
        bullets.append({"text": f"Containerized the application with Docker{compose}.", "skills": ["Docker"]})

    # 6. Quality.
    if repo.get("has_tests") and repo.get("has_ci"):
        bullets.append({
            "text": "Wrote automated tests and set up continuous integration to run them on every change.",
            "skills": [],
        })
    elif repo.get("has_tests"):
        bullets.append({"text": "Wrote automated tests for the core functionality.", "skills": []})
    elif repo.get("has_ci"):
        bullets.append({"text": "Set up continuous integration (CI) for the project.", "skills": []})

    # 7. Delivery.
    if repo.get("homepage"):
        bullets.append({"text": f"Deployed a live version at {repo['homepage']}.", "skills": []})
    commits = repo.get("commit_count") or 0
    if commits >= 10:
        period = active_period(repo.get("created_at"), repo.get("pushed_at"))
        when = f" ({period})" if period else ""
        bullets.append({"text": f"Developed the project across {commits} commits{when}.", "skills": []})
    if (repo.get("stars") or 0) >= 3:
        bullets.append({"text": f"Earned {repo['stars']} stars on GitHub.", "skills": []})

    # The main line stays first; the rest put job-description skills first.
    head, rest = bullets[:1], bullets[1:]
    rest.sort(key=lambda b: not (set(b["skills"]) & jd_skills))
    return (head + rest)[:MAX_BULLETS]


def job_match(job_description: str, skills: list[dict]) -> dict:
    """
    Which catalog skills a job description asks for, split by what the
    candidate can show: proven on GitHub, only claimed, or missing.
    """
    wanted = extract_skill_names(job_description)
    claimed = {s["skill_name"] for s in skills}
    verified = {s["skill_name"] for s in skills if s.get("status") in VERIFIED_STATUSES}

    proven = [s for s in wanted if s in verified]
    claimed_only = [s for s in wanted if s in claimed and s not in verified]
    missing = [s for s in wanted if s not in claimed]
    return {
        "skills": wanted,
        "proven": proven,
        "claimed_only": claimed_only,
        "missing": missing,
        "readiness": round(100 * len(proven) / len(wanted)) if wanted else None,
        "tips": (
            [f"{s}: on your resume, but no repository shows it yet - add a small project "
             "that uses it, or remove it from the resume." for s in claimed_only]
            + [f"{s}: the job asks for it and it isn't on your resume - learn it and build "
               "something with it to prove it." for s in missing]
        ),
    }


def bullet_report(repos: list[dict], skills: list[dict], job_description: str | None = None) -> dict:
    """
    Resume line suggestions for the candidate's best original projects,
    tailored to `job_description` when one is given.
    """
    claimed = {s["skill_name"] for s in skills}
    match = job_match(job_description, skills) if job_description and job_description.strip() else None
    jd_skills = set(match["skills"]) if match else set()

    ranked = rank_projects(repos, claimed)
    if jd_skills:
        ranked.sort(key=lambda r: -len(set(r.get("technologies", [])) & jd_skills))

    projects = []
    for repo in ranked[:MAX_PROJECTS]:
        projects.append({
            "name": repo["name"],
            "title": humanize_repo_name(repo["name"]),
            "url": repo["url"],
            "matched_skills": sorted(set(repo.get("technologies", [])) & jd_skills),
            "bullets": project_bullets(repo, claimed, jd_skills),
        })
    return {"job_match": match, "projects": projects}
