# DevProof — Prototype Demo Guide

The prototype stage covered iterations 1–4 of the proposal (resume intelligence, GitHub evidence
engine, technology fingerprinting, evidence scoring). The full app is now live at
**https://dev-proof-mu.vercel.app**; this guide shows the prototype flow on it.

## What the prototype demonstrates
- Resume upload with extraction of name, claimed skills, projects and GitHub username
- Retrieval of the candidate's 10 most recently updated public repositories
- Technology fingerprinting across the whole repository (marker files, source files, dependency
  manifests, database images) for the 46-skill catalog
- Transparent 0–100 evidence scoring with a verdict and the evidence behind it
  ([docs/scoring.md](../docs/scoring.md))
- An interview question for every skill with weak or no evidence, and "Not checkable on GitHub"
  for concepts and offline tools

## How to run it
- **Live:** open https://dev-proof-mu.vercel.app and sign in with Google. If the site was idle,
  the first load takes up to a minute while the free backend wakes up.
- **Locally:** see the root [README](../README.md#run-locally).

## Demo flow (about 5 minutes)
1. **Sign in** with an `@thapar.edu` account (student).
2. **Upload a resume PDF** on My resumes. Point out the extracted skills, projects and GitHub link.
3. Open the report and click **Analyze GitHub evidence**.
4. On the **Skills** tab, open one skill of each kind:
   - **Strong Evidence:** show the reason (e.g. `fastapi` in `requirements.txt`) and the
     repository, plus other supporting repositories;
   - **Needs Verification:** show that nothing was found and the generated interview question;
   - **Not checkable on GitHub** (e.g. DBMS): show the reason instead of a 0 score.
5. On the **Projects** tab, show resume projects linked to their repositories.
6. Sign in as a **recruiter** (non-Thapar account approved at `/admin`) and open the same candidate
   from Candidates to show the recruiter's view.

Afterwards, the features added later can be shown: Talent search, Match a job with the roadmap,
Practice and skill tests ([docs/features.md](../docs/features.md)).

## Known limitations at the prototype stage
- Only the default branch of public repositories is scanned; owning a repository counts as
  authorship (no per-file check).
- Scoring weights (40/20/20/20) and thresholds (70/40) were chosen by hand, not tuned on data.
- Only the 46 catalog skills are recognised; other skills on a resume are ignored.
- Interview questions come from the catalog (one per skill), not generated per project.
- GitHub's rate limit (60 requests/hour without a token) limits how many analyses can run; a token
  and, since iteration 6, caching address this.
