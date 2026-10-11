"""
Skill catalog: which resume phrasings count as which skill, what category
each skill is reported under, and how it is checked.

The catalog itself is data, in app/skills_catalog.json, so adding or
changing a skill means editing one JSON entry rather than code. This
module loads it once, validates it (a typo fails at startup, not silently
at runtime) and exposes:

- SKILLS            name -> skill entry (dict), in catalog order
- CATEGORIES        category names in report order
- SKILL_ALIASES     every alias (lower-case) -> skill name
- extract_skill_names(text)   the skills a resume claims

Two kinds of alias exist. Normal aliases ("python", "machine learning")
match anywhere as a whole token. Strict aliases are short or everyday
words ("c", "word", "excel", "iam") that would match all over a resume,
so they only count as an item in a list - next to a comma, bullet, pipe,
slash or bracket - as in "Python, C, C++" or "(Excel, PowerPoint, Word)".
"""
import json
import re
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("skills_catalog.json")

CHECK_TYPES = {"github", "manual"}
RULE_KEYS = {"marker_files", "extensions", "min_files", "file_label", "dependencies", "images", "any_repo"}

# Status shown for skills that can't be checked from code.
NOT_CHECKABLE = "Not checkable on GitHub"


def _load_catalog(path: Path) -> tuple[list[str], dict[str, dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = list(data["categories"])
    skills: dict[str, dict] = {}
    seen_aliases: dict[str, str] = {}

    for entry in data["skills"]:
        name = entry["name"]
        if name in skills:
            raise ValueError(f"Duplicate skill in catalog: {name}")
        if entry.get("category") not in categories:
            raise ValueError(f"{name}: unknown category {entry.get('category')!r}")
        if entry.get("check") not in CHECK_TYPES:
            raise ValueError(f"{name}: check must be one of {sorted(CHECK_TYPES)}")

        rules = entry.get("rules", {})
        unknown = set(rules) - RULE_KEYS
        if unknown:
            raise ValueError(f"{name}: unknown rule keys {sorted(unknown)}")
        if entry["check"] == "github" and not rules:
            raise ValueError(f"{name}: a 'github' skill needs rules")
        if entry["check"] == "manual" and not entry.get("reason"):
            raise ValueError(f"{name}: a 'manual' skill needs a reason")

        aliases = [a.lower() for a in entry.get("aliases", [])]
        strict = [a.lower() for a in entry.get("strict_aliases", [])]
        if not aliases and not strict:
            raise ValueError(f"{name}: needs at least one alias")
        for alias in aliases + strict:
            if alias in seen_aliases:
                raise ValueError(f"Alias {alias!r} used by both {seen_aliases[alias]} and {name}")
            seen_aliases[alias] = name

        skills[name] = {**entry, "aliases": aliases, "strict_aliases": strict, "rules": rules}

    return categories, skills


CATEGORIES, SKILLS = _load_catalog(CATALOG_PATH)

SKILL_ALIASES: dict[str, str] = {
    alias: name
    for name, skill in SKILLS.items()
    for alias in skill["aliases"] + skill["strict_aliases"]
}

SUPPORTED_SKILLS: list[str] = list(SKILLS)

# Characters that separate items in a skills list. A strict alias must
# touch at least one of these, so "Python, C, C++" matches C but
# "Grade: C" or "Section C" does not.
_SEPARATORS = ",;|•/()·"
_SEP_CLASS = re.escape(_SEPARATORS)


def _normal_pattern(alias: str) -> re.Pattern:
    # Whole-token match: not glued to other letters/digits. Lookarounds
    # instead of \b so aliases ending in symbols ("c++", "node.js") work.
    return re.compile(r"(?<![a-z0-9_])" + re.escape(alias) + r"(?![a-z0-9_+#])")


def _strict_pattern(alias: str) -> re.Pattern:
    a = re.escape(alias)
    before_sep = rf"(?<=[{_SEP_CLASS}])[ \t]*"
    before_edge = r"(?:^|(?<=:))[ \t]*"
    after_sep = rf"(?=[ \t]*[{_SEP_CLASS}])"
    after_edge = r"(?=[ \t]*$)"
    # Separator on at least one side; the other side may be a line edge,
    # or a colon before it ("Languages: C, Python"). A colon after it
    # means it's a label ("GitHub: github.com/..."), not a skill.
    return re.compile(
        rf"(?:{before_sep}{a}(?:{after_sep}|{after_edge}))|(?:{before_edge}{a}{after_sep})",
        re.MULTILINE,
    )


_NORMAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (_normal_pattern(alias), name)
    for name, skill in SKILLS.items()
    for alias in skill["aliases"]
]
_STRICT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (_strict_pattern(alias), name)
    for name, skill in SKILLS.items()
    for alias in skill["strict_aliases"]
]


# Lines that are contact details rather than skills ("LinkedIn | GitHub",
# "email@x.com | +91 ..."); strict aliases are not matched on them.
_CONTACT_HINTS = ("@", "linkedin", "http", "www.", ".com", "+91", "phone", "email")


def extract_skill_names(text: str) -> list[str]:
    """Skills claimed in `text`, as catalog names, sorted alphabetically."""
    lower = text.lower()
    list_text = "\n".join(
        line for line in lower.splitlines()
        if not any(hint in line for hint in _CONTACT_HINTS)
    )
    found = {name for pattern, name in _NORMAL_PATTERNS if pattern.search(lower)}
    found |= {name for pattern, name in _STRICT_PATTERNS if pattern.search(list_text)}
    return sorted(found)


def get_skill(name: str) -> dict | None:
    return SKILLS.get(name)


def is_checkable(name: str) -> bool:
    """True unless the catalog marks the skill as 'manual'. Unknown skills count as checkable."""
    skill = SKILLS.get(name)
    return skill is None or skill["check"] == "github"


def category_of(name: str) -> str:
    skill = SKILLS.get(name)
    return skill["category"] if skill else "Other"


def category_rank(name: str) -> int:
    category = category_of(name)
    return CATEGORIES.index(category) if category in CATEGORIES else len(CATEGORIES)
