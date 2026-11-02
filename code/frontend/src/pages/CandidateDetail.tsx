import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { Hero } from "../components/Hero";
import { ArrowLeftIcon, ChatIcon, ExternalIcon, GitHubIcon, SparkIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { PortfolioPanel } from "../components/PortfolioPanel";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiGet, apiPost } from "../lib/api";

interface SupportingRepo {
  repo: string;
  score: number;
}

interface SkillEntry {
  skill_name: string;
  category: string;
  checkable: boolean;
  status: string | null;
  score: number | null;
  reasons: string[];
  interview_question: string | null;
  supporting_repos: SupportingRepo[];
}

interface ProjectEntry {
  project_name: string;
  description: string | null;
  tech_stack: string[];
  period: string | null;
  bullets: string[];
  repo: { name: string; url: string } | null;
}

interface CandidateDetailData {
  candidate_id: number;
  name: string | null;
  email: string | null;
  github_username: string | null;
  created_at: string;
  skill_count: number;
  repos_analyzed: number;
  analyzed: boolean;
  skills: SkillEntry[];
  projects: ProjectEntry[];
}

/** Badge and score-bar colours for an evidence status. */
function statusTone(status: string | null): { badge: string; bar: string } {
  const s = status?.toLowerCase() ?? "";
  if (!status) return { badge: "bg-slate-500/10 text-ink-mute dark:text-slate-400", bar: "bg-slate-300" };
  if (s.includes("not checkable"))
    return { badge: "bg-sky-500/10 text-sky-700 dark:text-sky-300", bar: "bg-sky-400" };
  if (s.includes("strong"))
    return { badge: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300", bar: "bg-emerald-500" };
  if (s.includes("good"))
    return { badge: "bg-sun-400/25 text-amber-700 dark:text-sun-300", bar: "bg-sun-400" };
  return { badge: "bg-pop-500/10 text-pop-600 dark:text-pop-400", bar: "bg-pop-500" };
}

/** One colour per category tile, cycled in order. Full class names so Tailwind keeps them. */
const ACCENTS = [
  { tile: "from-brand-500 to-brand-700", dot: "bg-brand-500", ring: "ring-brand-500" },
  { tile: "from-pop-400 to-pop-600", dot: "bg-pop-500", ring: "ring-pop-500" },
  { tile: "from-sun-300 to-amber-500", dot: "bg-sun-400", ring: "ring-sun-400" },
  { tile: "from-emerald-400 to-teal-600", dot: "bg-emerald-500", ring: "ring-emerald-500" },
  { tile: "from-sky-400 to-indigo-500", dot: "bg-sky-500", ring: "ring-sky-500" },
  { tile: "from-fuchsia-400 to-purple-600", dot: "bg-fuchsia-500", ring: "ring-fuchsia-500" },
];

interface SkillGroup {
  category: string;
  skills: SkillEntry[];
}

/** Skills arrive sorted by category (resume-style order); group neighbours. */
function groupByCategory(skills: SkillEntry[]): SkillGroup[] {
  const groups: SkillGroup[] = [];
  for (const skill of skills) {
    const last = groups[groups.length - 1];
    if (last && last.category === skill.category) {
      last.skills.push(skill);
    } else {
      groups.push({ category: skill.category, skills: [skill] });
    }
  }
  return groups;
}

function isBacked(s: SkillEntry): boolean {
  return s.status === "Strong Evidence" || s.status === "Good Evidence";
}

/** e.g. "2 of 3 backed by GitHub" or "Checked in interview" for concept-only groups. */
function groupSummary(group: SkillGroup): string | null {
  const checkable = group.skills.filter((s) => s.checkable);
  if (checkable.length === 0) return "Checked in interview";
  if (checkable.some((s) => s.status === null)) return null;
  const backed = checkable.filter(isBacked).length;
  return `${backed} of ${checkable.length} backed by GitHub`;
}

/** Ring showing the share of checkable skills backed by GitHub. */
function EvidenceRing({ percent }: { percent: number }) {
  const r = 44;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative h-32 w-32">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="white"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - percent / 100)}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-extrabold leading-none">{percent}%</span>
        <span className="mt-1 text-[11px] font-semibold text-white/80">backed</span>
      </div>
    </div>
  );
}

