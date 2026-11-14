import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { Hero } from "../components/Hero";
import { ArrowLeftIcon, ChatIcon, ChevronIcon, ExternalIcon, EyeIcon, GitHubIcon, SparkIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { PortfolioPanel } from "../components/PortfolioPanel";
import { SkillTestsPanel } from "../components/SkillTestsPanel";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiGet, apiPost, apiPut } from "../lib/api";
import { latestTestScores, type SkillTest, type SkillTestScore } from "../lib/skillTests";

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
  /** Is this the resume the student made visible to recruiters? */
  visible_to_recruiters?: boolean;
  visible_candidate_id?: number | null;
  /** Does a student account own this resume (so it can receive skill tests)? */
  has_account?: boolean;
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

/** One colour per skill category, cycled in order. Full class names so Tailwind keeps them. */
const ACCENTS = [
  { dot: "bg-brand-600" },
  { dot: "bg-sky-700" },
  { dot: "bg-sun-400" },
  { dot: "bg-pop-500" },
  { dot: "bg-slate-500" },
  { dot: "bg-teal-600" },
]

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
    <div className="relative h-28 w-28">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="9" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="#45bb6a"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - percent / 100)}
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-bold leading-none">{percent}%</span>
        <span className="mt-1 text-[11px] font-semibold text-white/80">on GitHub</span>
      </div>
    </div>
  );
}

/** A skill as one compact row; clicking it opens the evidence underneath. */
function testTone(t: SkillTestScore): string {
  const ratio = t.total ? t.correct / t.total : 0;
  if (ratio >= 0.7) return "border-emerald-500/40 text-emerald-700 dark:text-emerald-300";
  if (ratio >= 0.4) return "border-sun-400/60 text-amber-700 dark:text-sun-300";
  return "border-pop-500/40 text-pop-600 dark:text-pop-400";
}

function SkillRow({
  skill: s,
  open,
  onToggle,
  test,
}: {
  skill: SkillEntry;
  open: boolean;
  onToggle: () => void;
  test?: SkillTestScore;
}) {
  const tone = statusTone(s.status);
  return (
    <li className="border-t border-slate-100 first:border-t-0 dark:border-night-600">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="group flex w-full items-center gap-3 py-3 text-left"
      >
        <span className="min-w-0 flex-1 truncate font-semibold group-hover:text-brand-700 dark:group-hover:text-brand-300">
          {s.skill_name}
        </span>
        {s.score !== null && (
          <span className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600 sm:block" aria-hidden="true">
            <span className={`bar-fill block h-full rounded-full ${tone.bar}`} style={{ width: `${Math.max(4, s.score)}%` }} />
          </span>
        )}
        {test && (
          <span
            className={`chip shrink-0 border bg-transparent py-1 tabular-nums ${testTone(test)}`}
            title="Latest skill test score"
          >
            Test {test.correct}/{test.total}
          </span>
        )}
        <span className={`chip shrink-0 py-1 ${tone.badge}`}>
          {s.status ?? "Pending Analysis"}
          {s.score !== null && ` · ${s.score}/100`}
        </span>
        <ChevronIcon
          className={`h-4 w-4 shrink-0 text-ink-mute transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      <div className={open ? "rise pb-4" : "hidden"}>
        {test && (
          <p className="mb-2 text-sm">
            <span className="font-semibold">Skill test:</span> {test.correct} of {test.total} correct
            {test.date ? ` on ${new Date(test.date).toLocaleDateString()}` : ""}
            {test.late ? " (submitted after the time limit)" : ""}.
          </p>
        )}
        {s.reasons.length > 0 &&
          (s.checkable ? (
            <ul className="space-y-1 text-sm text-ink-soft dark:text-slate-300">
              {s.reasons.map((reason) => (
                <li key={reason} className="flex gap-2">
                  <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${tone.bar}`} aria-hidden="true" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted text-sm italic">{s.reasons[0]}</p>
          ))}
        {s.supporting_repos.length > 0 && (
          <p className="muted mt-2 text-xs">
            <span className="font-semibold text-ink-soft dark:text-slate-300">Also supported by:</span>{" "}
            {s.supporting_repos.map((r) => `${r.repo} (${r.score})`).join(", ")}
          </p>
        )}
        {s.interview_question && (
          <p className="mt-3 flex gap-2 rounded-xl bg-brand-600/[0.07] px-3 py-2.5 text-sm text-brand-900 dark:bg-brand-500/10 dark:text-brand-100">
            <ChatIcon className="mt-0.5 h-4 w-4 shrink-0 text-brand-600 dark:text-brand-300" />
            <span>
              <span className="font-semibold">Suggested interview question:</span> {s.interview_question}
            </span>
          </p>
        )}
        {s.reasons.length === 0 && !s.interview_question && (
          <p className="muted text-sm">Run the analysis to see the evidence for this skill.</p>
        )}
      </div>
    </li>
  );
}

