"""Tests for the Projects-section parser in app/services/resume_projects.py."""
from app.services.resume_projects import (
    looks_like_tech_list,
    looks_like_title,
    parse_projects,
    parse_title,
)

# Layout of Khushi's resume: "Title | Tech" lines with bullet points,
# a title whose tech stack sits on the next line, and wrapped bullets.
PIPE_RESUME = """Khushi Agarwal
PROJECTS
Energy Consumption Analysis in Smart Buildings | Python Jan 2025 – Apr 2025
• Analyzed large-scale building energy consumption and weather datasets
to identify usage patterns.
• Performed data preprocessing, feature engineering, and exploratory data
analysis (EDA).
• Applied PCA for dimensionality reduction and feature optimization.
• Implemented K-Means clustering to group buildings based on consumption.
Credit Card Fraud Detection & Transaction Analytics |
Python, Scikit-learn, MySQL
• Built a fraud detection system using machine learning models.
• Designed a MySQL database and implemented SQL queries.
Emergency Management Database System | MySQL
• Designed a normalized relational database for emergency incident management.
• Implemented CRUD operations and database constraints.
EDUCATION
Thapar Institute of Engineering and Technology
"""

# Same resume where PDF extraction dropped the bullet characters.
NO_BULLETS_RESUME = """PROJECTS
Energy Consumption Analysis in Smart Buildings | Python
Analyzed large-scale building energy consumption and weather datasets.
Applied PCA for dimensionality reduction and feature optimization.
Credit Card Fraud Detection & Transaction Analytics | Python, MySQL
Built a fraud detection system using machine learning.
CERTIFICATIONS
AWS Cloud Practitioner
"""

# "Name - description" on one line, no bullets (the original test sample).
INLINE_RESUME = """PROJECTS
DevProof Dashboard - a React and FastAPI app for candidate evidence review
Inventory Tracker - Flask and MySQL based inventory management system

EXPERIENCE
Software Engineering Intern, Example Corp
"""

# Title with tech in brackets, dates on their own line, dash bullets.
BRACKET_RESUME = """Personal Projects:
Chat App (React, Node.js, MongoDB)
Mar 2024 - May 2024
- Built real-time messaging with WebSockets.
- Deployed on Render with a CI pipeline.
URL Shortener | Go | github.com/someone/shortener
- Wrote a REST API that turns long links into short codes.
Skills
Python, Go
"""


def _names(projects):
    return [p["name"] for p in projects]


def test_pipe_titles_become_separate_projects():
    projects = parse_projects(PIPE_RESUME)
    assert _names(projects) == [
        "Energy Consumption Analysis in Smart Buildings",
        "Credit Card Fraud Detection & Transaction Analytics",
        "Emergency Management Database System",
    ]


def test_tech_stack_and_dates_come_from_the_title_line():
    energy = parse_projects(PIPE_RESUME)[0]
    assert energy["tech_stack"] == ["Python"]
    assert energy["period"] == "Jan 2025 – Apr 2025"


def test_tech_stack_on_the_line_after_a_trailing_pipe():
    fraud = parse_projects(PIPE_RESUME)[1]
    assert fraud["tech_stack"] == ["Python", "Scikit-learn", "MySQL"]
    assert fraud["bullets"] == [
        "Built a fraud detection system using machine learning models.",
        "Designed a MySQL database and implemented SQL queries.",
    ]


def test_wrapped_bullet_lines_are_joined_not_split():
    energy = parse_projects(PIPE_RESUME)[0]
    assert energy["bullets"] == [
        "Analyzed large-scale building energy consumption and weather datasets to identify usage patterns.",
        "Performed data preprocessing, feature engineering, and exploratory data analysis (EDA).",
        "Applied PCA for dimensionality reduction and feature optimization.",
        "Implemented K-Means clustering to group buildings based on consumption.",
    ]


def test_section_ends_at_the_next_header():
    projects = parse_projects(PIPE_RESUME)
    assert not any("Thapar" in p["name"] for p in projects)
    assert "Implemented CRUD operations and database constraints." in projects[-1]["bullets"]


def test_resume_without_bullet_characters():
    projects = parse_projects(NO_BULLETS_RESUME)
    assert _names(projects) == [
        "Energy Consumption Analysis in Smart Buildings",
        "Credit Card Fraud Detection & Transaction Analytics",
    ]
    assert projects[0]["bullets"] == [
        "Analyzed large-scale building energy consumption and weather datasets.",
        "Applied PCA for dimensionality reduction and feature optimization.",
    ]
    assert projects[1]["tech_stack"] == ["Python", "MySQL"]


def test_name_dash_description_lines():
    projects = parse_projects(INLINE_RESUME)
    assert _names(projects) == ["DevProof Dashboard", "Inventory Tracker"]
    assert projects[0]["bullets"] == ["a React and FastAPI app for candidate evidence review"]


def test_bracket_tech_dates_line_and_links():
    projects = parse_projects(BRACKET_RESUME)
    assert _names(projects) == ["Chat App", "URL Shortener"]
    chat, short = projects
    assert chat["tech_stack"] == ["React", "Node.js", "MongoDB"]
    assert chat["period"] == "Mar 2024 - May 2024"
    assert chat["bullets"] == [
        "Built real-time messaging with WebSockets.",
        "Deployed on Render with a CI pipeline.",
    ]
    assert short["tech_stack"] == ["Go"]
    assert short["bullets"] == ["Wrote a REST API that turns long links into short codes."]


def test_no_projects_section():
    assert parse_projects("SKILLS\nPython\nEDUCATION\nBTech") == []


def test_title_and_tech_helpers():
    assert looks_like_title("Smart Building Energy Analysis")
    assert looks_like_title("Fraud Detection | Python")
    assert not looks_like_title("Built a fraud detection system using machine learning")
    assert not looks_like_title("Designed the database schema.")
    assert looks_like_tech_list("Python, Scikit-learn, MySQL")
    assert not looks_like_tech_list("Built a system, then deployed it")
    assert parse_title("Shop API | FastAPI, Docker | Live Demo")["tech_stack"] == ["FastAPI", "Docker"]
