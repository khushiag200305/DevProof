# DevProof

Evidence-based developer skill assessment and interview support platform. DevProof extracts the skills a candidate claims on their resume, checks them against their public GitHub repositories, and gives every skill an explainable verdict, so recruiters spend less time verifying resume claims and students learn what to prove next.

**Live app: https://dev-proof-mu.vercel.app** (sign in with Google; `@thapar.edu` accounts are students) · [Project website](https://khushiag200305.github.io/DevProof/)

## Project overview

Resumes list skills (Python, React, Docker, ...) that are hard to verify at scale. DevProof automates the first pass:

```
Resume upload → skill, project and GitHub extraction → repository analysis → technology fingerprinting
→ rule-based evidence scoring → Strong / Good / Needs Verification → targeted interview question
```

Every score comes with the specific evidence that produced it (a file, a dependency, a repository). DevProof never claims to prove or disprove that someone "knows" a skill, only whether public evidence supports the claim. Skills that can't be seen in code are marked **Not checkable on GitHub** instead of getting an unfair 0, and short timed skill tests and interview questions cover what GitHub can't.

## Features

### Everyone
- **Google sign-in** (no passwords stored). An `@thapar.edu` address signs in as a **student**; any other address signs in as a **recruiter**, who waits for an admin to approve the account.
- **Notifications** bell: analysis finished, new matches for a saved search, shortlisted, portfolio viewed, skill test sent or finished, recruiter requests.
- Light and dark mode, and a layout that works on phones.

### Students
- **Resume upload** (PDF, up to 5 MB): name, claimed skills, projects (title, tech stack, dates, bullet points) and GitHub username are extracted with pdfplumber and spaCy.
- **GitHub evidence analysis** of the 10 most recently updated repositories: each claimed skill gets a 0–100 score, a verdict (Strong Evidence / Good Evidence / Needs Verification / Not checkable on GitHub), the evidence behind it, and an interview question when evidence is weak. Resume projects are linked to their repositories.
- **Several resumes per account**: upload history, delete, and choose which one is **visible to recruiters**.
- **Public portfolio page** (`/p/<link>`) with a headline, proven skills and projects, shareable without signing in.
- **Resume lines**: suggested resume bullet points built from the analysed projects, optionally tailored to a job description.
- **Match a job**: paste a job description or pick a ready-made role (Backend, Frontend, Full Stack, Data Analyst, ML Engineer, Cloud / DevOps). Every resume gets a fit score, and the best one gets a **skill gap roadmap**: what DevProof needs to see for each unproven skill and which of the student's own repositories it fits into, a project idea for each missing skill, and Practise links.
- **Practice quizzes**: 460 multiple-choice questions (10 per skill, with explanations), 5/10/15 at a time, optionally timed; "Practise my unproven skills"; history of attempts.
- **Skill tests from recruiters**: taken once, timed on the server, with questions the student hasn't seen in practice.

### Recruiters
- **Candidates** dashboard and candidate reports (skills with evidence, interview questions, projects).
- **Talent search**: filter by skills and evidence strength, all/any match, recent GitHub activity, number of original repositories and text; results ranked by evidence. **Saved searches** (with "new since last run"), **shortlist** with private notes, and **compare** 2–4 candidates side by side.
- **Skill tests**: send a short timed quiz on chosen skills from a candidate's report, see the score per skill and the full answers, and see the latest score as a "Test 4/5" badge next to each skill's GitHub verdict. A **Tests sent** tab lists them all.

### Admins
- **Recruiter requests** page to approve or reject recruiter accounts (`ADMIN_EMAILS`; company domains in `RECRUITER_AUTO_APPROVE_DOMAINS` are approved automatically).

## How the evidence is found

