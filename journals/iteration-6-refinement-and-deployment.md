# Iteration 6: Testing, refinement and deployment

**Dates:** 14–16 November 2026
**Goal (proposal):** pilot testing, metrics, scalability improvements, staging deployment.

## Completed
- [x] **Recruiter approval**: new recruiter accounts wait for an admin; admin page at `/admin`
      (PR #8)
- [x] In-app **notifications** with a bell in the top bar (PR #9)
- [x] **Practice quizzes** for students with explanations and history (PR #10)
- [x] **Recruiter skill tests**: timed, taken once, scores per skill and full answers for the
      recruiter; "Tests sent" tab (PR #11)
- [x] GitHub **caching** and a clear rate-limit message; test scores next to each skill's GitHub
      verdict; phone menu; question bank grown to 460 (10 per skill); tests prefer questions the
      student hasn't practised (PR #12)
- [x] **Skill gap roadmap** in Match a job, with ready-made roles, moved to its own page `/jobs`
      (PRs #13, #14)
- [x] **Deployment** preparation and go-live (PR #15, 16 Nov): resume PDFs stored in the database,
      `render.yaml`, `vercel.json`; live at https://dev-proof-mu.vercel.app (Vercel frontend,
      Render backend and PostgreSQL)
- [x] Documentation brought up to date (README, docs/, journals, reports, site)

## Decisions
- "Red flags" for suspicious GitHub patterns (e.g. many repositories created in one week) were
  considered and dropped: the interview explanation matters more than commit dates.
- Anti-cheating for skill tests is kept to: one attempt, server-side timer, shuffled questions and
  options, and questions not seen in practice. Tab-switch counting was postponed.

## Blockers / notes
- On the first Vercel import the deployment didn't start (the browser froze on the import page);
  it was started manually from Deployments → Create Deployment → `main`.
- Render and Vercel each needed their GitHub app given access to the DevProof repository.
- The live database starts empty; real users re-upload on the live site and demo data is added
  with `python -m app.demo_data add` against the live database URL.
- Render's free backend sleeps after 15 minutes idle (first request ~1 minute).

## Still to do
- Pilot evaluation with students and a recruiter against the proposal's metrics (see
  [final report status](../project-report-final/README.md)).
- Update the report and diagrams with these features.
