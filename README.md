# DevProof

Evidence-based developer skill assessment and interview support platform. DevProof extracts claimed skills from a candidate's resume and analyzes their public GitHub activity to produce transparent, explainable skill-support assessments — reducing the manual effort recruiters spend verifying resume claims.

## Project overview

Resumes list skills (Python, React, Docker, etc.) that are hard to verify at scale. DevProof automates the first pass:

```
Resume upload → skill/GitHub extraction → repository analysis → technology fingerprinting
→ rule-based evidence scoring → Strong / Good / Needs Verification → targeted interview question
```

The prototype favors an explainable, rule-based approach over opaque ML: every score comes with the specific evidence items that produced it, and the system never claims to prove or disprove that a candidate "knows" a skill — only whether public evidence supports the claim.

## Features (planned for MVP)

- Google sign-in only (no passwords stored): an `@thapar.edu` address signs in as a **student**,
  any other address signs in as a **recruiter** — students upload their own resume and see their
  own report; recruiters browse every candidate who has uploaded one
- Resume PDF upload and parsing (pdfplumber) with skill/name/GitHub-link extraction
- Skill normalization (e.g. "ReactJS" → "React") via curated mapping + spaCy NER
- GitHub REST API integration: language composition, dependency manifests, fork status, commit activity
- Technology fingerprinting for an initial set: Python, Java, C++, JavaScript, React, Node.js, Express, Flask, FastAPI, Django, MongoDB, MySQL, PostgreSQL, Docker
- Transparent 0–100 rule-based evidence scoring with configurable weights
- Classification: Strong Evidence / Good Evidence / Needs Verification, each with a stated reason
- Auto-generated, template-based interview questions for low-evidence skills
- Candidate dashboard (React + Tailwind) with skill detail views

## Architecture

```
React + Tailwind CSS (frontend)
        ↓ REST API (Bearer session JWT)
FastAPI backend
 ├── Google sign-in (verify ID token → role by email domain → issue session JWT)
 ├── Resume parsing & NLP (pdfplumber, spaCy)
 ├── GitHub evidence engine (GitHub REST API)
 ├── Technology fingerprinting
 └── Evidence scoring & explainability
        ↓
PostgreSQL (User, Candidate, Skill, CandidateSkill, Repository, Evidence, Project, InterviewQuestion)
```

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React, Tailwind CSS, React Router |
| Backend | Python, FastAPI |
| Auth | Google Identity Services (sign-in), PyJWT (DevProof session tokens) |
| NLP / parsing | pdfplumber, spaCy, (optional) sentence-transformers |
| Database | PostgreSQL |
| External API | GitHub REST API |
| Testing | pytest + Ruff (backend), Vitest + React Testing Library + ESLint (frontend) |
| Automation | GitHub Actions CI/CD |

## Repository layout

```
code/
├── backend/                       FastAPI app, scoring engine, tests
└── frontend/                      React/Tailwind app and frontend tests
docs/                              Architecture diagrams, scoring tables, CI/CD diagram
journals/                          Weekly progress journals (one per iteration)
project-proposal/                  Original project proposal (PDF)
project-report-prototype-stage/    Mid-project prototype report + demo guide
project-report-final/              Final project report
site/                              GitHub Pages project documentation site (optional)
```

## Run locally

### Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (required — sign-in and candidate data are persisted; see setup below)

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

Edit `.env` and set `GOOGLE_CLIENT_ID` to the Client ID from step 2, and `JWT_SECRET` to a
random string (`python -c "import secrets; print(secrets.token_urlsafe(32))"`). Then:

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
student upload flow, or any other address to land on the recruiter dashboard.

## Development workflow

- Feature branch → Pull Request → GitHub Actions (lint + test + build) → Code review → Merge → Deploy to staging
- Weekly iterations per the timeline below; each iteration should be independently demonstrable

## Timeline (13-week semester plan)

| Week(s) | Iteration | Deliverable |
|---|---|---|
| 1–2 | Resume Intelligence | Project setup, PDF upload, text/skill extraction, GitHub URL extraction, basic CI |
| 3–4 | GitHub Evidence Engine | GitHub API integration, repo retrieval, language/fork detection, activity analysis |
| 5–6 | Technology Fingerprint Engine | Dependency/config detection rules for initial tech set |
| 7–8 | Evidence Scoring | Transparent scoring engine, classification with explanations |
| 9–10 | Dashboard + Interview Support | Candidate dashboard, skill detail views, interview question generation |
| 11–12 | Testing, Evaluation & Refinement | Pilot testing, metrics, scalability improvements, staging deployment |
| 13 | Buffer | Contingency, documentation, final review |

## Documentation

- [Project proposal](project-proposal/DevProof-Project-Proposal.pdf)
- Prototype demo guide — added in `project-report-prototype-stage/` once available
- Architecture diagrams — added in `docs/` once available

## Authors

| Team member | Roll number |
|---|---|
| Khushi Agarwal | 1024170221 |
| Swathi Gurada | 1024170106 |
| Rohit Singhal | 1024170213 |

---

DevProof · Software Engineering (UCS503) · Thapar Institute of Engineering and Technology
