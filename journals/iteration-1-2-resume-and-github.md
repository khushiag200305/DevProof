# Iterations 1–2: Resume Intelligence and GitHub Evidence Engine

**Dates:** 15–17 September 2026
**Goal (proposal):** project setup, PDF upload, text/skill extraction, GitHub URL extraction, basic
CI; then GitHub API integration, repository retrieval, language/fork detection and activity.

## Completed
- [x] Repository scaffolded: FastAPI backend, React frontend, GitHub Actions CI (Khushi, 15 Sep)
- [x] Resume PDF upload endpoint and pdfplumber text extraction (Khushi, Rohit, 16 Sep)
- [x] Skill and GitHub-link extraction; name extraction with spaCy (Khushi, Rohit, 16 Sep)
- [x] GitHub Evidence Engine: fetch a user's repositories with language, fork status and last
      update (Khushi, 16 Sep)
- [x] First technology fingerprinting for Flask, FastAPI, Django, React and Docker (Khushi, 16 Sep)
- [x] Google sign-in with role-based access: `@thapar.edu` students upload their own resume,
      other accounts are recruiters who browse candidates (Rohit, 17 Sep)
- [x] Evidence scores shown in the frontend (Khushi, 17 Sep)

## Blockers / notes
- spaCy tagged technology words on short resume headers (e.g. "Python Developer") as a person's
  name; fixed in the name extraction (Rohit, 16 Sep).
- The first scoring version never credited fingerprint evidence in `/score`; found and fixed the
  same day (Khushi).
- Google sign-in needs the same OAuth Client ID in the frontend and backend `.env` files;
  documented in the README.

## Next iteration preview
Scan whole repositories rather than the root folder, cover more skills, and make every score
explainable.
