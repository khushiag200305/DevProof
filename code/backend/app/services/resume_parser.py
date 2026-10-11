"""
Resume Intelligence (Iteration 1).

Extracts structured candidate data from a resume PDF's raw text:
- name          (spaCy PERSON NER over the resume header, with a
                  regex fallback for headers spaCy misses)
- skills        (curated dictionary + regex normalization, Section 3.1)
- projects      ("Projects" section heuristic: section header, then
                  following bullet/lines up to the next section header)
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

from ..skills_dictionary import SKILL_ALIASES

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
    Find mentions of known skills in resume text.

    Uses lookaround assertions instead of \\b, since \\b is unreliable
    right after punctuation characters (e.g. it fails to correctly
    bound "C++", which ends in non-word characters). This checks that
    the alias isn't immediately preceded/followed by another letter,
    digit, or underscore, which achieves a correct "whole token" match
    regardless of what the alias itself contains.
    """
    lower_text = text.lower()
    found = set()
    for alias, normalized in SKILL_ALIASES.items():
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, lower_text):
            found.add(normalized)
    return sorted(found)


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


def extract_projects(text: str) -> list[str]:
    """
    Heuristic extraction of project names from a resume's "Projects"
    section (or "Personal Projects" / "Academic Projects"): find the
    section header, then read lines until the next known section header,
    treating each non-empty line/bullet as one project entry.

    Keeps only a short project "name" per entry (first ~8 words) since
    resume project lines often continue into a description on the same
    line.
    """
    lines = [line.strip() for line in text.splitlines()]
    projects: list[str] = []
    in_projects_section = False

    for line in lines:
        lower = line.strip(" :•-").lower()

        if lower in ("projects", "personal projects", "academic projects"):
            in_projects_section = True
            continue

        if in_projects_section and lower in SECTION_HEADERS:
            break

        if not in_projects_section or not line.strip():
            continue

        # Strip common bullet characters, then keep a short "name" -
        # the first clause before a dash/colon, or the first 8 words.
        entry = re.sub(r"^[•\-*\s]+", "", line).strip()
        if not entry:
            continue
        entry = re.split(r"[:–—-]\s", entry, maxsplit=1)[0].strip()
        words = entry.split()
        name = " ".join(words[:8])
        if name:
            projects.append(name)

    return projects
