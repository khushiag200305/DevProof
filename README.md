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
        ↓ REST API
FastAPI backend
 ├── Resume parsing & NLP (pdfplumber, spaCy)
 ├── GitHub evidence engine (GitHub REST API)
 ├── Technology fingerprinting
 └── Evidence scoring & explainability
        ↓
PostgreSQL (Candidate, Skill, CandidateSkill, Repository, Evidence, Project, InterviewQuestion)
```

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React, Tailwind CSS |
| Backend | Python, FastAPI |
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
- PostgreSQL (optional for early iterations — see below)

### 1. Start the backend

```
cd code/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts at `http://localhost:8000`.

### 2. Start the frontend

```
cd code/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in a browser.

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
