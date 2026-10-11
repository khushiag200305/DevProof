"""
Tests for the skill catalog (app/skills_catalog.json) and resume skill
extraction (app/skills_dictionary.py). Pure - no database or network.
"""
import json

import pytest

from app.skills_dictionary import (
    CATALOG_PATH,
    CATEGORIES,
    SKILLS,
    _load_catalog,
    extract_skill_names,
    is_checkable,
)

RESUME_SKILLS_SECTION = """TECHNICAL SKILLS
Programming Languages:  Python, C, C++, Java
Cloud Computing & AWS:  EC2, S3, Lambda, IAM, VPC, Cloud Computing Fundamentals
AI & Machine Learning: Machine Learning Fundamentals, PCA, K-Means Clustering, Data Analysis, Prompt Engineering
Database: MySQL , SQL , CRUD Operations, Database Design, Normalization
Data & Analytics: Microsoft Excel, Tableau, Pandas, Data Cleaning, Data Visualization, Exploratory Data Analysis (EDA)
Core Concepts: Data Structures & Algorithms, Object-Oriented Programming, Computer Networks, Operating System, DBMS
Business & Productivity Tools: Microsoft Office (Excel, PowerPoint, Word), Git, GitHub, VS Code
"""


# --- the catalog file itself ---------------------------------------------


def test_catalog_loads_and_every_skill_is_well_formed():
    assert len(SKILLS) >= 40
    for name, skill in SKILLS.items():
        assert skill["category"] in CATEGORIES, name
        if skill["check"] == "github":
            assert skill["rules"], name
        else:
            assert skill["reason"] and skill["question"], name


@pytest.mark.parametrize(
    "broken, message",
    [
        ({"name": "X", "category": "Nope", "aliases": ["x"], "check": "manual", "reason": "r"}, "unknown category"),
        ({"name": "X", "category": "Tools", "aliases": ["x"], "check": "maybe"}, "check must be"),
        ({"name": "X", "category": "Tools", "aliases": ["x"], "check": "github", "rules": {"files": []}}, "unknown rule keys"),
        ({"name": "X", "category": "Tools", "aliases": ["x"], "check": "manual"}, "needs a reason"),
        ({"name": "X", "category": "Tools", "aliases": ["python"], "check": "manual", "reason": "r"}, "used by both"),
    ],
)
def test_catalog_mistakes_fail_loudly(tmp_path, broken, message):
    data = json.loads(CATALOG_PATH.read_text())
    data["skills"].append(broken)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))

    with pytest.raises(ValueError, match=message):
        _load_catalog(path)


# --- extraction from resume text -----------------------------------------


def test_every_skill_in_a_real_skills_section_is_extracted():
    assert extract_skill_names(RESUME_SKILLS_SECTION) == sorted([
        "Python", "C", "C++", "Java",
        "AWS", "AWS EC2", "AWS S3", "AWS Lambda", "AWS IAM", "AWS VPC", "Cloud Computing",
        "Machine Learning", "PCA", "K-Means Clustering", "Data Analysis", "Prompt Engineering",
        "MySQL", "SQL", "CRUD Operations", "Database Design", "Normalization",
        "Excel", "Tableau", "Pandas", "Data Cleaning", "Data Visualization", "Exploratory Data Analysis",
        "Data Structures & Algorithms", "Object-Oriented Programming", "Computer Networks",
        "Operating Systems", "DBMS",
        "Microsoft Office", "Git & GitHub", "VS Code",
    ])


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Languages: C, Python", ["C", "Python"]),
        ("C/C++ programmer", ["C", "C++"]),
        ("Grade: C", []),
        ("Completed Section C of the course", []),
        ("Word count: 500", []),
        ("I am a student", []),
        ("I excel at teamwork", []),
        ("Microsoft Office (Excel, PowerPoint, Word)", ["Excel", "Microsoft Office"]),
        ("Python,Cobol", ["Python"]),
        ("Used a lambda function in Python", ["Python"]),
        ("NoSQL and PostgreSQL", ["PostgreSQL"]),
    ],
)
def test_short_words_only_count_as_list_items(text, expected):
    assert extract_skill_names(text) == sorted(expected)


def test_contact_lines_do_not_count_as_skill_claims():
    text = "aditi@example.com | LinkedIn | GitHub | +91 98765 43210\nGitHub: github.com/aditi"
    assert extract_skill_names(text) == []


def test_concept_and_offline_skills_are_marked_not_checkable():
    for name in ["Object-Oriented Programming", "Excel", "AWS IAM", "Normalization", "PCA"]:
        assert not is_checkable(name)
    for name in ["Python", "C", "SQL", "Machine Learning", "Tableau", "Git & GitHub"]:
        assert is_checkable(name)
    assert is_checkable("SomethingNotInCatalog")
