# REST API

Base URL: `https://devproof-api-yurx.onrender.com` (local: `http://localhost:8000`). Interactive
docs: `/docs`. Every `/api` call except sign-in and public portfolios needs
`Authorization: Bearer <session token>`. "Recruiter" means an **approved** recruiter.

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/health` | anyone | Liveness check |
| **Auth** | | | |
| POST | `/api/auth/google` | anyone | Exchange a Google ID token for a session token and user |
| GET | `/api/auth/me` | signed in | Current user, role, recruiter status, admin flag |
| **Resumes and reports** | | | |
| POST | `/api/resume/upload` | student | Upload and parse a resume PDF |
| GET | `/api/candidates` | recruiter | Visible resumes of all students |
| GET | `/api/candidates/me` | student | Own uploads |
| GET | `/api/candidates/{id}` | owner, recruiter | Report |
| PUT | `/api/candidates/{id}/visible` | owner | Make this resume the one recruiters see |
| DELETE | `/api/candidates/{id}` | owner | Delete an upload and its report |
| POST | `/api/candidates/{id}/analyze` | owner, recruiter | Run the GitHub evidence analysis |
| POST | `/api/candidates/{id}/resume-bullets` | owner, recruiter | Suggested resume lines (optional job description) |
| GET / PUT | `/api/candidates/{id}/portfolio` | owner | Portfolio settings (publish, headline) |
| GET | `/api/portfolio/{slug}` | anyone | Public portfolio page |
| **Match a job** | | | |
| GET | `/api/job-fit/roles` | student | Ready-made roles |
| POST | `/api/job-fit` | student | Fit of every upload to `job_description` or `role`, with a roadmap |
| **Talent search** | | | |
| GET | `/api/talent/skills` | recruiter | Skill suggestions |
| POST | `/api/talent/search` | recruiter | Search and rank candidates |
| GET / POST | `/api/talent/saved-searches` | recruiter | List / save searches |
| POST | `/api/talent/saved-searches/{id}/run` | recruiter | Run a saved search, marking new results |
| DELETE | `/api/talent/saved-searches/{id}` | recruiter | Delete a saved search |
| GET | `/api/talent/shortlist` | recruiter | Shortlist |
| PUT / DELETE | `/api/talent/shortlist/{candidate_id}` | recruiter | Add or update notes / remove |
| GET | `/api/talent/compare?ids=1,2,3` | recruiter | Compare 2–4 candidates |
| **Practice** | | | |
| GET | `/api/quiz/skills` | student | Skills with questions, suggested unproven skills |
| POST | `/api/quiz/practice` | student | Start a practice quiz (`skills`, `count`, `timed`) |
| GET | `/api/quiz/attempts` | student | Practice history |
| GET | `/api/quiz/attempts/{id}` | student (own) | An attempt (questions while in progress, result when submitted) |
| POST | `/api/quiz/attempts/{id}/submit` | student (own) | Submit answers and get the graded result |
| **Skill tests** | | | |
| GET | `/api/skill-tests/skills` | recruiter | Skills that have questions |
| POST | `/api/skill-tests` | recruiter | Send a test to the student behind a resume |
| GET | `/api/skill-tests/sent` | recruiter | Tests this recruiter sent |
| GET | `/api/skill-tests/candidate/{id}` | recruiter | Tests sent to this student |
| GET | `/api/skill-tests/{id}/result` | recruiter (sender) | Full graded test |
| DELETE | `/api/skill-tests/{id}` | recruiter (sender) | Cancel before it starts |
| GET | `/api/skill-tests/mine` | student | Tests received |
| POST | `/api/skill-tests/{id}/start` | student (receiver) | Start (or resume) the test |
| **Notifications** | | | |
| GET | `/api/notifications` | signed in | Unread count and latest 30 |
| POST | `/api/notifications/{id}/read` | signed in | Mark one as read |
| POST | `/api/notifications/read-all` | signed in | Mark all as read |
| **Admin** | | | |
| GET | `/api/admin/recruiters` | admin | Recruiter accounts and their status |
| PUT | `/api/admin/recruiters/{user_id}` | admin | Approve or reject (`{"status": ...}`) |
| **Earlier prototype endpoints** | | | |
| POST | `/score` | recruiter | Score a username's skills directly (no database) |
| GET | `/github/{username}/repos` | recruiter | Raw repository list |
| GET | `/github/{username}/{repo}/fingerprint` | recruiter | Raw fingerprint of one repository |