- **Skill catalog** (`code/backend/app/skills_catalog.json`): 46 skills in 8 resume-style categories (languages, web, databases, cloud, AI/ML, data & analytics, core concepts, tools), each with aliases (e.g. "ReactJS" → "React"), how it is checked, detection rules and an interview question. Adding a skill means adding one JSON entry; the catalog is validated at startup.
- **Technology fingerprinting**: every folder of a repository is scanned (ignoring `node_modules`, `venv`, `dist`, `build`) for marker files (`Dockerfile`, `pom.xml`, `CMakeLists.txt`, ...), source-file counts (e.g. 3+ `.py` files), package names in dependency files (`requirements.txt`, `package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`) and database images in `docker-compose.yml`.
- **Scoring** (per repository, best repository counts): fingerprint match 40 + language match 20 + not a fork 20 + updated in the last 12 months 20. Strong ≥ 70, Good 40–69, Needs Verification < 40. See [docs/scoring.md](docs/scoring.md).
- GitHub results are cached (repository list for 10 minutes, each repository until it is pushed again), and a GitHub rate limit stops the analysis with a clear "try again in N minutes" message.

## Architecture

```
React + TypeScript + Tailwind CSS (Vercel)
        ↓ REST API (Bearer session JWT)
FastAPI backend (Render)
 ├── Google sign-in (verify ID token → role by email domain → recruiter approval → session JWT)
 ├── Resume parsing (pdfplumber, spaCy)
 ├── GitHub evidence engine (GitHub REST API, cache) + technology fingerprinting
 ├── Evidence scoring, interview questions, portfolio, resume lines
 ├── Talent search, job fit + roadmap, quizzes and skill tests, notifications
        ↓
PostgreSQL (Render): users, candidates (with the resume PDF), skills, projects, repositories,
evidence, interview questions, portfolios, saved searches, shortlist, notifications,
quiz attempts, skill tests
```

Diagrams of the system, data model, request flow and CI/CD are in [docs/](docs/README.md).

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React 18, TypeScript, Tailwind CSS, React Router, Vite |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Auth | Google Identity Services (sign-in), PyJWT (DevProof session tokens) |
| Parsing | pdfplumber, spaCy (`en_core_web_sm`) |
| Database | PostgreSQL |
| External API | GitHub REST API |
| Testing | pytest + Ruff (backend, 220 tests), Vitest + React Testing Library + ESLint (frontend, 54 tests) |
| Automation | GitHub Actions CI on every pull request |
| Hosting | Vercel (frontend), Render (backend + PostgreSQL) |

## Repository layout

```
code/
├── backend/                       FastAPI app, evidence engine, tests
│   ├── app/routers/               one router per feature area
│   ├── app/services/              pure logic (scoring, talent search, job fit, roadmap, quiz, ...)
│   ├── app/skills_catalog.json    skill catalog and detection rules
│   └── app/question_bank.json     quiz questions
└── frontend/                      React app (src/pages, src/components, src/lib) and tests
docs/                              Architecture, data model, scoring, API and CI/CD documentation
journals/                          Progress journals, one per iteration
project-proposal/                  Original project proposal (PDF)
project-report-prototype-stage/    Prototype demo guide
project-report-final/              Final report outline and status
site/                              Project website (GitHub Pages, .github/workflows/pages.yml)
render.yaml                        Render deployment (backend + database)
```

## Run locally

### Requirements

- Python 3.11+ (a `venv` or a conda environment both work)
- Node.js 20+
- PostgreSQL 15+ (required: sign-in and candidate data are persisted; see setup below). On macOS,
  [Postgres.app](https://postgresapp.com) or Homebrew both work.

### 1. Set up PostgreSQL

macOS (Homebrew):

```
brew install postgresql@16
brew services start postgresql@16
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"   # add to your shell profile

psql -d postgres -c "CREATE ROLE devproof WITH LOGIN PASSWORD 'devproof';"
psql -d postgres -c "CREATE DATABASE devproof OWNER devproof;"
# PostgreSQL 15+ no longer grants CREATE on the public schema by default -
# without this, table creation on startup fails with "no schema has been
# selected to create in":
psql -d devproof -c "GRANT ALL ON SCHEMA public TO devproof;"
```

(Already have Postgres running elsewhere? Just create a `devproof`/`devproof` role+database,
run the `GRANT` above, or point `DATABASE_URL` at whatever instance you have.)

### 2. Google sign-in setup

DevProof uses Google Identity Services for sign-in — no passwords are stored. You need one
OAuth Client ID, shared by both the frontend and backend:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) → create a project (or
   pick an existing one).
