"""
Unit tests for the technology detection rules in app/services/tech_rules.py.

Pure functions only - repositories are described as a list of file paths
plus the text of their dependency files, the same inputs fingerprinting.py
fetches from GitHub.
"""
import json

from app.services.tech_rules import (
    detect_technologies,
    manifest_paths,
    parse_compose_images,
    parse_dependencies,
)


def _package_json(dependencies=None, dev_dependencies=None) -> str:
    return json.dumps(
        {"name": "app", "dependencies": dependencies or {}, "devDependencies": dev_dependencies or {}}
    )


# --- whole-repo scanning -------------------------------------------------


def test_files_in_subfolders_are_found():
    # A monorepo: nothing useful at the root, everything one level down.
    paths = ["README.md", "backend/Dockerfile", "frontend/package.json", "frontend/src/App.jsx"]
    manifests = {"frontend/package.json": _package_json({"react": "^18.3.1"})}

    detected = detect_technologies(paths, manifests)

    assert detected["Docker"] == ["Dockerfile found at backend/Dockerfile"]
    assert detected["React"] == ["'react' listed in frontend/package.json"]


def test_third_party_folders_are_ignored():
    paths = [f"node_modules/lib/file{i}.js" for i in range(20)] + ["venv/lib/site.py"] * 5
    assert detect_technologies(paths, {}) == {}


def test_manifest_paths_prefers_shallow_files_and_respects_the_limit():
    paths = [
        "examples/demo/package.json",
        "package.json",
        "backend/requirements.txt",
        "node_modules/react/package.json",
        "docker-compose.yml",
        "src/main.py",
    ]
    assert manifest_paths(paths, limit=3) == [
        "docker-compose.yml",
        "package.json",
        "backend/requirements.txt",
    ]


# --- languages -----------------------------------------------------------


def test_language_needs_a_minimum_number_of_source_files():
    one_script = detect_technologies(["tools/convert.py"], {})
    real_project = detect_technologies(["a.py", "pkg/b.py", "pkg/c.py"], {})

    assert "Python" not in one_script
    assert real_project["Python"] == ["3 .py/.ipynb source files"]


def test_java_and_cpp_detected_from_build_files_and_sources():
    paths = ["api/pom.xml", "CMakeLists.txt", "src/main.cpp", "src/graph.cpp", "src/graph.hpp"]

    detected = detect_technologies(paths, {})

    assert detected["Java"] == ["pom.xml found at api/pom.xml"]
    assert "CMakeLists.txt found at CMakeLists.txt" in detected["C++"]
    assert "3 .cpp/.cc source files" in detected["C++"]


def test_javascript_detected_from_sources():
    detected = detect_technologies(["index.js", "src/a.js", "src/b.jsx"], {})
    assert detected["JavaScript"] == ["3 .js/.jsx source files"]


# --- frameworks and databases from dependency files ----------------------


def test_python_frameworks_and_databases_from_requirements():
    requirements = "Flask==3.0.0\nflask_pymongo>=2.3  # comment\nPyMySQL\n-r dev.txt\n"

    detected = detect_technologies(["requirements.txt", "app.py"], {"requirements.txt": requirements})

    assert detected["Flask"] == ["'flask' listed in requirements.txt"]
    assert detected["MongoDB"] == ["'flask-pymongo' listed in requirements.txt"]
    assert detected["MySQL"] == ["'pymysql' listed in requirements.txt"]
    assert "requirements.txt found at requirements.txt" in detected["Python"]


def test_node_backend_from_package_json():
    manifests = {"server/package.json": _package_json({"express": "^4", "mongoose": "^8", "pg": "^8"})}

    detected = detect_technologies(["server/package.json"], manifests)

    assert detected["Express"] == ["'express' listed in server/package.json"]
    assert detected["Node.js"] == ["'express', 'mongoose' listed in server/package.json"]
    assert detected["MongoDB"] == ["'mongoose' listed in server/package.json"]
    assert detected["PostgreSQL"] == ["'pg' listed in server/package.json"]


def test_frontend_only_package_json_is_not_node_backend_evidence():
    manifests = {"package.json": _package_json({"react": "^18"}, {"vite": "^5"})}

    detected = detect_technologies(["package.json"], manifests)

    assert "React" in detected
    assert "Node.js" not in detected


def test_word_inside_another_package_name_does_not_match():
    # The old keyword search matched "flask" inside "flask-cors"-style text
    # and "react" inside "react-icons"; names must now match exactly.
    manifests = {"package.json": _package_json({"react-icons": "^5", "preact": "^10"})}

    assert "React" not in detect_technologies(["package.json"], manifests)


def test_databases_from_docker_compose_images():
    compose = """
services:
  db:
    image: mysql:8.0
  cache:
    image: "docker.io/library/mongo:7"
  pg:
    image: postgis/postgis:16-3.4
"""
    detected = detect_technologies(["docker-compose.yml"], {"docker-compose.yml": compose})

    assert detected["MySQL"] == ["mysql image in docker-compose.yml"]
    assert detected["MongoDB"] == ["mongo image in docker-compose.yml"]
    assert detected["PostgreSQL"] == ["postgis image in docker-compose.yml"]
    assert detected["Docker"] == ["docker-compose.yml found at docker-compose.yml"]


def test_java_dependencies_from_pom_and_gradle():
    pom = "<dependency><artifactId>mysql-connector-j</artifactId></dependency>"
    gradle = "implementation 'org.springframework.boot:spring-boot-starter-data-mongodb:3.2.0'"

    detected = detect_technologies(
        ["pom.xml", "app/build.gradle"], {"pom.xml": pom, "app/build.gradle": gradle}
    )

    assert detected["MySQL"] == ["'mysql-connector-j' listed in pom.xml"]
    assert detected["MongoDB"] == ["'spring-boot-starter-data-mongodb' listed in app/build.gradle"]


# --- parsers -------------------------------------------------------------


def test_parse_pyproject_dependencies():
    pyproject = """
[project]
dependencies = ["fastapi>=0.110", "SQLAlchemy[asyncio] ~= 2.0", "psycopg2-binary"]

[tool.poetry.dependencies]
django = "^5.0"
"""
    names = parse_dependencies("pyproject.toml", pyproject)

    assert {"fastapi", "sqlalchemy", "psycopg2-binary", "django"} <= names


def test_parse_dependencies_tolerates_broken_files():
    assert parse_dependencies("package.json", "{ not json") == set()
    assert parse_dependencies("package.json", "[]") == set()
    assert parse_dependencies("README.md", "flask") == set()


def test_parse_compose_images_strips_registry_and_tag():
    content = "image: ghcr.io/acme/postgres:16@sha256:abc\nimage: 'redis'"
    assert parse_compose_images(content) == {"postgres", "redis"}


def test_tool_config_files_are_not_counted_as_source_code():
    paths = ["eslint.config.js", "tailwind.config.js", "postcss.config.js", ".eslintrc.js", "src/main.ts"]
    assert "JavaScript" not in detect_technologies(paths, {})
