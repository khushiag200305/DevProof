"""
Unit tests for the resume intelligence extraction functions
(app/services/resume_parser.py). These operate on plain extracted text,
not PDF bytes or the DB, so they don't require a live PostgreSQL
instance to run.
"""
from app.services.resume_parser import (
    extract_github_url,
    extract_github_username,
    extract_name,
    extract_projects,
    extract_skills,
)

SAMPLE_RESUME_TEXT = """Aditi Sharma
aditi.sharma@example.com | github.com/aditisharma-dev | +91 98765 43210

SUMMARY
Full-stack developer with experience building web applications.

SKILLS
Python, JavaScript, React, FastAPI, Docker, PostgreSQL

PROJECTS
DevProof Dashboard - a React and FastAPI app for candidate evidence review
Inventory Tracker - Flask and MySQL based inventory management system

EXPERIENCE
Software Engineering Intern, Example Corp
"""


def test_extract_name():
    name = extract_name(SAMPLE_RESUME_TEXT)
    assert name == "Aditi Sharma"


def test_extract_name_no_person_found():
    assert extract_name("") is None


def test_extract_name_does_not_misdetect_a_skill_as_a_name():
    # Regression: on short, sparse header text spaCy's small model can
    # mistag an all-caps technology word as a PERSON entity (observed:
    # "Docker" tagged PERSON given just a two-line header). The name
    # should never come back as a known skill keyword.
    text = "Test Person\ngithub.com/testuser\n\nSKILLS\nPython, Docker, React"
    assert extract_name(text) == "Test Person"


def test_extract_skills():
    # SAMPLE_RESUME_TEXT mentions skills both in the SKILLS section and
    # inside project descriptions (Flask, MySQL) - extraction scans the
    # whole document, so both should be picked up.
    skills = extract_skills(SAMPLE_RESUME_TEXT)
    assert skills == sorted(
        ["Python", "JavaScript", "React", "FastAPI", "Docker", "PostgreSQL", "Flask", "MySQL"]
    )


def test_extract_skills_normalizes_variants():
    text = "Experience with ReactJS, Node.js, and Postgres."
    skills = extract_skills(text)
    assert "React" in skills
    assert "Node.js" in skills
    assert "PostgreSQL" in skills


def test_extract_github_url():
    url = extract_github_url(SAMPLE_RESUME_TEXT)
    assert url is not None
    assert "github.com/aditisharma-dev" in url


def test_extract_github_url_missing():
    assert extract_github_url("No GitHub link in this resume.") is None


def test_extract_github_username():
    assert extract_github_username("github.com/khushiag200305") == "khushiag200305"
    assert (
        extract_github_username("https://github.com/khushiag200305/DevProof")
        == "khushiag200305"
    )


def test_extract_projects():
    projects = extract_projects(SAMPLE_RESUME_TEXT)
    assert any("DevProof Dashboard" in p for p in projects)
    assert any("Inventory Tracker" in p for p in projects)
