# DevProof — Final Project Report

The final report (PDF, department template) goes in this folder. This page is its outline and
the current status of each section, so the report can be written from it.

Live app: https://dev-proof-mu.vercel.app · Repository documentation: [docs/](../docs/README.md)

## 1. Final architecture and changes from the proposal

As proposed: React frontend, FastAPI backend, PostgreSQL, GitHub REST API, rule-based explainable
scoring, GitHub Actions CI. See [docs/architecture.md](../docs/architecture.md).

Changes and additions:
- **Google sign-in** with student / recruiter roles and **admin approval** for recruiters (not in
  the proposal; needed so only real recruiters see students' data).
- **Skill catalog** as one JSON file (46 skills, 8 categories) instead of rules in code, and a
  **Not checkable on GitHub** verdict for concepts and offline tools.
- Sentence-transformers (optional in the proposal) were not needed: matching uses the catalog's
  aliases.
- **Deployment** on Vercel (frontend) and Render (backend + PostgreSQL), with resume PDFs stored
  in the database ([docs/ci-cd.md](../docs/ci-cd.md)).

## 2. Implemented features vs planned scope

| Planned (proposal) | Status |
|---|---|
| Resume PDF upload and parsing (skills, GitHub link) | Done, plus name and projects with tech stack and dates |
| GitHub API integration: languages, manifests, forks, activity | Done, with caching and rate-limit handling |
| Technology fingerprinting | Done for every GitHub-checkable catalog skill, whole-repository scan |
| Transparent 0–100 scoring with configurable weights | Done (40/20/20/20, thresholds 70/40) |
| Strong / Good / Needs Verification with reasons | Done, plus Not checkable on GitHub |
| Template-based interview questions for low-evidence skills | Done (catalog question per skill) |
| Candidate dashboard with skill detail views | Done (reports with tabs, expandable skill rows) |
| Staging deployment | Done: production at https://dev-proof-mu.vercel.app |

Beyond the proposal: public portfolio, resume lines, talent search (saved searches, shortlist,
compare), visible-resume choice, Match a job with a skill gap roadmap, practice quizzes, recruiter
skill tests, notifications, demo data. Details in [docs/features.md](../docs/features.md).

## 3. Evaluation against the proposal's metrics (Table 3)

**Status: not measured yet.** The pilot (students uploading on the live site, at least one recruiter
or faculty member reviewing candidates) is the next step. Suggested method for each metric:

| Metric | How to measure | Result |
|---|---|---|
| Verification time reduction | Time a reviewer takes to judge 5 resumes' skills by hand (reading GitHub) vs with DevProof reports | _to fill in_ |
| Human-system agreement | Reviewer rates each claimed skill Strong / Good / Needs verification by hand; % agreement with DevProof's verdicts | _to fill in_ |
| Evidence coverage | Share of claimed, GitHub-checkable skills that get at least Good Evidence across pilot resumes | _to fill in_ |
| User clarity | Short survey (1–5): "I understand why each skill got its verdict" | _to fill in_ |
| Reliability | Analyses completed without error / total; same verdicts on re-run with unchanged repositories | _to fill in_ |
| Interview-question usefulness | Reviewer rates the suggested questions (1–5) for skills needing verification | _to fill in_ |

Engineering quality already available: 220 backend and 54 frontend automated tests run on every
pull request.

## 4. Lessons learned, limitations and future work

Lessons (from the [journals](../journals/README.md)):
- Bonus points must only count on repositories that show the skill; otherwise every skill scored
  well.
- Free hosting wipes local files, so uploaded files belong in the database.
- An explainable rule-based score was easier to justify to users than an opaque model.
- Design feedback took several rounds; a flat, report-style look worked best for a verification tool.

Limitations:
- Public repositories and the default branch only; repository ownership counts as authorship.
- Only catalog skills are recognised.
- Skill tests can't prevent looking up answers; they are one signal among several.
- Free hosting: the backend sleeps when idle and the free database is time-limited.

Future work:
- Per-commit authorship checks for shared repositories.
- Signals on skill tests (time per question, leaving the page).
- More skills and questions; skills outside the catalog.
- Email notifications.
