"""
Demo data: 20 fictional students so the recruiter features (candidate
list, talent search, compare, shortlists) have something to show in a
demo. Clearly marked and removable:

    python -m app.demo_data add      # add the demo students (skips if already there)
    python -m app.demo_data remove   # delete only the demo students
    python -m app.demo_data reset    # remove, then add again

Every demo student has an email ending in @demo.devproof, "(Demo)" after
their name, and no GitHub username (so "Re-run analysis" never calls the
GitHub API for them). Their repository links point to example.com, a
domain reserved for examples. Real accounts and uploads are never touched.
"""
import json
import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from . import models
from .database import Base, SessionLocal, engine, ensure_columns
from .services.scoring import GOOD_THRESHOLD, STRONG_THRESHOLD, default_interview_question
from .skills_dictionary import NOT_CHECKABLE, is_checkable

DEMO_DOMAIN = "demo.devproof"
REPO_BASE = "https://example.com/devproof-demo"

# Student profiles: name, focus, skills with a rough strength (0-100,
# None for concept skills), and projects (repo name, title, tech, points).
PROFILES = [
    ("Aarav Mehta", "Backend", {"Python": 100, "FastAPI": 95, "PostgreSQL": 80, "Docker": 75, "Git & GitHub": 100, "SQL": 70, "Object-Oriented Programming": None},
     [("campus-events-api", "Campus Events API", ["Python", "FastAPI", "PostgreSQL", "Docker"], ["Built a REST API for college event registrations used by 3 clubs.", "Containerised the API and database with Docker Compose."]),
      ("expense-splitter", "Expense Splitter", ["Python", "SQL"], ["Wrote a command-line app to split shared expenses among hostel roommates."])]),
    ("Diya Sharma", "Frontend", {"JavaScript": 100, "React": 95, "Node.js": 60, "Express": 55, "Git & GitHub": 100, "MongoDB": 45, "Data Structures & Algorithms": None},
     [("study-planner", "Study Planner", ["React", "JavaScript"], ["Built a React study planner with drag-and-drop weekly timetables.", "Added offline support with local storage."]),
      ("notes-sync", "Notes Sync", ["Node.js", "Express", "MongoDB"], ["Created an Express API to sync notes between devices."])]),
    ("Kabir Singh", "Data science", {"Python": 100, "Pandas": 90, "NumPy": 85, "Machine Learning": 80, "Data Visualization": 70, "Exploratory Data Analysis": 75, "SQL": 35, "PCA": None},
     [("crop-yield-prediction", "Crop Yield Prediction", ["Python", "Machine Learning", "Pandas"], ["Trained regression models on 10 years of Punjab crop data.", "Compared random forest and gradient boosting on yield accuracy."]),
      ("covid-dashboard", "COVID Data Dashboard", ["Python", "Data Visualization"], ["Visualised district-level case trends with interactive charts."])]),
    ("Ananya Iyer", "Full-stack", {"JavaScript": 95, "React": 85, "Node.js": 80, "Express": 75, "PostgreSQL": 65, "Docker": 30, "Git & GitHub": 100, "DBMS": None},
     [("hostel-complaints", "Hostel Complaint Tracker", ["React", "Node.js", "Express", "PostgreSQL"], ["Built a full-stack app for students to raise and track hostel complaints.", "Designed role-based views for wardens and students."]),
      ("portfolio-site", "Portfolio Website", ["React", "JavaScript"], ["Built a personal portfolio site with a blog section."])]),
    ("Rohan Gupta", "Java", {"Java": 100, "Object-Oriented Programming": None, "Data Structures & Algorithms": None, "MySQL": 70, "SQL": 65, "Git & GitHub": 90},
     [("library-management", "Library Management System", ["Java", "MySQL"], ["Built a Java desktop app for issuing and returning library books.", "Normalised the MySQL schema to third normal form."]),
      ("dsa-practice", "DSA Practice", ["Java"], ["Solved 300+ data structure and algorithm problems with tests."])]),
    ("Ishita Verma", "ML", {"Python": 95, "Machine Learning": 90, "Pandas": 80, "NumPy": 80, "Prompt Engineering": 60, "Flask": 55, "K-Means Clustering": None, "Docker": 20},
     [("resume-screening-model", "Resume Screening Model", ["Python", "Machine Learning", "Flask"], ["Trained a text classifier to tag resumes by job role.", "Served predictions through a small Flask API."]),
      ("customer-segments", "Customer Segmentation", ["Python", "Pandas"], ["Grouped online shoppers into segments using clustering."])]),
    ("Arjun Nair", "Cloud", {"Python": 85, "AWS": 80, "AWS Lambda": 75, "AWS S3": 70, "Docker": 85, "Git & GitHub": 95, "Cloud Computing": None, "AWS IAM": None},
     [("serverless-image-resizer", "Serverless Image Resizer", ["Python", "AWS Lambda", "AWS S3"], ["Built an AWS Lambda function that resizes images uploaded to S3.", "Deployed it with infrastructure as code."]),
      ("dockerised-blog", "Dockerised Blog", ["Docker", "Python"], ["Packaged a blog app and its database with Docker Compose."])]),
    ("Sneha Kapoor", "Frontend", {"JavaScript": 90, "React": 80, "Git & GitHub": 85, "Node.js": 35, "Data Visualization": 50, "Microsoft Office": None},
     [("weather-now", "Weather Now", ["React", "JavaScript"], ["Built a weather app using a public API with 5-day forecasts."]),
      ("quiz-game", "Quiz Game", ["JavaScript"], ["Made a timed quiz game with a leaderboard."])]),
    ("Vikram Rao", "Systems", {"C": 100, "C++": 95, "Data Structures & Algorithms": None, "Operating Systems": None, "Computer Networks": None, "Git & GitHub": 80, "Python": 40},
     [("mini-shell", "Mini Unix Shell", ["C"], ["Wrote a Unix shell in C with pipes, redirection and background jobs."]),
      ("chat-server", "Multi-client Chat Server", ["C++"], ["Built a TCP chat server handling 50 concurrent clients with threads."])]),
    ("Priya Nair", "Data analyst", {"SQL": 90, "MySQL": 80, "Tableau": 75, "Excel": None, "Pandas": 60, "Data Analysis": 70, "Data Cleaning": 65, "Python": 55},
     [("sales-dashboard", "Sales Analytics Dashboard", ["SQL", "Tableau"], ["Built a Tableau dashboard tracking monthly sales by region.", "Wrote SQL views to clean and join raw sales data."]),
      ("survey-analysis", "Student Survey Analysis", ["Python", "Pandas", "Data Analysis"], ["Analysed 1,200 survey responses on campus facilities."])]),
    ("Aditya Kulkarni", "Backend", {"Python": 90, "Django": 85, "PostgreSQL": 75, "Docker": 50, "Git & GitHub": 90, "SQL": 60, "Database Design": None},
     [("canteen-ordering", "Canteen Ordering System", ["Python", "Django", "PostgreSQL"], ["Built a Django app for pre-ordering canteen food with order queues.", "Added an admin dashboard for daily sales."]),
      ("url-shortener", "URL Shortener", ["Python", "Docker"], ["Built a URL shortener with click analytics."])]),
    ("Meera Joshi", "Full-stack", {"JavaScript": 90, "React": 90, "Node.js": 85, "MongoDB": 80, "Express": 80, "Docker": 55, "Git & GitHub": 100},
     [("ride-share-campus", "Campus Ride Share", ["React", "Node.js", "MongoDB", "Express"], ["Built an app for students to share cab rides to the railway station.", "Added real-time seat updates with websockets."]),
      ("recipe-finder", "Recipe Finder", ["React"], ["Built a recipe search app with filters for dietary needs."])]),
    ("Siddharth Malhotra", "Data science", {"Python": 85, "Pandas": 80, "NumPy": 75, "Machine Learning": 60, "Data Visualization": 80, "Tableau": 40, "Exploratory Data Analysis": 70},
     [("ipl-analysis", "IPL Match Analysis", ["Python", "Pandas", "Data Visualization"], ["Analysed 15 seasons of IPL data to find winning factors.", "Built charts on toss decisions and venue effects."]),
      ("house-prices", "House Price Prediction", ["Python", "Machine Learning"], ["Predicted house prices with linear and tree-based models."])]),
    ("Tanvi Bhatt", "Java", {"Java": 90, "MySQL": 60, "Object-Oriented Programming": None, "Git & GitHub": 75, "JavaScript": 45, "Data Structures & Algorithms": None},
     [("bank-simulator", "Bank Account Simulator", ["Java", "MySQL"], ["Built a Java banking simulator with transactions and statements."])]),
    ("Nikhil Reddy", "Cloud", {"Docker": 90, "AWS": 70, "AWS EC2": None, "Python": 75, "Git & GitHub": 90, "Node.js": 50, "Cloud Computing": None},
     [("ci-cd-demo", "CI/CD Pipeline Demo", ["Docker", "Python"], ["Set up a CI pipeline that tests and builds a Docker image on every push."]),
      ("status-page", "Service Status Page", ["Node.js", "AWS"], ["Built a status page that checks uptime of college websites."])]),
    ("Kavya Menon", "ML", {"Python": 90, "Machine Learning": 85, "Prompt Engineering": 80, "Pandas": 65, "FastAPI": 60, "NumPy": 70},
     [("study-buddy-llm", "Study Buddy Chatbot", ["Python", "Prompt Engineering", "FastAPI"], ["Built a chatbot that answers questions from course notes.", "Wrapped it in a FastAPI service with rate limiting."]),
      ("emotion-detector", "Emotion Detector", ["Python", "Machine Learning"], ["Classified emotions in tweets with a fine-tuned model."])]),
    ("Harsh Agarwal", "Backend", {"Node.js": 85, "Express": 85, "MongoDB": 75, "JavaScript": 90, "Docker": 40, "Git & GitHub": 85, "PostgreSQL": 25},
     [("attendance-api", "Attendance API", ["Node.js", "Express", "MongoDB"], ["Built an API for QR-code based class attendance."])]),
    ("Riya Saxena", "Data analyst", {"Excel": None, "SQL": 75, "Tableau": 80, "Data Analysis": 75, "Data Cleaning": 70, "Python": 45, "Microsoft Office": None},
     [("placement-insights", "Placement Insights", ["SQL", "Tableau", "Data Analysis"], ["Built dashboards on five years of campus placement data."])]),
    ("Yash Thakur", "Full-stack", {"Python": 80, "Flask": 80, "JavaScript": 70, "React": 60, "MySQL": 70, "Git & GitHub": 80, "CRUD Operations": None},
     [("lost-and-found", "Lost and Found Portal", ["Python", "Flask", "MySQL"], ["Built a Flask portal for reporting lost items on campus."]),
      ("todo-react", "Todo App", ["React"], ["Built a todo app with filters and due dates."])]),
    ("Zara Khan", "Frontend", {"JavaScript": 95, "React": 90, "Data Visualization": 75, "Node.js": 55, "Git & GitHub": 95, "Docker": 15},
     [("air-quality-viz", "Air Quality Visualiser", ["React", "Data Visualization"], ["Visualised live air quality readings across Indian cities.", "Built accessible charts with keyboard navigation."]),
      ("design-system", "Mini Design System", ["React", "JavaScript"], ["Built reusable React components with documentation."])]),
]


