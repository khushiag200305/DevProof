"""
Skill gap roadmap: for the resume that best fits a job (or a ready-made
role), say what to do about every skill the job wants:

    proven        nothing to do; names the repository that proves it
    claimed only  how DevProof would see it on GitHub, and which of the
                  student's own repositories it would fit into
    missing       a small project idea that would prove it

Pure logic: works on the scored resume from services/job_fit.py and a
list of the resume's analysed repositories.
"""
from datetime import datetime, timezone

from ..skills_dictionary import SKILLS

# Ready-made roles a student can pick instead of pasting a job description.
ROLES: dict[str, list[str]] = {
    "Backend Developer": ["Python", "FastAPI", "Django", "SQL", "PostgreSQL", "Docker", "Git & GitHub", "Data Structures & Algorithms", "DBMS", "Object-Oriented Programming"],
    "Frontend Developer": ["JavaScript", "React", "Node.js", "Git & GitHub", "Data Structures & Algorithms", "Computer Networks"],
    "Full Stack Developer": ["JavaScript", "React", "Node.js", "Express", "MongoDB", "SQL", "Docker", "Git & GitHub", "Data Structures & Algorithms"],
    "Data Analyst": ["Python", "SQL", "Pandas", "Excel", "Data Cleaning", "Exploratory Data Analysis", "Data Visualization", "Tableau", "Data Analysis"],
    "ML Engineer": ["Python", "Machine Learning", "NumPy", "Pandas", "PCA", "K-Means Clustering", "Data Cleaning", "Docker", "Git & GitHub"],
    "Cloud / DevOps Engineer": ["Docker", "AWS", "AWS EC2", "AWS S3", "AWS Lambda", "AWS IAM", "AWS VPC", "Cloud Computing", "Operating Systems", "Computer Networks", "Git & GitHub"],
}

# Which technologies a repository should already use for a skill to fit
# naturally into it (e.g. FastAPI goes into a Python repo).
HOSTS: dict[str, list[str]] = {
    "React": ["JavaScript", "Node.js"],
    "Node.js": ["JavaScript"],
    "Express": ["Node.js", "JavaScript"],
    "Flask": ["Python"],
    "FastAPI": ["Python"],
    "Django": ["Python"],
    "SQL": ["FastAPI", "Flask", "Django", "Express", "Node.js", "Java"],
    "MySQL": ["FastAPI", "Flask", "Django", "Express", "Node.js", "Java"],
    "PostgreSQL": ["FastAPI", "Flask", "Django", "Express", "Node.js", "Java"],
    "MongoDB": ["Express", "Node.js", "FastAPI", "Flask"],
    "Docker": ["FastAPI", "Flask", "Django", "Express", "Node.js", "Java", "Python"],
    "AWS": ["FastAPI", "Flask", "Django", "Express", "Node.js", "Python"],
    "AWS Lambda": ["Python", "Node.js", "JavaScript"],
    "AWS S3": ["Django", "FastAPI", "Flask", "Express", "Node.js"],
    "Machine Learning": ["Pandas", "NumPy", "Python"],
    "Prompt Engineering": ["Python", "JavaScript"],
    "Pandas": ["Python"],
    "NumPy": ["Python"],
    "Data Analysis": ["Pandas", "Python"],
    "Data Cleaning": ["Pandas", "Python"],
    "Exploratory Data Analysis": ["Pandas", "Python"],
    "Data Visualization": ["Pandas", "React", "Python"],
}

