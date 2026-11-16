# Evidence scoring

Code: `code/backend/app/services/scoring.py`, detection rules in
`code/backend/app/skills_catalog.json` (applied by `services/tech_rules.py`).

## Which skills are scored

Only skills **claimed on the resume** are scored. Each of the 46 catalog skills is either:

- **checkable on GitHub** (`"check": "github"`): languages, frameworks, databases, Docker, AWS
  SDKs and config, ML and data libraries, notebooks, Tableau workbooks; or
- **not checkable** (`"check": "manual"`): concepts (OOP, DBMS, Operating Systems, ...), offline
  tools (Excel, Microsoft Office) and console settings (AWS IAM, VPC). These get **Not checkable on
  GitHub**, no score, the catalog's reason, and an interview question.

## Evidence kinds

| Kind | Example |
|---|---|
| Marker file | `Dockerfile`, `docker-compose.yml`, `pom.xml`, `CMakeLists.txt`, `serverless.yml`, `.twbx` |
| Source files | files with the skill's extensions, e.g. `.py`/`.ipynb`, `.java`, `.cpp`, `.c`, `.js/.jsx` (some skills need several) |
| Dependency | exact package name in `requirements.txt`, `pyproject.toml`, `package.json`, `pom.xml`, `build.gradle` (e.g. `fastapi`, `react`, `psycopg2`, `scikit-learn`) |
| Database image | `postgres`, `mysql` or `mongo` image in `docker-compose.yml` |

The whole repository tree is scanned, not just the root. `node_modules`, `venv`, `dist` and
`build` folders are ignored.

## Points per repository

| Signal | Points | Counted when |
|---|---|---|
| Fingerprint match | 40 | a marker file, source files, dependency or image for the skill is found |
| Language match | 20 | GitHub's primary language of the repository is the skill |
| Not a fork | 20 | the repository is original, **and** it showed the skill above |
| Recent activity | 20 | updated in the last 12 months, **and** it showed the skill above |

The last two only count when the repository shows the skill itself. Otherwise any recent,
original repository would add 40 points to every claimed skill.

A skill's score is its **best single repository** (capped at 100), not a sum over repositories,
so many weak repositories don't add up to a strong verdict. Other repositories that also show the
skill are listed as supporting repositories but don't change the score.

## Verdicts

| Score | Verdict | Shown with |
|---|---|---|
| 70–100 | **Strong Evidence** | the evidence and repository |
| 40–69 | **Good Evidence** | the evidence and repository |
| 0–39 | **Needs Verification** | the reason, and an interview question from the catalog |
| none | **Not checkable on GitHub** | the reason, and an interview question |

## Worked example

Resume claims **FastAPI**. The repository `shop-api` is original, updated last month, and has
`fastapi` in `requirements.txt`; its primary language is Python.

| Signal | Points |
|---|---|
| Fingerprint match (`fastapi` in requirements.txt) | 40 |
| Language match (Python ≠ FastAPI) | 0 |
| Not a fork | 20 |
| Recent activity | 20 |
| **Total** | **80 → Strong Evidence** |

The same resume claims **Python**: `shop-api` gives 40 (`requirements.txt` and `.py` files) + 20
(language) + 20 + 20 = 100, Strong Evidence. A claimed **Docker** with no Dockerfile or compose
file anywhere scores 0: Needs Verification, with the catalog's question "How did you use Docker to
containerize this application?".

## Beyond GitHub

- **Skill tests** (sent by recruiters) add a quiz score next to the GitHub verdict ("Test 4/5").
  They never change the evidence score.
- **Job fit** uses the verdicts: a proven skill (Strong or Good) counts 100, a claimed but unproven
  skill 40, a missing skill 0, averaged over the skills the job asks for.
