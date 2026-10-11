"""
Technology detection rules: what in a repository counts as evidence for
each supported skill.

This module is pure logic - no network calls. It works on two inputs that
services/fingerprinting.py fetches from GitHub:

- every file path in the repository (from one recursive tree request), and
- the text of a few dependency/config files ("manifests") found there.

Three kinds of evidence are recognised, all of them concrete and listable
so every score stays explainable:

- marker files     - a file whose presence alone means the technology is
                     used (Dockerfile, pom.xml, CMakeLists.txt, ...)
- source files     - enough files with the language's extension (.py,
                     .java, .cpp, ...). A minimum count keeps one stray
                     script from counting as evidence.
- dependencies     - a package named in a dependency file (package.json,
                     requirements.txt, pom.xml, ...) or a database image
                     in a docker-compose file.
"""
import json
import posixpath
import re

from ..skills_dictionary import SKILLS

# Folders that hold third-party or generated code, not the candidate's own.
IGNORED_DIRS = {
    "node_modules", "vendor", "venv", ".venv", "env", "site-packages",
    "dist", "build", "target", "out", ".git", "__pycache__", "third_party",
    "bower_components", ".next",
}

# Source files needed before a language counts on extensions alone, unless
# a rule sets its own min_files (e.g. one Tableau workbook is enough).
MIN_SOURCE_FILES = 3

COMPOSE_FILES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}

# Dependency/config files whose contents are worth fetching and parsing.
MANIFEST_FILES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "setup.py",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
} | COMPOSE_FILES

# Detection rules for every skill the catalog marks as checkable on GitHub
# (app/skills_catalog.json). Skills marked 'manual' have no rules.
TECH_RULES: dict[str, dict] = {
    name: skill["rules"]
    for name, skill in SKILLS.items()
    if skill["check"] == "github"
}


def is_tooling_config(path: str) -> bool:
    """
    Tool configuration written in a language rather than code in it,
    e.g. 'vite.config.ts', 'tailwind.config.js', '.eslintrc.js'. These are
    left out of source-file counts; 'setup.py' and 'manage.py' are too,
    since they are generated boilerplate (setup.py still counts as a
    Python marker file).
    """
    name = posixpath.basename(path).lower()
    return ".config." in name or name.startswith(".") or name in ("setup.py", "manage.py")


def is_ignored(path: str) -> bool:
    """True if the path sits inside a third-party or generated folder."""
    return any(part in IGNORED_DIRS for part in path.split("/")[:-1])


def manifest_paths(paths: list[str], limit: int) -> list[str]:
    """
    The dependency/config files worth fetching, shallowest first (the
    project's own top-level files before deeply nested examples), capped
    at `limit` to bound the number of GitHub API calls per repository.
    """
    candidates = [
        p for p in paths
        if posixpath.basename(p) in MANIFEST_FILES and not is_ignored(p)
    ]
    candidates.sort(key=lambda p: (p.count("/"), p))
    return candidates[:limit]


def _normalize(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def parse_dependencies(path: str, content: str) -> set[str]:
    """
    Package names declared in a dependency file, lower-cased, with "_"
    folded to "-" (so "Flask_PyMongo" and "flask-pymongo" match).
    Unparseable files simply yield no names.
    """
    filename = posixpath.basename(path)
    names: set[str] = set()

    if filename == "package.json":
        try:
            data = json.loads(content)
        except ValueError:
            return names
        if isinstance(data, dict):
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                deps = data.get(section)
                if isinstance(deps, dict):
                    names.update(_normalize(n) for n in deps)

    elif filename == "requirements.txt":
        for line in content.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
            if match:
                names.add(_normalize(match.group(0)))

    elif filename in ("pyproject.toml", "Pipfile", "setup.py"):
        # Requirement strings appear quoted ("fastapi>=0.110") or as TOML
        # keys (fastapi = "^0.110"); match a package name at either start.
        for match in re.finditer(
            r"""(?m)(?:["']|^\s*)([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:[<>=!~^;"']|=\s)""",
            content,
        ):
            names.add(_normalize(match.group(1)))

    elif filename == "pom.xml":
        names.update(_normalize(m) for m in re.findall(r"<artifactId>\s*([^<\s]+)\s*</artifactId>", content))

    elif filename in ("build.gradle", "build.gradle.kts"):
        # 'group:artifact:version' coordinates -> artifact
        for match in re.finditer(r"""["']([\w.-]+):([\w.-]+)(?::[^"']*)?["']""", content):
            names.add(_normalize(match.group(2)))

    return names


def parse_compose_images(content: str) -> set[str]:
    """Image names in a docker-compose file, without registry or tag: 'library/mysql:8' -> 'mysql'."""
    images = set()
    for match in re.finditer(r"""(?m)^\s*image:\s*["']?([^\s"'#]+)""", content):
        image = match.group(1).split("@", 1)[0]
        name = image.rsplit("/", 1)[-1].split(":", 1)[0]
        images.add(name.lower())
    return images


def detect_technologies(paths: list[str], manifests: dict[str, str]) -> dict[str, list[str]]:
    """
    Apply TECH_RULES to one repository.

    `paths` is every file path in the repo; `manifests` maps the path of
    each fetched dependency/config file to its text. Returns technology ->
    human-readable evidence strings; technologies with no evidence are
    omitted.
    """
    own_paths = [p for p in paths if not is_ignored(p)]
    by_name: dict[str, list[str]] = {}
    for p in own_paths:
        by_name.setdefault(posixpath.basename(p), []).append(p)

    deps_by_file = {path: parse_dependencies(path, text) for path, text in manifests.items()}
    images_by_file = {
        path: parse_compose_images(text)
        for path, text in manifests.items()
        if posixpath.basename(path) in COMPOSE_FILES
    }

    evidence: dict[str, list[str]] = {}
    for tech, rule in TECH_RULES.items():
        found: list[str] = []

        for marker in rule.get("marker_files", []):
            for p in sorted(by_name.get(marker, []), key=lambda x: (x.count("/"), x))[:1]:
                found.append(f"{marker} found at {p}")

        extensions = tuple(rule.get("extensions", []))
        if extensions:
            count = sum(
                1 for p in own_paths
                if p.lower().endswith(extensions) and not is_tooling_config(p)
            )
            if count >= rule.get("min_files", MIN_SOURCE_FILES):
                if "file_label" in rule:
                    plural = "" if count == 1 else "s"
                    found.append(f"{count} {rule['file_label']}{plural}")
                else:
                    label = "/".join(extensions[:2]) if len(extensions) > 1 else extensions[0]
                    found.append(f"{count} {label} source files")

        if rule.get("any_repo") and own_paths:
            found.append("public repository on GitHub")

        wanted = {_normalize(d) for d in rule.get("dependencies", [])}
        for path in sorted(deps_by_file):
            matched = sorted(wanted & deps_by_file[path])
            if matched:
                found.append(f"{', '.join(repr(m) for m in matched)} listed in {path}")

        wanted_images = set(rule.get("images", []))
        for path in sorted(images_by_file):
            matched = sorted(wanted_images & images_by_file[path])
            if matched:
                found.append(f"{', '.join(matched)} image in {path}")

        if found:
            evidence[tech] = found

    return evidence