# One small project that would prove each skill.
PROJECT_IDEAS: dict[str, str] = {
    "Python": "Write a command-line tool, e.g. an expense tracker that saves to a CSV file.",
    "Java": "Build a library management console app with classes for books, members and loans.",
    "C": "Write a student records program using structs, files and dynamic memory.",
    "C++": "Build a bank account simulator using classes, the STL and smart pointers.",
    "JavaScript": "Make an interactive to-do or quiz web page with plain JavaScript.",
    "React": "Build a small React app that fetches data from a public API and lets users filter it.",
    "Node.js": "Write a small Node.js server that serves a JSON API.",
    "Express": "Build a REST API with Express for notes or tasks, with create, read, update and delete routes.",
    "Flask": "Build a Flask web app with a form and a database, e.g. a feedback board.",
    "FastAPI": "Build a FastAPI backend with a few endpoints and Pydantic models, e.g. a bookings API.",
    "Django": "Build a Django blog with models, the admin site and user login.",
    "SQL": "Design a schema for a small shop in a .sql file and write queries for common reports.",
    "MySQL": "Connect an app to MySQL and store its data there instead of a file.",
    "PostgreSQL": "Connect an app to PostgreSQL, ideally run with docker-compose.",
    "MongoDB": "Store an app's data in MongoDB, e.g. with Mongoose or PyMongo.",
    "Database Design": "Draw an ER diagram for a project, then build the tables from it.",
    "Normalization": "Take a messy spreadsheet, normalise it to 3NF and explain each step in a README.",
    "CRUD Operations": "Build an app with full create, read, update and delete for one kind of record.",
    "Docker": "Add a Dockerfile and docker-compose.yml so one of your apps runs with a single command.",
    "AWS": "Deploy one of your apps on AWS, e.g. with Elastic Beanstalk or Lambda.",
    "AWS Lambda": "Write a Lambda function triggered by an API or a file upload.",
    "AWS S3": "Let an app upload and download files from an S3 bucket.",
    "AWS EC2": "Host one of your apps on an EC2 instance and describe the setup in its README.",
    "AWS IAM": "Set up an IAM role with least-privilege access for one of your AWS projects.",
    "AWS VPC": "Draw and document a VPC with public and private subnets for an app.",
    "Cloud Computing": "Deploy a project to a cloud platform and explain the service model you used.",
    "Machine Learning": "Train and evaluate a model with scikit-learn on a public dataset, in a notebook.",
    "PCA": "Apply PCA to a dataset in a notebook and plot the explained variance.",
    "K-Means Clustering": "Cluster customers or songs with K-Means and choose k with the elbow method.",
    "Prompt Engineering": "Build a small app that calls an LLM API with a well-designed prompt.",
    "Pandas": "Analyse a public dataset with pandas in a notebook and summarise the findings.",
    "NumPy": "Implement a small numeric task, e.g. image filters or matrix maths, with NumPy.",
    "Data Analysis": "Answer three questions about a public dataset in a Jupyter notebook.",
    "Data Cleaning": "Clean a messy real dataset in a notebook: missing values, duplicates and types.",
    "Exploratory Data Analysis": "Do an EDA notebook with distributions, correlations and outliers.",
    "Data Visualization": "Build a few clear charts with matplotlib, seaborn or plotly from real data.",
    "Tableau": "Publish a Tableau dashboard and commit the workbook (.twbx) to a repository.",
    "Excel": "Build an Excel model with formulas, a pivot table and a chart.",
    "Data Structures & Algorithms": "Solve problems regularly and keep your solutions in a repository.",
    "Object-Oriented Programming": "Design a small system, e.g. parking lot or library, with classes and inheritance.",
    "Computer Networks": "Write a simple client-server chat using sockets.",
    "Operating Systems": "Simulate CPU scheduling or page replacement algorithms in code.",
    "DBMS": "Build a small project that uses transactions and indexes, and explain them in the README.",
    "Git & GitHub": "Push your projects to GitHub with clear commits, branches and pull requests.",
    "VS Code": "Mention the extensions and debugging setup you use when you talk about your projects.",
    "Microsoft Office": "Prepare a report in Word and a slide deck in PowerPoint for one of your projects.",
}