def _status(score: int) -> str:
    if score >= STRONG_THRESHOLD:
        return "Strong Evidence"
    if score >= GOOD_THRESHOLD:
        return "Good Evidence"
    return "Needs Verification"


def _slug(name: str) -> str:
    return name.lower().replace(" ", ".")


def _skill(db: Session, name: str) -> models.Skill:
    skill = db.query(models.Skill).filter_by(skill_name=name).first()
    if skill is None:
        skill = models.Skill(skill_name=name)
        db.add(skill)
        db.flush()
    return skill


def _demo_users(db: Session) -> list[models.User]:
    return db.query(models.User).filter(models.User.email.like(f"%@{DEMO_DOMAIN}")).all()


def add(db: Session) -> int:
    """Add the demo students. Returns how many were added (0 if already there)."""
    if _demo_users(db):
        return 0
    rng = random.Random(2026)
    now = datetime.now(timezone.utc)

    for i, (name, focus, skills, projects) in enumerate(PROFILES):
        slug = _slug(name)
        user = models.User(
            google_sub=f"demo-{slug}", email=f"{slug}@{DEMO_DOMAIN}", name=f"{name} (Demo)", role="student",
        )
        db.add(user)
        db.flush()
        candidate = models.Candidate(
            user_id=user.user_id, name=f"{name} (Demo)", email=user.email, github_username=None,
            resume_path=None, created_at=now - timedelta(days=2 + i * 2, hours=rng.randint(0, 20)),
        )
        db.add(candidate)
        db.flush()
        user.visible_candidate_id = candidate.candidate_id

        # Repositories, one per project, plus details for portfolio/resume lines.
        repos: dict[str, models.Repository] = {}
        for repo_name, title, tech, points in projects:
            pushed = now - timedelta(days=rng.randint(3, 200))
            repo = models.Repository(
                candidate_id=candidate.candidate_id, repo_name=repo_name, repo_url=f"{REPO_BASE}/{repo_name}",
                is_fork=False, commit_count=rng.randint(8, 140), last_updated=pushed,
            )
            db.add(repo)
            db.flush()
            db.add(models.RepositoryDetail(
                repo_id=repo.repo_id, description=points[0], language=tech[0], topics=",".join(t.lower() for t in tech),
                stars=rng.randint(0, 12), created_at=pushed - timedelta(days=rng.randint(30, 150)), pushed_at=pushed,
                technologies=json.dumps(tech), has_tests=rng.random() < 0.5, has_ci=rng.random() < 0.35,
                has_readme=True, has_docs=rng.random() < 0.3, has_frontend_and_backend=len(tech) >= 3,
                has_compose="Docker" in tech, source_files=rng.randint(6, 60),
            ))
            repos[repo_name] = repo
            db.add(models.Project(
                candidate_id=candidate.candidate_id, project_name=title, description="\n".join(points),
                tech_stack=", ".join(tech),
                period=f"{(pushed - timedelta(days=90)).strftime('%b %Y')} - {pushed.strftime('%b %Y')}",
            ))

        # Skills with scores and the evidence behind them.
        for skill_name, strength in skills.items():
            skill = _skill(db, skill_name)
            if not is_checkable(skill_name) or strength is None:
                db.add(models.CandidateSkill(
                    candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status=NOT_CHECKABLE, score=None,
                ))
                continue
            score = max(0, min(100, strength + rng.choice([-5, 0, 0, 5]))) // 5 * 5
            db.add(models.CandidateSkill(
                candidate_id=candidate.candidate_id, skill_id=skill.skill_id, status=_status(score), score=score,
            ))
            backing = [r for (rn, _t, tech, _p) in projects if skill_name in tech for r in [repos[rn]]]
            if score >= GOOD_THRESHOLD and backing:
                repo = backing[0]
                for kind, text, weight in [
                    ("fingerprint_match", f"{skill_name} found in the code", 40),
                    ("not_fork", "original repository, not a fork", 20),
                    ("recent_activity", "updated within the last 12 months", 20),
                ][: 3 if score >= STRONG_THRESHOLD else 2]:
                    db.add(models.Evidence(
                        candidate_id=candidate.candidate_id, skill_id=skill.skill_id, repo_id=repo.repo_id,
                        evidence_type=kind, description=f"{repo.repo_name}: {text}", weight=weight,
                    ))
            else:
                db.add(models.InterviewQuestion(
                    candidate_id=candidate.candidate_id, skill_id=skill.skill_id,
                    question=default_interview_question(skill_name),
                ))
    db.commit()
    return len(PROFILES)


def remove(db: Session) -> int:
    """Delete the demo students and everything attached to them. Returns how many were removed."""
    users = _demo_users(db)
    for user in users:
        for candidate in db.query(models.Candidate).filter_by(user_id=user.user_id).all():
            db.query(models.ShortlistEntry).filter_by(candidate_id=candidate.candidate_id).delete()
            db.delete(candidate)
        db.flush()
        db.delete(user)
    db.commit()
    return len(users)


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else ""
    if command not in ("add", "remove", "reset"):
        print(__doc__)
        return 1
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    with SessionLocal() as db:
        if command in ("remove", "reset"):
            print(f"Removed {remove(db)} demo students.")
        if command in ("add", "reset"):
            added = add(db)
            print(f"Added {added} demo students." if added else "Demo students are already there; nothing added.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
