# Iterations 3–4: Technology Fingerprint Engine and Evidence Scoring

**Dates:** 10–11 October 2026
**Goal (proposal):** dependency/config detection rules for the initial technology set; a
transparent scoring engine with explained classifications.

## Completed
- [x] Scoring fix: the "original repository" and "recently updated" bonuses only count on
      repositories that actually show the skill (otherwise every claimed skill got 40 free points)
- [x] Analyze GitHub evidence from the candidate report page; results saved to the database
      (scores, evidence, interview questions)
- [x] Whole-repository scan (every folder, not just the root), with language and database detection
      (drivers and `docker-compose` images)
- [x] Skill catalog (`skills_catalog.json`): 46 skills in 8 categories with aliases, rules and
      interview questions, validated at startup
- [x] "Not checkable on GitHub" verdict for concepts and offline tools instead of an unfair 0/100
- [x] Other repositories supporting each skill are listed
- [x] CI runs on pull requests into any branch

## Scoring as delivered
Fingerprint 40 + language 20 + not a fork 20 + updated in the last 12 months 20; best single
repository counts; Strong ≥ 70, Good 40–69, Needs Verification < 40. See
[docs/scoring.md](../docs/scoring.md).

## Blockers / notes
- An analysis makes up to ~50 GitHub API calls; without a token GitHub allows 60 per hour, so a
  `GITHUB_TOKEN` is needed for demos.

## Next iteration preview
Use the analysis results for students (portfolio, resume lines) and give the frontend a proper
design.
