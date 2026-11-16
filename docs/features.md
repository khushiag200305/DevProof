# Features

Live app: https://dev-proof-mu.vercel.app

## Sign-in and roles

- Google sign-in only; no passwords are stored. The backend verifies Google's ID token and issues
  its own session token (JWT).
- `@thapar.edu` → **student**. Any other address → **recruiter**, who sees a waiting page until an
  admin approves the account (or immediately, for domains in `RECRUITER_AUTO_APPROVE_DOMAINS`).
- **Admins** (`ADMIN_EMAILS`) approve or reject recruiters at `/admin` ("Recruiter requests").

## Students

| Feature | Where | What it does |
|---|---|---|
| Upload a resume | My resumes | PDF up to 5 MB. Extracts name, claimed skills, projects (title, tech stack, dates, bullets) and GitHub username; an optional GitHub link overrides the one in the PDF. The PDF is stored in the database. |
| GitHub analysis | Report → Analyze GitHub evidence | Scores every claimed skill from the 10 most recently updated repositories ([scoring](scoring.md)), saves the evidence, links resume projects to repositories, writes interview questions for weak skills. Re-run any time. |
| Resume history | My resumes | Several uploads per account; delete one; choose which is **visible to recruiters** (the first upload is visible automatically; later ones ask). |
| Report | `/candidate/<id>` | Evidence ring, Skills tab (category filter, verdict, score, reasons, supporting repositories, interview question, test score), Projects tab, Portfolio & resume lines tab. |
| Public portfolio | `/p/<link>` | Publish with a headline; shows proven skills and projects; anyone with the link can open it, no sign-in. The owner is notified when it's viewed (at most once a day). |
| Resume lines | Portfolio & resume lines | Suggested bullet points from the analysed projects, optionally tailored to a pasted job description. |
| Match a job | `/jobs` | Paste a job description or pick a role (Backend, Frontend, Full Stack, Data Analyst, ML Engineer, Cloud / DevOps). Each resume gets a fit score (proven 100, claimed 40, missing 0, averaged); the best is marked with a reason and can be made visible. |
| Skill gap roadmap | `/jobs` | For the best resume: each unproven skill with what DevProof needs to see and which of the student's original repositories it fits into; each missing skill with a project idea; proven skills with their repository; Practise links and "Practise all my gaps". |
| Practice quizzes | `/practice` | 460 questions (10 per skill) with explanations; 5/10/15 questions; optional timer (1 minute per question); "Practise my unproven skills"; history. Private to the student. |
| Skill tests | `/practice` | Tests sent by recruiters appear at the top with the recruiter's company domain and message. Taken once; the timer starts on Start and runs on the server; reloading continues the same attempt; expires after 7 days; late answers are flagged. |

## Recruiters

| Feature | Where | What it does |
|---|---|---|
| Candidates | `/dashboard` | Every student's visible resume, searchable and sortable. |
| Candidate report | `/candidate/<id>` | Skills with evidence and interview questions, projects; a link to the visible resume if an older one is opened. |
| Talent search | `/talent` | Skills with the evidence needed (Strong / Good or better / on resume), match all or any, GitHub activity in the last 3/6/12 months, minimum original repositories, has GitHub, text. Ranked by average evidence score over the searched skills. One row per student. |
| Saved searches | `/talent` | Save a search; running it again marks new results; a notification arrives when a new resume matches. |
| Shortlist | `/talent` → Shortlist | Private notes per candidate; the student is notified once when shortlisted. |
| Compare | `/talent` | 2–4 candidates side by side, skill by skill. |
| Skill tests | Report → Skill tests | Pick skills (unproven ones preselected), 5/10/15 questions, 10–30 minutes, optional message. See status, score per skill and the full answers; cancel before it starts. The latest score shows as "Test x/y" next to the skill's GitHub verdict. Tests prefer questions the student hasn't practised. |
| Tests sent | `/talent` → Tests sent | Every test sent, with status and score. |

## Notifications

A bell in the top bar (checked every minute): analysis ready, new matches for a saved search,
shortlisted, portfolio viewed, new skill test, skill test finished, new recruiter request (admins),
recruiter approved.

## Limits worth knowing

- Evidence comes from public repositories on the default branch; owning a repository counts as
  authorship (no per-file check).
- Matching, roadmap and search only know the 46 catalog skills.
- Skill tests can't stop someone looking answers up or asking someone else; they are one signal
  next to the GitHub evidence and the interview questions.