2. **APIs & Services → OAuth consent screen**: choose **External**, fill in an app name and your
   email, and add your own Google account as a test user (while the app is unpublished, only
   test users can sign in).
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Web application**
   - Authorized JavaScript origins: `http://localhost:5173`
   - Leave Authorized redirect URIs empty (not needed for the popup-based sign-in flow)
4. Copy the generated **Client ID** (looks like `1234567890-abc...apps.googleusercontent.com`).

### 3. Start the backend

```
cd code/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
cp .env.example .env
```

Edit `.env` and set `GOOGLE_CLIENT_ID` to the Client ID from step 2, `JWT_SECRET` to a
random string (`python -c "import secrets; print(secrets.token_urlsafe(32))"`), `GITHUB_TOKEN`
(see step 5) and `ADMIN_EMAILS` to your own email so you can approve recruiters. Then:

```
uvicorn app.main:app --reload
```

The API starts at `http://localhost:8000` (interactive docs at `/docs`).

### 4. Start the frontend

```
cd code/frontend
npm install
cp .env.example .env
```

Edit `.env` and set `VITE_GOOGLE_CLIENT_ID` to the **same** Client ID from step 2. Then:

```
npm run dev
```

Open `http://localhost:5173` in a browser. Sign in with an `@thapar.edu` address to land on the
student upload flow, or any other address to sign in as a recruiter (approve it at `/admin` with an
admin account).

### 5. Run the GitHub evidence analysis

Open any candidate's report and click **Analyze GitHub evidence**. The backend
(`POST /api/candidates/{id}/analyze`) fetches the candidate's 10 most recently updated public
repositories, fingerprints them, scores every claimed skill from 0 to 100, and saves the
classification, the evidence behind each score, and a suggested interview question for skills that
need verification. Click **Re-run analysis** later to refresh the results.

One analysis makes up to ~50 GitHub API calls. Without a token GitHub allows 60 per hour, so set
`GITHUB_TOKEN` in `code/backend/.env` (a classic token with no scopes is enough) before a demo.

### 6. Optional: demo data

`python -m app.demo_data add` (from `code/backend`) adds 20 clearly marked fictional students
("... (Demo)", `@demo.devproof` emails, no GitHub account) so recruiter features have data to show.
`python -m app.demo_data remove` deletes only them.

### Tests

```
cd code/backend && pytest          # needs the PostgreSQL database from step 1
cd code/frontend && npm test && npm run lint && npm run build
```

## Deploy

The backend and its database run on **Render** (free plan), the frontend on **Vercel** (free plan).
Resume PDFs are stored in the database, so nothing is lost when Render restarts the server.

### 1. Backend and database on Render

