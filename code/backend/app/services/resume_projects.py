"""
Projects section parsing: turns the lines of a resume's "Projects"
section into structured projects - a title, its tech stack and dates
(often written on the title line), and the description points under it.

Resumes write projects in a few common ways, all handled here:

    Energy Consumption Analysis in Smart Buildings | Python   Jan 2025 - Apr 2025
    • Analyzed building energy and weather datasets to find
      usage patterns.                       <- wrapped line, joined to the point above
    • Applied PCA for dimensionality reduction.

    Credit Card Fraud Detection |
    Python, Scikit-learn, MySQL             <- tech stack on its own line

    DevProof Dashboard - a React and FastAPI app for evidence review
                                            <- title and description on one line

PDF text extraction sometimes drops the bullet characters, so titles are
also recognised by shape (a "|" separator, or a short Title Case line)
rather than only by "the line without a bullet".

Pure logic on text, so it is tested without PDFs.
"""
import re

from ..skills_dictionary import SKILL_ALIASES

PROJECT_HEADERS = {"projects", "personal projects", "academic projects", "key projects", "major projects"}

# Headers that end the Projects section (lower-cased, without trailing ':').
SECTION_HEADERS = {
    "experience", "work experience", "professional experience", "internships", "internship",
    "education", "skills", "technical skills", "certifications", "certificates", "achievements",
    "publications", "summary", "objective", "contact", "awards", "extracurricular activities",
    "extra-curricular activities", "positions of responsibility", "leadership", "activities",
    "coursework", "relevant coursework", "languages", "interests", "hobbies", "volunteering",
} | PROJECT_HEADERS