# What DevProof looks for on GitHub, in plain words, for each skill it can check.
PROOF_HINTS: dict[str, str] = {
    "Python": "Commit a few .py files or a notebook, with a requirements.txt.",
    "Java": "Commit Java source files, ideally with a pom.xml or build.gradle.",
    "C": "Commit at least 3 .c source files.",
    "C++": "Commit at least 3 .cpp files, ideally with a CMakeLists.txt.",
    "JavaScript": "Commit at least 3 .js or .jsx files.",
    "React": "List react in the project's package.json.",
    "Node.js": "Add a Node backend, e.g. express in package.json.",
    "Express": "List express in package.json.",
    "Flask": "List flask in requirements.txt.",
    "FastAPI": "List fastapi in requirements.txt.",
    "Django": "List django in requirements.txt.",
    "SQL": "Commit a .sql schema file, or connect the app to a SQL database driver.",
    "MySQL": "Use a MySQL driver (e.g. pymysql or mysql2) or a mysql image in docker-compose.",
    "PostgreSQL": "Use a Postgres driver (e.g. psycopg2 or pg) or a postgres image in docker-compose.",
    "MongoDB": "Use pymongo or mongoose, or a mongo image in docker-compose.",
    "Docker": "Add a Dockerfile or docker-compose.yml.",
    "AWS": "Use boto3 or the AWS SDK, or add a serverless.yml / cdk.json.",
    "AWS Lambda": "Add a serverless.yml or samconfig.toml, or use mangum for a Python API.",
    "AWS S3": "Use the S3 client (@aws-sdk/client-s3, s3fs or django-storages).",
    "Machine Learning": "List scikit-learn, tensorflow or torch in requirements.txt.",
    "Prompt Engineering": "Call an LLM API, e.g. openai or anthropic in requirements.txt.",
    "Pandas": "List pandas in requirements.txt.",
    "NumPy": "List numpy in requirements.txt.",
    "Data Analysis": "Commit a Jupyter notebook, or list pandas in requirements.txt.",
    "Data Cleaning": "Commit a Jupyter notebook, or list pandas in requirements.txt.",
    "Exploratory Data Analysis": "Commit a Jupyter notebook, or list pandas in requirements.txt.",
    "Data Visualization": "Use matplotlib, seaborn or plotly, or a chart library like recharts.",
    "Tableau": "Commit a Tableau workbook (.twb or .twbx).",
    "Git & GitHub": "Any original repository with your own commits counts.",
}


def how_to_prove(skill: str) -> str | None:
    """What DevProof looks for on GitHub for this skill, or None if it can't be checked there."""
    info = SKILLS.get(skill)
    if not info or info["check"] != "github":
        return None
    return PROOF_HINTS.get(skill, f"Push a project that uses {skill}.")


def _aware(value) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _host_repo(skill: str, repos: list[dict]) -> str | None:
    """The student's most recently pushed original repo where this skill fits."""
    hosts = set(HOSTS.get(skill, []))
    candidates = [
        r for r in repos
        if not r.get("is_fork") and skill not in r.get("technologies", []) and hosts & set(r.get("technologies", []))
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: _aware(r.get("pushed_at")))["name"]


def _proof_repo(skill: str, repos: list[dict]) -> str | None:
    owning = [r for r in repos if skill in r.get("technologies", [])]
    owning.sort(key=lambda r: (r.get("is_fork", False), -_aware(r.get("pushed_at")).timestamp()))
    return owning[0]["name"] if owning else None


def build_roadmap(fit: dict, repos: list[dict]) -> dict:
    """
    `fit` is one resume scored by job_fit.score_resume (proven /
    claimed_only / missing). `repos`: [{name, technologies, is_fork, pushed_at}].
    """
    proven = [{"skill": s, "repo": _proof_repo(s, repos)} for s in fit["proven"]]

    claimed = []
    for s in fit["claimed_only"]:
        proof = how_to_prove(s)
        repo = _host_repo(s, repos) if proof else None
        if proof is None:
            step = "GitHub can't show this one. Practise it and be ready to explain it with an example in the interview."
        else:
            step = f"{proof} Then re-run the analysis."
        claimed.append({"skill": s, "checkable": proof is not None, "repo": repo, "step": step})

    missing = []
    for s in fit["missing"]:
        repo = _host_repo(s, repos) if how_to_prove(s) else None
        idea = PROJECT_IDEAS.get(s, f"Build a small project that uses {s}.")
        missing.append({"skill": s, "checkable": how_to_prove(s) is not None, "repo": repo, "idea": idea,
                        "proof": how_to_prove(s)})

    return {
        "candidate_id": fit["candidate_id"],
        "fit": fit["fit"],
        "proven": proven,
        "claimed": claimed,
        "missing": missing,
        "practice": [g["skill"] for g in claimed + missing],
    }
