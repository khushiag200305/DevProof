"""
Curated skill dictionary: maps variant phrasing found in resumes to a
single normalized skill name (e.g. "ReactJS" / "React.js" -> "React").

Covers the MVP's supported technology set (14 starter technologies, per
the proposal's Section 3.1) and stays intentionally small and explicit
rather than ML-driven, since every match needs to be traceable back to a
literal alias for the explainability requirement.
"""

SKILL_ALIASES: dict[str, str] = {
    "python": "Python",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "express": "Express",
    "expressjs": "Express",
    "express.js": "Express",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "django": "Django",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
}

# Technologies covered by SKILL_ALIASES, in a stable, de-duplicated order
# -- useful anywhere the UI/tests need the canonical supported set.
SUPPORTED_SKILLS: list[str] = sorted(set(SKILL_ALIASES.values()))