1. Sign in to [render.com](https://render.com) with GitHub.
2. **New > Blueprint**, pick this repository. Render reads `render.yaml` and creates the
   `devproof-api` web service and the `devproof-db` database.
3. Fill in the values it asks for:

   | Setting | Value |
   |---|---|
   | `GOOGLE_CLIENT_ID` | the same Client ID as in `code/backend/.env` |
   | `GITHUB_TOKEN` | the same token as in `code/backend/.env` |
   | `ADMIN_EMAILS` | admin emails, comma-separated |
   | `FRONTEND_ORIGINS` | leave empty for now (filled in step 3) |
   | `RECRUITER_AUTO_APPROVE_DOMAINS` | optional, can be empty |

   `DATABASE_URL` and `JWT_SECRET` are filled in automatically.
4. Wait for the first deploy (about 5 minutes) and open `https://<service>.onrender.com/health`;
   it should show `{"status":"ok", ...}`. Copy that address (without `/health`).

### 2. Frontend on Vercel

1. Sign in to [vercel.com](https://vercel.com) with GitHub. **Add New > Project**, import this
   repository.
2. Set **Root Directory** to `code/frontend` (framework preset: Vite).
3. Environment variables:
   - `VITE_API_BASE` = the Render address from step 1, e.g. `https://devproof-api.onrender.com`
   - `VITE_GOOGLE_CLIENT_ID` = the same Client ID
4. Deploy and copy the site address, e.g. `https://devproof.vercel.app`.
   `vercel.json` sends every path to the React app, so links like `/p/<slug>` open directly.

### 3. Connect them

1. In Render, set `FRONTEND_ORIGINS` to the Vercel address (no trailing slash) and save; the
   service redeploys.
2. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), open the OAuth
   client and add the Vercel address under **Authorized JavaScript origins**. It can take a few
   minutes to apply.
3. Open the Vercel address and sign in.

### Good to know

- Render's free web service sleeps after 15 minutes without visits; the first request then
  takes about a minute. Open the site a few minutes before a demo.
- Render's free PostgreSQL database is time-limited (check Render's current free-plan limits);
  export anything you need before it expires.
- Every push to `main` redeploys both sites automatically.
- Optional demo students: copy the database's **External Database URL** from Render, then on your
  own computer run `DATABASE_URL="<that url>" python -m app.demo_data add` from `code/backend`.

## Development workflow

- Feature branch → Pull Request → GitHub Actions (backend: Ruff + pytest against PostgreSQL;
  frontend: ESLint + Vitest + production build) → review → merge into `main` → Render and Vercel
  redeploy automatically.
- Each iteration was demonstrable on its own; progress is recorded in [journals/](journals/).

## Timeline

Planned in the proposal (13-week semester) and what was delivered:

| Iteration | Planned | Delivered |
|---|---|---|
| 1. Resume Intelligence | Project setup, PDF upload, text/skill extraction, GitHub URL extraction, basic CI | Done (15–16 Sep): scaffold, CI, PDF parsing, skill and GitHub link extraction |
| 2. GitHub Evidence Engine | GitHub API integration, repo retrieval, language/fork detection, activity analysis | Done (16–17 Sep), plus Google sign-in with student/recruiter roles |
| 3. Technology Fingerprint Engine | Dependency/config detection rules for an initial tech set | Done (16 Sep – 11 Oct): whole-repo scan, 46-skill catalog, "Not checkable on GitHub" |
| 4. Evidence Scoring | Transparent scoring engine, classification with explanations | Done (17 Sep – 11 Oct): 40/20/20/20 scoring, reasons, supporting repositories |
| 5. Dashboard + Interview Support | Candidate dashboard, skill detail views, interview questions | Done (Oct – 9 Nov): reports with tabs, portfolio, resume lines, project parsing, talent search, Match a job |
| 6. Testing, Evaluation & Refinement | Pilot testing, metrics, scalability, staging deployment | 14–16 Nov: recruiter approval, notifications, practice quizzes, skill tests, roadmap, GitHub caching, deployment to Vercel + Render. Pilot evaluation still to do |
| 7. Buffer | Contingency, documentation, final review | Documentation updated 16 Nov |

## Documentation

- [Project proposal](project-proposal/DevProof-Project-Proposal.pdf)
- [Architecture, data model, scoring, API and CI/CD](docs/README.md)
- [Progress journals](journals/README.md)
- [Prototype demo guide](project-report-prototype-stage/PROTOTYPE_DEMO.md)
- [Final report outline and status](project-report-final/README.md)
- [Project website](https://khushiag200305.github.io/DevProof/) (source in [site/](site/README.md))

## Authors

| Team member | Roll number |
|---|---|
| Khushi Agarwal | 1024170221 |
| Swathi Gurada | 1024170106 |
| Rohit Singhal | 1024170213 |

---

DevProof · Software Engineering (UCS503) · Thapar Institute of Engineering and Technology
