# Architecture

## System

```mermaid
flowchart LR
    S([Student]) --> FE
    R([Recruiter]) --> FE
    A([Admin]) --> FE
    V([Visitor]) -->|public portfolio /p/link| FE

    subgraph Vercel
        FE["React + TypeScript + Tailwind<br/>single-page app"]
    end

    subgraph Render
        API["FastAPI backend"]
        DB[("PostgreSQL")]
    end

    FE -->|"REST + session JWT"| API
    FE -->|"Google sign-in popup"| G["Google Identity Services"]
    API -->|"verify ID token"| G
    API -->|"repos, trees, manifests, commits"| GH["GitHub REST API"]
    API <--> DB
```

- **Frontend** (`code/frontend`): pages in `src/pages`, shared parts in `src/components`, API calls
  and types in `src/lib`. `lib/api.ts` adds the session token to every request; `AuthContext`
  remembers the signed-in user; `App.tsx` maps URLs to pages and checks roles.
- **Backend** (`code/backend/app`): each feature has a **router** (HTTP, who is calling, database
  reads and writes) and a **service** with the logic, most of it pure functions tested without a
  database.
- **Database**: PostgreSQL through SQLAlchemy. New tables are created on startup
  (`create_all`); new columns on existing tables are added by `database.ensure_columns()`.

## Backend structure

```mermaid
flowchart TB
    subgraph Routers["app/routers"]
        auth & resume & candidates & portfolio & resume_bullets
        talent & job_fit & quiz & skill_tests & notifications & admin
    end
    subgraph Services["app/services"]
        resume_parser & resume_projects & project_links
        github_client & fingerprinting & tech_rules & scoring & analysis
        portfolio_s["portfolio"] & resume_bullets_s["resume_bullets"] & talent_search
        job_fit_s["job_fit"] & roadmap & quiz_s["quiz"] & visibility & approval & notifications_s["notifications"]
    end
    Data["skills_catalog.json<br/>question_bank.json"]
    Routers --> Services
    Services --> Data
    Routers --> Models["models.py (SQLAlchemy)"]
```

| Service | Responsibility |
|---|---|
| `resume_parser`, `resume_projects` | Text from the PDF (pdfplumber), name (spaCy), skills, GitHub link, projects with tech stack and dates |
| `github_client` | GitHub REST calls, in-memory cache, rate-limit detection |
| `fingerprinting`, `tech_rules` | Scan a repository's files and manifests and decide which catalog skills it shows |
| `scoring`, `analysis` | Score each claimed skill, pick reasons and supporting repositories, write interview questions |
| `project_links` | Match resume projects to repositories by name |
| `portfolio`, `resume_bullets` | Public portfolio content; resume lines, optionally tailored to a job description |
| `talent_search` | Recruiter search, ranking, comparison |
| `job_fit`, `roadmap` | Fit of each resume to a job or role; skill gap roadmap |
| `quiz` | Question picking, option shuffling, grading |
| `visibility`, `approval`, `notifications` | Which resume recruiters see; recruiter approval; in-app notifications |

## How an analysis runs

```mermaid
sequenceDiagram
    actor U as Student or recruiter
    participant FE as Frontend
    participant API as Backend
    participant GH as GitHub
    participant DB as PostgreSQL

    U->>FE: Analyze GitHub evidence
    FE->>API: POST /api/candidates/{id}/analyze
    API->>DB: load candidate, resume PDF, claimed skills
    API->>API: re-read projects from the PDF
    API->>GH: list repositories (cached 10 min)
    loop 10 most recently updated repositories
        API->>GH: file tree, manifests, commit count (cached until next push)
        API->>API: fingerprint: which skills this repository shows
    end
    API->>API: score each claimed skill (best repository counts)
    API->>DB: save scores, evidence, interview questions, repository details, project links
    API->>DB: notification "analysis ready" (+ saved-search matches)
    API-->>FE: report
    FE-->>U: verdict, reasons and evidence per skill
```

If GitHub's hourly limit runs out, the analysis stops with "try again in about N minutes" rather
than treating unreadable repositories as empty.

## Data model

```mermaid
erDiagram
    users ||--o{ candidates : uploads
    users ||--o{ saved_searches : saves
    users ||--o{ shortlist_entries : shortlists
    users ||--o{ notifications : receives
    users ||--o{ quiz_attempts : takes
    users ||--o{ skill_tests : "sends / receives"
    candidates ||--o{ candidate_skills : claims
    skills ||--o{ candidate_skills : ""
    candidates ||--o{ repositories : has
    repositories ||--o| repository_details : "details"
    candidates ||--o{ evidence : ""
    skills ||--o{ evidence : ""
    repositories ||--o{ evidence : supports
    candidates ||--o{ projects : lists
    candidates ||--o{ interview_questions : ""
    skills ||--o{ interview_questions : ""
    candidates ||--o| portfolios : publishes
    candidates ||--o{ shortlist_entries : ""
    quiz_attempts ||--o| skill_tests : "answers"

    users {
        int user_id PK
        string email
        string role "student / recruiter"
        string recruiter_status "pending / approved / rejected"
        int visible_candidate_id "resume recruiters see"
    }
    candidates {
        int candidate_id PK
        int user_id FK
        string name
        string github_username
        bytes resume_pdf
    }
    candidate_skills {
        int candidate_id PK
        int skill_id PK
        string status
        int score
    }
    repositories {
        int repo_id PK
        int candidate_id FK
        string repo_name
        bool is_fork
    }
    evidence {
        int evidence_id PK
        string evidence_type
        string description
        int weight
    }
    quiz_attempts {
        int attempt_id PK
        int user_id FK
        string kind "practice / test"
        int score
    }
    skill_tests {
        int test_id PK
        int recruiter_id FK
        int student_id FK
        int attempt_id FK
    }
```

Other tables: `repository_details` (technologies, signals, push date), `projects` (title,
description, tech stack, period), `interview_questions`, `portfolios` (public link, headline),
`saved_searches`, `shortlist_entries` (private notes), `notifications`.

## Access rules

- Sign-in: Google ID token verified on the backend; `@thapar.edu` → student, other emails →
  recruiter (pending until approved, unless the domain is in `RECRUITER_AUTO_APPROVE_DOMAINS`).
  Admins are listed in `ADMIN_EMAILS`.
- Students see only their own uploads. Recruiters see each student's one visible resume.
- Practice results are private to the student; skill test results go to the recruiter who sent
  the test.
- Public portfolio pages need no sign-in and show only what the student published.