function ProjectCard({ project: p, analyzed, index }: { project: ProjectEntry; analyzed: boolean; index: number }) {
  const accent = ACCENTS[index % ACCENTS.length];
  return (
    <li aria-label={p.project_name} className="panel flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <span className="font-display text-xl font-bold leading-snug">{p.project_name}</span>
        {p.period && (
          <span className="chip shrink-0 bg-slate-500/10 text-ink-soft dark:text-slate-300">{p.period}</span>
        )}
      </div>
      {p.tech_stack.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.tech_stack.map((t) => (
            <span key={t} className="chip bg-brand-600/10 text-brand-700 dark:bg-brand-500/15 dark:text-brand-200">
              {t}
            </span>
          ))}
        </div>
      )}
      {p.bullets.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm text-ink-soft dark:text-slate-300">
          {p.bullets.map((b) => (
            <li key={b} className="flex gap-2.5">
              <span className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${accent.dot}`} aria-hidden="true" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
      {analyzed && (
        <p className="mt-auto pt-5 text-sm">
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

type Tab = "skills" | "projects" | "share" | "tests";

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
  const [category, setCategory] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("skills");
  const [openSkills, setOpenSkills] = useState<Set<string>>(new Set());
  const [testScores, setTestScores] = useState<Record<string, SkillTestScore>>({});

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

  // Skill test scores shown beside each verdict: the recruiter's own tests,
  // or every test a student has taken. Reloaded when coming back to Skills.
  const canHaveTests = !!candidate && (user?.role === "student" || !!candidate.has_account);
  useEffect(() => {
    if (!canHaveTests || tab !== "skills" || !candidateId) return;
    const path = user?.role === "student" ? "/api/skill-tests/mine" : `/api/skill-tests/candidate/${candidateId}`;
    apiGet<SkillTest[]>(path)
      .then((t) => setTestScores(latestTestScores(Array.isArray(t) ? t : [])))
      .catch(() => setTestScores({}));
  }, [canHaveTests, tab, candidateId, user?.role]);

  const makeVisible = async () => {
    if (!candidate) return;
    try {
      await apiPut(`/api/candidates/${candidate.candidate_id}/visible`, {});
      setCandidate({ ...candidate, visible_to_recruiters: true, visible_candidate_id: candidate.candidate_id });
    } catch (err) {
      setAnalyzeError(err instanceof ApiError ? err.message : "Could not change which resume recruiters see.");
    }
  };

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

  const toggleSkill = (name: string) =>
    setOpenSkills((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  const groups = candidate ? groupByCategory(candidate.skills) : [];
  const shownGroups = category ? groups.filter((g) => g.category === category) : groups;
  const skills = candidate?.skills ?? [];
  const checkable = skills.filter((s) => s.checkable);
  const backedPercent =
    candidate?.analyzed && checkable.length > 0
      ? Math.round((checkable.filter(isBacked).length / checkable.length) * 100)
      : null;
  const allOpen = skills.length > 0 && skills.every((s) => openSkills.has(s.skill_name));
  const displayName = candidate ? (candidate.name ?? `Candidate #${candidate.candidate_id}`) : "";

  const breakdown = [
    { label: "Strong", count: skills.filter((s) => s.status === "Strong Evidence").length, color: "bg-emerald-500" },
    { label: "Good", count: skills.filter((s) => s.status === "Good Evidence").length, color: "bg-sun-400" },
    { label: "Needs proof", count: skills.filter((s) => s.checkable && s.status !== null && !isBacked(s)).length, color: "bg-pop-500" },
    { label: "Interview only", count: skills.filter((s) => !s.checkable).length, color: "bg-sky-400" },
    { label: "Not checked yet", count: skills.filter((s) => s.checkable && s.status === null).length, color: "bg-slate-300 dark:bg-slate-500" },
  ].filter((b) => b.count > 0);

  const tabs: { id: Tab; label: string; count?: number }[] = candidate
    ? [
        { id: "skills", label: "Skills", count: skills.length },
        ...(candidate.projects.length > 0
          ? [{ id: "projects" as Tab, label: "Projects", count: candidate.projects.length }]
          : []),
        ...(user?.role === "student" ? [{ id: "share" as Tab, label: "Portfolio & resume lines" }] : []),
        ...(user?.role === "recruiter" && candidate.has_account ? [{ id: "tests" as Tab, label: "Skill tests" }] : []),
      ]
    : [];

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
                <div className="flex items-center gap-5">
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
                <Avatar name={displayName} className="h-16 w-16 text-2xl ring-4 ring-white/25" />
                <div className="min-w-0">
                  <h1 className="break-words text-3xl font-bold leading-tight sm:text-4xl">
                    {displayName}
                  </h1>
                  <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-white/85">
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

            {candidate.visible_to_recruiters !== undefined &&
              (user?.role === "student" ? (
                <div
                  className={`mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
                    candidate.visible_to_recruiters
                      ? "border-brand-600/30 bg-brand-600/5"
                      : "border-slate-200 bg-white dark:border-night-600 dark:bg-night-800"
                  }`}
                >
                  <p className="flex items-center gap-2 font-medium">
                    <EyeIcon className={`h-4 w-4 ${candidate.visible_to_recruiters ? "text-brand-600 dark:text-brand-300" : "text-ink-mute"}`} />
                    {candidate.visible_to_recruiters
                      ? "Recruiters see this resume"
                      : "Recruiters see a different resume"}
                  </p>
                  {!candidate.visible_to_recruiters && (
                    <button onClick={makeVisible} className="btn-primary px-3 py-1.5 text-xs">
                      Make this one visible
                    </button>
                  )}
                </div>
              ) : (
                !candidate.visible_to_recruiters &&
                candidate.visible_candidate_id && (
                  <p className="mt-4 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm dark:border-night-600 dark:bg-night-800">
                    This student has chosen a different resume for recruiters.{" "}
                    <Link to={`/candidate/${candidate.visible_candidate_id}`} className="link">
                      Open it
                    </Link>
                  </p>
                )
              ))}

            <div role="tablist" aria-label="Report sections" className="mt-6 flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-night-600">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={tab === t.id}
                  onClick={() => setTab(t.id)}
                  className={`-mb-px flex shrink-0 items-center gap-2 border-b-[3px] px-4 py-3 text-sm font-semibold transition ${
                    tab === t.id
                      ? "border-brand-600 text-ink dark:border-brand-400 dark:text-white"
                      : "border-transparent text-ink-mute hover:text-ink dark:text-slate-400 dark:hover:text-white"
                  }`}
                >
                  {t.label}
                  {t.count !== undefined && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        tab === t.id
                          ? "bg-brand-600 text-white"
                          : "bg-slate-200/70 text-ink-soft dark:bg-night-600 dark:text-slate-300"
                      }`}
                    >
                      {t.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Skills: summary and category filter on the left, skill rows on the right. */}
            <div role="tabpanel" className={tab === "skills" ? "mt-6 grid gap-6 lg:grid-cols-[17rem_1fr]" : "hidden"}>
              <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
                <div className="panel p-5 sm:p-5">
                  <h2 className="text-lg font-bold">Claimed skills</h2>
                  <p className="muted mt-1 text-sm">
                    {candidate.analyzed
                      ? `Scored against ${candidate.repos_analyzed} public GitHub ${
                          candidate.repos_analyzed === 1 ? "repository" : "repositories"
                        }. Every score lists the evidence behind it.`
                      : "Run the analysis to check each skill against public GitHub evidence."}
                  </p>
                  {skills.length > 0 && (
                    <>
                      <div className="mt-4 flex h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600" aria-hidden="true">
                        {breakdown.map((b) => (
                          <span key={b.label} className={`bar-fill ${b.color}`} style={{ width: `${(b.count / skills.length) * 100}%` }} />
                        ))}
                      </div>
                      <ul className="mt-3 space-y-1.5 text-sm">
                        {breakdown.map((b) => (
                          <li key={b.label} className="flex items-center gap-2">
                            <span className={`h-2.5 w-2.5 rounded-full ${b.color}`} aria-hidden="true" />
                            <span className="flex-1 text-ink-soft dark:text-slate-300">{b.label}</span>
                            <span className="font-semibold tabular-nums">{b.count}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>

                {groups.length > 1 && (
                  <nav aria-label="Skill categories" className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:block lg:rounded-2xl lg:border lg:border-slate-200/70 lg:bg-white lg:p-2 lg:dark:border-night-600 lg:dark:bg-night-800">
                    {[{ category: null as string | null, label: "All categories", count: skills.length, dot: "bg-ink dark:bg-white" }, ...groups.map((g, i) => ({
                      category: g.category as string | null,
                      label: g.category,
                      count: g.skills.length,
                      dot: ACCENTS[i % ACCENTS.length].dot,
                    }))].map((item) => {
                      const active = category === item.category;
                      return (
                        <button
                          key={item.label}
                          onClick={() => setCategory(item.category)}
                          aria-pressed={active}
                          className={`flex shrink-0 items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-semibold transition lg:w-full ${
                            active
                              ? "bg-ink text-white dark:bg-white dark:text-ink"
                              : "bg-white text-ink-soft ring-1 ring-slate-200/70 hover:bg-slate-100 dark:bg-night-800 dark:text-slate-300 dark:ring-night-600 dark:hover:bg-night-700 lg:bg-transparent lg:ring-0 lg:dark:bg-transparent"
                          }`}
                        >
                          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${active ? "bg-white" : item.dot}`} aria-hidden="true" />
                          <span className="truncate lg:flex-1">{item.label}</span>
                          <span className={`text-xs tabular-nums ${active ? "text-white/80" : "text-ink-mute"}`}>{item.count}</span>
                        </button>
                      );
                    })}
                  </nav>
                )}
              </aside>

              <div className="min-w-0">
                {skills.length === 0 ? (
                  <p className="panel muted text-sm">No skills detected.</p>
                ) : (
                  <>
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <p className="muted text-sm">Click a skill to see the evidence behind its score.</p>
                      <button
                        onClick={() => setOpenSkills(allOpen ? new Set() : new Set(skills.map((s) => s.skill_name)))}
                        className="btn-ghost shrink-0 px-3 py-1.5 text-xs"
                      >
                        {allOpen ? "Collapse all" : "Expand all"}
                      </button>
                    </div>
                    <div key={category ?? "all"} className="gap-5 xl:columns-2">
                      {shownGroups.map((group) => {
                        const summary = groupSummary(group);
                        const accent = ACCENTS[groups.indexOf(group) % ACCENTS.length];
                        return (
                          <section
                            key={group.category}
                            aria-label={group.category}
                            className="panel rise mb-5 break-inside-avoid px-5 pb-2 pt-4 sm:px-5"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 pb-1">
                              <h3 className="flex items-center gap-2.5 text-lg font-bold">
                                <span className={`h-3 w-3 rounded-full ${accent.dot}`} aria-hidden="true" />
                                {group.category}
                              </h3>
                              {summary && <span className="muted text-xs font-semibold">{summary}</span>}
                            </div>
                            <ul>
                              {group.skills.map((s) => (
                                <SkillRow
                                  key={s.skill_name}
                                  skill={s}
                                  open={openSkills.has(s.skill_name)}
                                  onToggle={() => toggleSkill(s.skill_name)}
                                  test={testScores[s.skill_name]}
                                />
                              ))}
                            </ul>
                          </section>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            </div>

            {candidate.projects.length > 0 && (
              <div role="tabpanel" className={tab === "projects" ? "mt-6" : "hidden"}>
                <h2 className="text-2xl font-bold">Projects on the resume</h2>
                <p className="muted mt-1 text-sm">
                  {candidate.analyzed
                    ? "Each project is linked to its GitHub repository when the names match."
                    : "Run the analysis to link each project to its GitHub repository."}
                </p>
                <ul className="mt-5 grid gap-5 md:grid-cols-2">
                  {candidate.projects.map((p, i) => (
                    <ProjectCard key={`${p.project_name}-${i}`} project={p} analyzed={candidate.analyzed} index={i} />
                  ))}
                </ul>
              </div>
            )}

            {user?.role === "recruiter" && candidate.has_account && tab === "tests" && (
              <div role="tabpanel" className="mt-6">
                <SkillTestsPanel
                  candidateId={candidate.candidate_id}
                  resumeSkills={skills.map((s) => s.skill_name)}
                  suggested={skills.filter((s) => !isBacked(s)).map((s) => s.skill_name)}
                />
              </div>
            )}

            {user?.role === "student" && (
              <div role="tabpanel" className={tab === "share" ? "mt-6 grid items-start gap-6 lg:grid-cols-[1fr_2fr]" : "hidden"}>
                {candidate.analyzed ? (
                  <div className="relative overflow-hidden rounded-xl bg-ink p-6 text-white dark:bg-night-800 dark:ring-1 dark:ring-white/10 sm:p-7">
                    <SparkIcon className="absolute -right-5 -top-5 h-28 w-28 text-brand-400 opacity-20" />
                    <h2 className="relative text-2xl font-bold">Resume bullet ideas</h2>
                    <p className="relative mt-2 text-sm text-white/90">
                      Resume lines written from your repositories, tailored to a job if you paste one.
                    </p>
                    <Link
                      to={`/candidate/${candidate.candidate_id}/bullets`}
                      className="btn-light relative mt-5"
                    >
                      Get resume lines
                    </Link>
                  </div>
                ) : (
                  <div className="panel muted text-sm">
                    Run the GitHub analysis to get resume lines written from your repositories.
                  </div>
                )}
                <PortfolioPanel candidateId={candidate.candidate_id} refreshKey={analysisRuns} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
