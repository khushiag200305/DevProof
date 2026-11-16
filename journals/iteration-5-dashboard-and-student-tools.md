# Iteration 5: Dashboard, interview support and student tools

**Dates:** 30 October – 9 November 2026
**Goal (proposal):** candidate dashboard, skill detail views, interview question generation.

## Completed
- [x] Repository details saved per analysis (technologies, project signals, push date)
- [x] Public **portfolio** page (`/p/<link>`) with publish controls and a headline (30 Oct)
- [x] **Resume bullet** generator, optionally tailored to a job description (30 Oct)
- [x] Resume projects parsed properly (title, tech stack, dates, bullets) and linked to GitHub
      repositories (2 Nov)
- [x] Candidate report reworked into tabs (Skills / Projects / Portfolio & resume lines) with
      compact, expandable skill rows (2 Nov)
- [x] Frontend redesign with light and dark mode; after feedback ("too vertical", "childish",
      "looks AI generated") settled on a flat, report-style theme with a GitHub-style activity
      grid on the sign-in page (2–8 Nov)
- [x] Recruiter **talent search** with saved searches, shortlist with notes, and compare (9 Nov)
- [x] Students can delete an upload and choose which resume is **visible to recruiters**; each
      person appears once in search (9 Nov)
- [x] **Match a job**: which of a student's resumes fits a pasted job description (9 Nov)
- [x] Demo data script with 20 clearly marked fictional students (9 Nov)

## Blockers / notes
- Stored resume paths broke when the project folder was moved; the analysis now also looks for the
  file by name in the uploads folder.
- 8 Nov: the GitHub repository was recreated (same name, full history kept) to remove a stale
  contributor entry GitHub Support couldn't fix on a free account. The old one is `DevProof-old`;
  pull request numbers restarted at #1.
- Testing showed one account had uploaded another team member's resume; each student should upload
  from their own Thapar account.

## Next iteration preview
Recruiter approval, notifications, the quiz system, and deployment.