function SkillCard({ skill: s }: { skill: SkillEntry }) {
  const tone = statusTone(s.status);
  return (
    <li className="tile flex flex-col p-4 transition hover:border-brand-200 hover:shadow-md dark:hover:border-night-600">
      <div className="flex items-start justify-between gap-3">
        <span className="font-display text-lg font-bold leading-tight">{s.skill_name}</span>
        <span className={`chip shrink-0 py-1 ${tone.badge}`}>
          {s.status ?? "Pending Analysis"}
          {s.score !== null && ` · ${s.score}/100`}
        </span>
      </div>
      {s.score !== null && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600" aria-hidden="true">
          <div className={`bar-fill h-full rounded-full ${tone.bar}`} style={{ width: `${Math.max(3, s.score)}%` }} />
        </div>
      )}
      {s.reasons.length > 0 &&
        (s.checkable ? (
          <ul className="mt-3 space-y-1 text-sm text-ink-soft dark:text-slate-300">
            {s.reasons.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${tone.bar}`} aria-hidden="true" />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted mt-3 text-sm italic">{s.reasons[0]}</p>
        ))}
      {s.supporting_repos.length > 0 && (
        <p className="muted mt-3 text-xs">
          <span className="font-semibold text-ink-soft dark:text-slate-300">Also supported by:</span>{" "}
          {s.supporting_repos.map((r) => `${r.repo} (${r.score})`).join(", ")}
        </p>
      )}
      {s.interview_question && (
        <p className="mt-3 flex gap-2 rounded-xl bg-brand-600/10 px-3 py-2.5 text-sm text-brand-800 dark:bg-brand-500/15 dark:text-brand-100">
          <ChatIcon className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <span className="font-semibold">Suggested interview question:</span> {s.interview_question}
          </span>
        </p>
      )}
    </li>
  );
}

function ProjectCard({ project: p, analyzed, index }: { project: ProjectEntry; analyzed: boolean; index: number }) {
  const accent = ACCENTS[index % ACCENTS.length];
  return (
    <li aria-label={p.project_name} className="tile relative flex flex-col overflow-hidden p-5">
      <span className={`absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r ${accent.tile}`} aria-hidden="true" />
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
        <span className="font-display text-lg font-bold leading-snug">{p.project_name}</span>
        {p.period && <span className="muted shrink-0 text-xs font-medium">{p.period}</span>}
      </div>
      {p.tech_stack.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.tech_stack.map((t) => (
            <span key={t} className="chip bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
              {t}
            </span>
          ))}
        </div>
      )}
      {p.bullets.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-sm text-ink-soft dark:text-slate-300">
          {p.bullets.map((b) => (
            <li key={b} className="flex gap-2">
              <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${accent.dot}`} aria-hidden="true" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
      {analyzed && (
        <p className="mt-auto pt-4 text-sm">
          {p.repo ? (
            <a
              href={p.repo.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700 dark:bg-white dark:text-ink dark:hover:bg-brand-100"
            >
              <GitHubIcon className="h-3.5 w-3.5" />
              GitHub: {p.repo.name}
              <ExternalIcon className="h-3 w-3" />
            </a>
          ) : (
            <span className="muted text-xs">No matching GitHub repository found</span>
          )}
        </p>
      )}
    </li>
  );
}

export function CandidateDetail() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const { user } = useAuth();
  const homePath = user?.role === "recruiter" ? "/dashboard" : "/upload";
  const [candidate, setCandidate] = useState<CandidateDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analysisRuns, setAnalysisRuns] = useState(0);
  const [openCategory, setOpenCategory] = useState<string | null>(null);

  useEffect(() => {
    if (!candidateId) return;
    setLoading(true);
    apiGet<CandidateDetailData>(`/api/candidates/${candidateId}`)
      .then(setCandidate)
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 403
            ? "You don't have access to this candidate's report."
            : err instanceof ApiError && err.status === 404
              ? "Candidate not found."
              : "Could not load this candidate."
        )
      )
      .finally(() => setLoading(false));
  }, [candidateId]);

  const runAnalysis = async () => {
    if (!candidateId) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const updated = await apiPost<CandidateDetailData>(
        `/api/candidates/${candidateId}/analyze`
      );
      setCandidate(updated);
      setAnalysisRuns((n) => n + 1);
    } catch (err) {
      setAnalyzeError(
        err instanceof ApiError ? err.message : "Analysis failed. Please try again."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const groups = candidate ? groupByCategory(candidate.skills) : [];
  const shownGroups = openCategory ? groups.filter((g) => g.category === openCategory) : groups;
  const checkable = candidate?.skills.filter((s) => s.checkable) ?? [];
  const backedPercent =
    candidate?.analyzed && checkable.length > 0
      ? Math.round((checkable.filter(isBacked).length / checkable.length) * 100)
      : null;
  const displayName = candidate ? (candidate.name ?? `Candidate #${candidate.candidate_id}`) : "";

  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        {!candidate && (
          <Link to={homePath} className="link inline-flex items-center gap-1.5 text-sm">
            <ArrowLeftIcon className="h-4 w-4" /> Back
          </Link>
        )}

        {loading && <p className="muted mt-6 text-sm">Loading...</p>}
        {error && <p className="alert mt-6">{error}</p>}

        {candidate && (
          <>
            <Hero
              seed={displayName}
              aside={
                <div className="flex items-center gap-5 lg:flex-col lg:items-end">
                  {backedPercent !== null && <EvidenceRing percent={backedPercent} />}
                  {candidate.github_username ? (
                    <button onClick={runAnalysis} disabled={analyzing} className="btn-light">
                      <SparkIcon className={`h-4 w-4 ${analyzing ? "animate-spin" : ""}`} />
                      {analyzing
                        ? "Analyzing GitHub..."
                        : candidate.analyzed
                          ? "Re-run analysis"
                          : "Analyze GitHub evidence"}
                    </button>
                  ) : (
                    <p className="rounded-full bg-white/15 px-4 py-2 text-sm font-medium ring-1 ring-white/30">
                      No GitHub username on this resume
                    </p>
                  )}
                </div>
              }
            >
              <Link
                to={homePath}
                className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-sm font-semibold text-white ring-1 ring-white/25 transition hover:bg-white/25"
              >
                <ArrowLeftIcon className="h-4 w-4" /> Back
              </Link>
              <div className="mt-5 flex items-center gap-4">
                <Avatar name={displayName} className="h-16 w-16 text-2xl ring-4 ring-white/30 sm:h-20 sm:w-20 sm:text-3xl" />
                <div className="min-w-0">
                  <h1 className="break-words text-3xl font-extrabold leading-tight sm:text-5xl">
                    {displayName}
                  </h1>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-white/85">
                    {candidate.email && <span>{candidate.email}</span>}
                    {candidate.github_username && (
                      <a
                        href={`https://github.com/${candidate.github_username}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-semibold text-white underline-offset-4 hover:underline"
                      >
                        <GitHubIcon className="h-3.5 w-3.5" />@{candidate.github_username}
                      </a>
                    )}
                    <span>Uploaded {new Date(candidate.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </Hero>

            {analyzeError && <p className="alert mt-4">{analyzeError}</p>}

            <section className="panel mt-6" aria-labelledby="skills-heading">
              <h2 id="skills-heading" className="text-2xl font-bold">
                Claimed skills
              </h2>
              <p className="muted mt-1 text-sm">
                {candidate.analyzed
                  ? `Scored against ${candidate.repos_analyzed} public GitHub ${
                      candidate.repos_analyzed === 1 ? "repository" : "repositories"
                    }. Every score lists the evidence behind it.`
                  : "Run the analysis to check each skill against public GitHub evidence."}
              </p>

              {candidate.skills.length === 0 ? (
                <p className="muted mt-4 text-sm">No skills detected.</p>
              ) : (
                <>
                  {groups.length > 1 && (
                    <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
                      <button
                        onClick={() => setOpenCategory(null)}
                        aria-pressed={openCategory === null}
                        className={`rounded-2xl border-2 p-4 text-left transition hover:-translate-y-0.5 ${
                          openCategory === null
                            ? "border-ink bg-ink text-white dark:border-white dark:bg-white dark:text-ink"
                            : "border-slate-200 hover:border-ink/40 dark:border-night-600 dark:hover:border-slate-400"
                        }`}
                      >
                        <span className="block font-display text-base font-bold">All skills</span>
                        <span className="mt-1 block text-xs opacity-75">{candidate.skills.length} on the resume</span>
                      </button>
                      {groups.map((g, i) => {
                        const accent = ACCENTS[i % ACCENTS.length];
                        const open = openCategory === g.category;
                        const groupCheckable = g.skills.filter((s) => s.checkable);
                        const backed = groupCheckable.filter(isBacked).length;
                        return (
                          <button
                            key={g.category}
                            onClick={() => setOpenCategory(open ? null : g.category)}
                            aria-pressed={open}
                            className={`group relative overflow-hidden rounded-2xl bg-gradient-to-br p-4 text-left text-white shadow-md transition hover:-translate-y-1 hover:shadow-xl ${accent.tile} ${
                              open ? `ring-4 ring-offset-2 ring-offset-white dark:ring-offset-night-800 ${accent.ring} scale-[1.02]` : ""
                            } ${openCategory && !open ? "opacity-60 hover:opacity-100" : ""}`}
                          >
                            <span className="absolute -right-3 -top-3 font-display text-6xl font-extrabold opacity-20 transition-transform group-hover:scale-110">
                              {g.skills.length}
                            </span>
                            <span className="relative block font-display text-base font-bold leading-tight">
                              {g.category}
                            </span>
                            <span className="relative mt-1 block text-xs font-medium text-white/85">
                              {groupCheckable.length === 0
                                ? "Concepts"
                                : candidate.analyzed
                                  ? `${backed}/${groupCheckable.length} proven`
                                  : `${g.skills.length} to check`}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <div key={openCategory ?? "all"} className="mt-6 space-y-8">
                    {shownGroups.map((group) => {
                      const summary = groupSummary(group);
                      const accent = ACCENTS[groups.indexOf(group) % ACCENTS.length];
                      return (
                        <section key={group.category} aria-label={group.category} className="rise">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h3 className="flex items-center gap-2.5 text-xl font-bold">
                              <span className={`h-3 w-3 rounded-full ${accent.dot}`} aria-hidden="true" />
                              {group.category}
                            </h3>
                            {summary && (
                              <span className="chip bg-slate-500/10 py-1 text-ink-soft dark:text-slate-300">
                                {summary}
                              </span>
                            )}
                          </div>
                          <ul className="mt-3 grid gap-3 md:grid-cols-2">
                            {group.skills.map((s) => (
                              <SkillCard key={s.skill_name} skill={s} />
                            ))}
                          </ul>
                        </section>
                      );
                    })}
                  </div>
                </>
              )}
            </section>

            {candidate.projects.length > 0 && (
              <section className="panel mt-6" aria-labelledby="projects-heading">
                <h2 id="projects-heading" className="text-2xl font-bold">
                  Projects on the resume
                </h2>
                <p className="muted mt-1 text-sm">
                  {candidate.analyzed
                    ? "Each project is linked to its GitHub repository when the names match."
                    : "Run the analysis to link each project to its GitHub repository."}
                </p>
                <ul className="mt-5 grid gap-4 md:grid-cols-2">
                  {candidate.projects.map((p, i) => (
                    <ProjectCard key={`${p.project_name}-${i}`} project={p} analyzed={candidate.analyzed} index={i} />
                  ))}
                </ul>
              </section>
            )}

            {user?.role === "student" && (
              <div className="mt-6 grid gap-6 lg:grid-cols-3">
                {candidate.analyzed && (
                  <div className="relative flex flex-col justify-between gap-5 overflow-hidden rounded-2xl bg-gradient-to-br from-pop-500 via-pop-400 to-sun-400 p-6 text-white shadow-lg shadow-pop-500/20 sm:p-7">
                    <SparkIcon className="absolute -right-4 -top-4 h-28 w-28 opacity-20" />
                    <div className="relative">
                      <h2 className="text-2xl font-extrabold">Resume bullet ideas</h2>
                      <p className="mt-2 text-sm text-white/90">
                        Resume lines written from your repositories, tailored to a job if you paste one.
                      </p>
                    </div>
                    <Link
                      to={`/candidate/${candidate.candidate_id}/bullets`}
                      className="btn-light relative self-start text-pop-600"
                    >
                      Get resume lines
                    </Link>
                  </div>
                )}
                <div className={candidate.analyzed ? "lg:col-span-2" : "lg:col-span-3"}>
                  <PortfolioPanel candidateId={candidate.candidate_id} refreshKey={analysisRuns} />
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