# Bullet glyphs PDF extraction produces: real bullets, dashes, private-use
# Wingdings bullets, and pdfminer's "(cid:NN)" placeholders.
_BULLET = re.compile(r"^\s*(?:[•●▪◦‣∙·○■□➢➤►▸*\-–—]|\(cid:\d+\))\s*")

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE = rf"(?:{_MONTH}\s*'?\d{{2,4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
_PERIOD = re.compile(
    rf"\(?\b{_DATE}\s*(?:[-–—]|to)\s*(?:{_DATE}|present|current|ongoing|now)\b\)?|\(?\b{_MONTH}\s*'?\d{{2,4}}\b\)?",
    re.IGNORECASE,
)
_LINK_WORDS = re.compile(r"\b(?:github|link|live|demo|code|repo|website|url)\b", re.IGNORECASE)
_URL = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|io|app|dev|org|in)/\S*", re.IGNORECASE)
_SMALL_WORDS = {"a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "using", "via", "&", "by", "at"}
_TERMINAL = (".", "!", "?")


def _strip_bullet(line: str) -> tuple[bool, str]:
    match = _BULLET.match(line)
    if match and not line.lstrip().startswith(("--",)):
        return True, line[match.end():].strip()
    return False, line.strip()


def _header_key(line: str) -> str:
    return line.strip().strip(":•-").strip().lower()


def is_title_case(text: str) -> bool:
    """Most longer words capitalised, like a heading ("Smart Building Energy Analysis")."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9.+#'-]*", text) if w.lower() not in _SMALL_WORDS]
    if not words:
        return False
    capitalised = sum(1 for w in words if w[0].isupper())
    return capitalised / len(words) >= 0.7


def looks_like_title(line: str) -> bool:
    """A project title line: has a '|' separator, or is a short Title Case phrase."""
    if "|" in line:
        return True
    text = _PERIOD.sub("", line).strip(" -–—,")
    words = text.split()
    return (
        0 < len(words) <= 10
        and not text.endswith(_TERMINAL)
        and not text[:1].islower()
        and is_title_case(text)
    )


def looks_like_tech_list(line: str) -> bool:
    """'Python, Scikit-learn, MySQL' - comma-separated short items, mostly known skills."""
    parts = [p.strip() for p in re.split(r"[,|/]", line) if p.strip()]
    if len(parts) < 2 or any(len(p.split()) > 3 for p in parts):
        return False
    known = sum(1 for p in parts if p.lower() in SKILL_ALIASES)
    return known >= max(1, len(parts) // 2)


def split_tech(text: str) -> list[str]:
    """'Python, Scikit-learn | MySQL' -> ['Python', 'Scikit-learn', 'MySQL']."""
    text = _URL.sub(" ", text)
    text = _LINK_WORDS.sub(" ", text)
    items = [p.strip(" .:;()[]") for p in re.split(r"[,|/•·]|\s{2,}", text)]
    seen: list[str] = []
    for item in items:
        if item and item.lower() not in {s.lower() for s in seen}:
            seen.append(item)
    return seen


def parse_title(line: str) -> dict:
    """
    Split a title line into the project name, its tech stack, its dates
    and (for 'Name - description' lines) an inline description.
    """
    period_match = _PERIOD.search(line)
    period = period_match.group(0).strip("() ") if period_match else None
    if period_match:
        line = (line[:period_match.start()] + " " + line[period_match.end():]).strip()

    inline = None
    if "|" in line:
        name, _, tail = line.partition("|")
        tech = split_tech(tail)
    else:
        name, tech = line, []
        # "Name - short description" / "Name: description"
        match = re.match(r"^(.{3,80}?)\s+[-–—:]\s+(.+)$", line)
        if match and is_title_case(match.group(1)):
            name, inline = match.group(1), match.group(2).strip()
        # "Name (Python, Flask)"
        paren = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
        if paren and looks_like_tech_list(paren.group(2) + ","):
            name, tech = paren.group(1), split_tech(paren.group(2))

    name = _URL.sub("", name).strip(" -–—:|,")
    return {"name": name, "tech_stack": tech, "period": period, "inline": inline}


def _new_project(title: dict) -> dict:
    project = {
        "name": title["name"],
        "tech_stack": title["tech_stack"],
        "period": title["period"],
        "bullets": [],
        "_open_tech": not title["tech_stack"] and title.get("trailing_pipe", False),
    }
    if title.get("inline"):
        project["bullets"].append(title["inline"])
    return project


def section_lines(text: str) -> list[str]:
    """The lines between a Projects header and the next section header."""
    lines: list[str] = []
    inside = False
    for raw in text.splitlines():
        key = _header_key(raw)
        if key in PROJECT_HEADERS:
            inside = True
            continue
        if inside and key in SECTION_HEADERS:
            break
        if inside and raw.strip():
            lines.append(raw.rstrip())
    return lines


def has_inline_title(line: str) -> bool:
    """'DevProof Dashboard - a React app ...': a Title Case name, a dash or colon, then text."""
    match = re.match(r"^(.{3,80}?)\s+[-–—:]\s+(.+)$", line)
    return bool(match) and len(match.group(1).split()) <= 8 and is_title_case(match.group(1))


def parse_projects(text: str) -> list[dict]:
    """
    Structured projects from a resume's text:
    [{"name", "tech_stack": [...], "period": str | None, "bullets": [...]}].

    Each line in the Projects section is, in this order of checks:
    1. a bullet point                  -> a description point of the current project
    2. a date range (before any point) -> the current project's dates
    3. a tech list (before any point)  -> the current project's tech stack
    4. starting lower-case             -> a wrapped continuation of the last point
    5. a title (has "|", Title Case, or "Name - description") -> a new project
    6. anything else                   -> continuation of an unfinished point, or a new point
    """
    projects: list[dict] = []
    current: dict | None = None

    for raw in section_lines(text):
        is_bullet, line = _strip_bullet(raw)
        if not line:
            continue
        points = current["bullets"] if current else None
        previous = points[-1] if points else None

        if is_bullet:
            if current is None:
                # Points before any title: each one is its own project.
                current = _new_project(parse_title(line))
                projects.append(current)
            else:
                points.append(line)
                current["_open_tech"] = False
            continue

        if current is not None and not points and _PERIOD.fullmatch(line.strip("() ")):
            current["period"] = line.strip("() ")
        elif current is not None and not points and "|" not in line and (
            current["_open_tech"] or looks_like_tech_list(line)
        ):
            current["tech_stack"].extend(t for t in split_tech(line) if t not in current["tech_stack"])
            current["_open_tech"] = False
        elif previous is not None and line[:1].islower():
            points[-1] = f"{previous} {line}"
        elif looks_like_title(line) or has_inline_title(line):
            title = parse_title(line)
            title["trailing_pipe"] = line.rstrip().endswith("|")
            current = _new_project(title)
            projects.append(current)
        elif previous is not None and not previous.endswith(_TERMINAL):
            points[-1] = f"{previous} {line}"
        elif current is not None:
            points.append(line)  # a point written without a bullet glyph
        else:
            current = _new_project(parse_title(line))
            projects.append(current)

    for project in projects:
        project.pop("_open_tech", None)
        project["bullets"] = [re.sub(r"\s+", " ", b).strip() for b in project["bullets"]]
    return [p for p in projects if p["name"]]
