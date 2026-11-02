"""
Resume Intelligence (Iteration 1).

Extracts structured candidate data from a resume PDF's raw text:
- name          (spaCy PERSON NER over the resume header, with a
                  regex fallback for headers spaCy misses)
- skills        (curated dictionary + regex normalization, Section 3.1)
- projects      (title, tech stack, dates and description points per
                  project - see services/resume_projects.py)
- GitHub URL    (regex over github.com links)

This module does text extraction and rule-based extraction only - no
ML scoring, no GitHub calls. Text extraction uses pdfplumber (works
better than PyMuPDF did on the multi-column resumes we tested against,
which is also why the upload endpoint still accepts a manual GitHub URL
override: PDF extraction from graphic-heavy resumes is unreliable).
"""
import io
import re
from functools import lru_cache

import pdfplumber
import spacy

from ..skills_dictionary import SKILL_ALIASES, extract_skill_names
from .resume_projects import parse_projects

GITHUB_URL_PATTERN = re.compile(
    r"(?<![\w.])(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)?",
    re.IGNORECASE,
)

# Section headers used to find the boundaries of the "Projects" section
# and to know where it ends. Lower-cased for matching.
SECTION_HEADERS = (
    "experience", "work experience", "education", "skills",
    "technical skills", "projects", "personal projects",
    "academic projects", "certifications", "achievements",
    "publications", "summary", "objective", "contact", "awards",
)

# A line that looks like a name: 1-4 title-cased words, no digits,
# no "@" (rules out emails), no punctuation-heavy contact lines.
_NAME_LINE_PATTERN = re.compile(r"^[A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3}$")


@lru_cache(maxsize=1)
def _nlp():
    """Load spaCy's small English model once per process."""
    return spacy.load("en_core_web_sm")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF's bytes using pdfplumber."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_skills(text: str) -> list[str]:
    """
    Find the skills a resume claims, using the aliases in the skill
    catalog (app/skills_catalog.json). See app/skills_dictionary.py for
    how short words like "C" or "Word" are matched only as list items.
    """
    return extract_skill_names(text)


def extract_github_links(text: str) -> list[str]:
    """Find all GitHub profile/repo URLs mentioned in resume text."""
    return sorted(set(GITHUB_URL_PATTERN.findall(text)))


def extract_github_url(text: str) -> str | None:
    """Return the first (or only) GitHub link found, if any."""
    links = extract_github_links(text)
    return links[0] if links else None


def extract_github_username(github_link: str) -> str | None:
    """
    Pull the username out of a github.com link.

    Handles links with or without a protocol/www prefix, e.g.:
    'github.com/khushiag200305' -> 'khushiag200305'
    'https://github.com/khushiag200305/DevProof' -> 'khushiag200305'
    """
    match = re.search(r"github\.com/([A-Za-z0-9_-]+)", github_link, re.IGNORECASE)
    return match.group(1) if match else None


def extract_name(text: str) -> str | None:
    """
    Best-effort candidate name extraction.

    Resumes almost always lead with the candidate's name, so this first
    checks whether the first line looks like a name (and isn't a skill
    keyword). That heuristic runs first, ahead of spaCy: on short, sparse
    header text (no surrounding sentence context), spaCy's small model
    can mistag an all-caps technology word as a PERSON entity - e.g. it
    tags "Docker" as PERSON given just a two-line header - so a plain
    first-line check is the more reliable signal here. spaCy's PERSON
    NER is the fallback, for headers that don't follow the "name on its
    own first line" convention.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return None

    first_line = lines[0]
    if (
        _NAME_LINE_PATTERN.match(first_line)
        and "@" not in first_line
        and first_line.lower() not in SKILL_ALIASES
    ):
        return first_line

    header = "\n".join(lines[:5])
    doc = _nlp()(header)
    for ent in doc.ents:
        candidate = ent.text.strip()
        if ent.label_ == "PERSON" and candidate.lower() not in SKILL_ALIASES:
            return candidate

    return None


def extract_project_details(text: str) -> list[dict]:
    """
    Structured projects from the resume's Projects section: name, tech
    stack, dates and description points (services/resume_projects.py).
    """
    return parse_projects(text)


def extract_projects(text: str) -> list[str]:
    """Just the project names, in resume order."""
    return [p["name"] for p in parse_projects(text)]


def read_resume_text(path: str) -> str | None:
    """Text of a stored resume PDF, or None if the file is gone or unreadable."""
    try:
        with open(path, "rb") as pdf_file:
            return extract_text_from_pdf(pdf_file.read())
    except Exception:  # pragma: no cover - depends on the stored file
        return None
