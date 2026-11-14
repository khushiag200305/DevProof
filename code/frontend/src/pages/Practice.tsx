import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Hero, HeroStat } from "../components/Hero";
import { SparkIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { QuizResultView } from "../components/QuizResultView";
import { QuizRunner } from "../components/QuizRunner";
import { ApiError, apiGet, apiPost } from "../lib/api";
import type { AttemptSummary, QuizInProgress, QuizResult, QuizSkill } from "../lib/quiz";
import { STATUS_LABEL, STATUS_STYLE, type SkillTest } from "../lib/skillTests";

interface SkillsResponse {
  skills: QuizSkill[];
  suggested: string[];
  counts: number[];
}

/** Student mock interview practice: pick skills, take a quiz, review the answers. */
export function Practice() {
  const [catalog, setCatalog] = useState<SkillsResponse | null>(null);
  const [params] = useSearchParams();
  // Skills sent from the job roadmap, e.g. /practice?skills=Docker,SQL
  const [fromRoadmap] = useState<string[]>(() =>
    (params.get("skills") ?? "").split(",").map((s) => s.trim()).filter(Boolean)
  );
  const [selected, setSelected] = useState<string[]>(fromRoadmap);
  const [count, setCount] = useState(10);
  const [timed, setTimed] = useState(false);
  const [attempt, setAttempt] = useState<QuizInProgress | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [history, setHistory] = useState<AttemptSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [tests, setTests] = useState<SkillTest[]>([]);
  /** Set while taking (or reviewing) a recruiter's test rather than practice. */
  const [fromTest, setFromTest] = useState(false);

  const loadHistory = () =>
    apiGet<AttemptSummary[]>("/api/quiz/attempts").then(setHistory).catch(() => setHistory([]));
  const loadTests = () =>
    apiGet<SkillTest[]>("/api/skill-tests/mine")
      .then((t) => setTests(Array.isArray(t) ? t : []))
      .catch(() => setTests([]));

  useEffect(() => {
    apiGet<SkillsResponse>("/api/quiz/skills")
      .then(setCatalog)
      .catch(() => setError("Could not load practice skills."));
    loadHistory();
    loadTests();
  }, []);

  const startTest = async (t: SkillTest) => {
    setStarting(true);
    setError(null);
    try {
      const started = await apiPost<QuizInProgress>(`/api/skill-tests/${t.test_id}/start`);
      setResult(null);
      setFromTest(true);
      setAttempt(started);
      window.scrollTo?.({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the test.");
      loadTests();
    } finally {
      setStarting(false);
    }
  };

  const openTestResult = async (t: SkillTest) => {
    if (!t.attempt_id) return;
    try {
      const past = await apiGet<QuizResult>(`/api/quiz/attempts/${t.attempt_id}`);
      setAttempt(null);
      setFromTest(true);
      setResult(past);
    } catch {
      setError("Could not open that test.");
    }
  };

  const openTests = tests.filter((t) => t.status === "waiting" || t.status === "in_progress");

  const byCategory = useMemo(() => {
    const groups: Record<string, QuizSkill[]> = {};
    for (const s of catalog?.skills ?? []) (groups[s.category] ??= []).push(s);
    return Object.entries(groups);
  }, [catalog]);

  const toggle = (name: string) =>
    setSelected((s) => (s.includes(name) ? s.filter((x) => x !== name) : [...s, name]));

  const start = async (skills: string[]) => {
    setStarting(true);
    setError(null);
    try {
      const started = await apiPost<QuizInProgress>("/api/quiz/practice", { skills, count, timed });
      setResult(null);
      setFromTest(false);
      setAttempt(started);
      window.scrollTo?.({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the quiz.");
    } finally {
      setStarting(false);
    }
  };

  const openPast = async (id: number) => {
    try {
      const past = await apiGet<QuizResult | QuizInProgress>(`/api/quiz/attempts/${id}`);
      setFromTest(false);
      if (past.status === "submitted") {
        setAttempt(null);
        setResult(past);
      } else {
        setResult(null);
        setAttempt(past);
      }
    } catch {
      setError("Could not open that attempt.");
    }
  };

  const finished = history.filter((h) => h.score !== null);
  const best = finished.length ? Math.max(...finished.map((h) => Math.round((100 * (h.score ?? 0)) / Math.max(1, h.total)))) : null;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero
          seed="practice"
          aside={
            <div className="grid grid-cols-2 gap-3">
              <HeroStat value={finished.length} label="Quizzes taken" />
              <HeroStat value={best === null ? "-" : `${best}%`} label="Best score" />
            </div>
          }
        >
          <h1 className="text-4xl font-bold sm:text-5xl">Interview practice</h1>
          <p className="mt-3 max-w-xl text-white/80 sm:text-lg">
            Practise the questions recruiters are likely to ask, especially for skills your GitHub doesn't prove yet.
          </p>
        </Hero>

        {error && <p className="alert mt-4">{error}</p>}

        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_20rem]">
          <div className="min-w-0">
            {attempt ? (
              <QuizRunner
                key={attempt.attempt_id}
                attempt={attempt}
                onDone={(r) => {
                  setAttempt(null);
                  setResult(r);
                  loadHistory();
                  loadTests();
                }}
              />
            ) : result ? (
              <>
                <div className="mb-4 flex flex-wrap gap-2">
                  <button onClick={() => start(result.skills)} disabled={starting} className="btn-primary">
                    Practise these skills again
                  </button>
                  <button onClick={() => setResult(null)} className="btn-ghost">
                    {fromTest ? "Back" : "New practice"}
                  </button>
                </div>
                {fromTest && (
                  <p className="muted mb-4 text-sm">This was a recruiter's skill test. They can see this score.</p>
                )}
                <QuizResultView result={result} />
              </>
            ) : (
              <>
              {openTests.length > 0 && (
                <section aria-label="Skill tests from recruiters" className="panel mb-6 border-l-4 border-l-brand-600">
                  <h2 className="text-xl font-bold">Skill tests from recruiters</h2>
                  <p className="muted mt-1 text-sm">
                    You can take each test once. The timer starts when you press Start and the recruiter sees your score.
                  </p>
                  <ul className="mt-4 space-y-3">
                    {openTests.map((t) => (
                      <li
                        key={t.test_id}
                        aria-label={`Skill test on ${t.skills.join(", ")}`}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-4 dark:border-night-600"
                      >
                        <div className="min-w-0">
                          <p className="font-semibold">{t.skills.join(", ")}</p>
                          <p className="muted text-xs">
                            {t.question_count} questions, {t.time_limit_minutes} minutes
                            {t.from_domain ? `, from a recruiter at ${t.from_domain}` : ""}
                            , due by {new Date(t.expires_at).toLocaleDateString()}
                          </p>
                          {t.message && <p className="mt-2 text-sm">"{t.message}"</p>}
                        </div>
                        <button onClick={() => startTest(t)} disabled={starting} className="btn-primary">
                          {t.status === "in_progress" ? "Continue test" : "Start test"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              <section aria-label="Start a practice quiz" className="panel">
                <h2 className="text-xl font-bold">Start a practice quiz</h2>

                {fromRoadmap.length > 0 && (
                  <div className="mt-4 rounded-lg border border-brand-600/30 bg-brand-600/5 p-4">
                    <p className="text-sm font-semibold">Practise your roadmap gaps</p>
                    <p className="muted mt-1 text-sm">{fromRoadmap.join(", ")}</p>
                    <button onClick={() => start(fromRoadmap)} disabled={starting} className="btn-primary mt-3">
                      <SparkIcon className="h-4 w-4" />
                      Start this quiz
                    </button>
                  </div>
                )}

                {catalog && catalog.suggested.length > 0 && fromRoadmap.length === 0 && (
                  <div className="mt-4 rounded-lg border border-brand-600/30 bg-brand-600/5 p-4">
                    <p className="text-sm font-semibold">Practise my unproven skills</p>
                    <p className="muted mt-1 text-sm">
                      From the resume visible to recruiters: {catalog.suggested.join(", ")}.
                    </p>
                    <button onClick={() => start(catalog.suggested)} disabled={starting} className="btn-primary mt-3">
                      <SparkIcon className="h-4 w-4" />
                      Practise these
                    </button>
                  </div>
                )}

                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="label">Questions</p>
                    <div role="group" aria-label="Number of questions" className="mt-1.5 grid grid-cols-3 gap-1 rounded-md bg-slate-100 p-1 dark:bg-night-700">
                      {(catalog?.counts ?? [5, 10, 15]).map((n) => (
                        <button
                          key={n}
                          type="button"
                          aria-pressed={count === n}
                          onClick={() => setCount(n)}
                          className={`rounded px-2 py-1.5 text-sm font-semibold transition ${
                            count === n ? "bg-white text-ink shadow-sm dark:bg-night-600 dark:text-white" : "text-ink-mute"
                          }`}
                        >
                          {n}
                        </button>
                      ))}
                    </div>
                  </div>
                  <label className="flex items-center gap-2.5 self-end pb-2 text-sm font-medium">
                    <input type="checkbox" checked={timed} onChange={(e) => setTimed(e.target.checked)} className="h-4 w-4 accent-brand-600" />
                    Timed (1 minute per question)
                  </label>
                </div>

                <p className="label mt-6">Or pick skills</p>
                <div className="mt-2 space-y-4">
                  {byCategory.map(([category, skills]) => (
                    <div key={category}>
                      <p className="muted text-xs font-semibold">{category}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {skills.map((s) => {
                          const on = selected.includes(s.name);
                          return (
                            <button
                              key={s.name}
                              type="button"
                              aria-pressed={on}
                              onClick={() => toggle(s.name)}
                              className={`chip border py-1.5 transition ${
                                on
                                  ? "border-ink bg-ink text-white dark:border-white dark:bg-white dark:text-ink"
                                  : "border-slate-200 text-ink-soft hover:border-slate-400 dark:border-night-600 dark:text-slate-300"
                              }`}
                            >
                              {s.name}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-night-600">
                  <button onClick={() => start(selected)} disabled={starting || selected.length === 0} className="btn-primary">
                    {starting ? "Starting..." : "Start practice"}
                  </button>
                  <span className="muted text-sm">
                    {selected.length === 0 ? "Pick at least one skill." : `${selected.length} selected`}
                  </span>
                </div>
              </section>
              </>
            )}
          </div>

          <div className="space-y-6">
          {tests.some((t) => !(t.status === "waiting" || t.status === "in_progress")) && (
            <aside aria-label="Recruiter tests taken" className="panel h-fit p-5 sm:p-5">
              <h2 className="text-lg font-bold">Recruiter tests</h2>
              <ul className="mt-3 space-y-1">
                {tests
                  .filter((t) => !(t.status === "waiting" || t.status === "in_progress"))
                  .map((t) => (
                    <li key={t.test_id}>
                      <button
                        onClick={() => openTestResult(t)}
                        disabled={t.score === null}
                        className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left transition hover:bg-slate-100 disabled:cursor-default disabled:hover:bg-transparent dark:hover:bg-night-700"
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold">{t.skills.join(", ")}</span>
                          <span className={`chip mt-1 py-0.5 text-[11px] ${STATUS_STYLE[t.status]}`}>{STATUS_LABEL[t.status]}</span>
                        </span>
                        {t.score !== null && (
                          <span className="shrink-0 text-sm font-semibold tabular-nums">
                            {t.score}/{t.total}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}
              </ul>
            </aside>
          )}
          <aside aria-label="Past practice" className="panel h-fit p-5 sm:p-5">
            <h2 className="text-lg font-bold">Past practice</h2>
            {history.length === 0 ? (
              <p className="muted mt-2 text-sm">Your quizzes will appear here.</p>
            ) : (
              <ul className="mt-3 space-y-1">
                {history.map((h) => (
                  <li key={h.attempt_id}>
                    <button
                      onClick={() => openPast(h.attempt_id)}
                      className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left transition hover:bg-slate-100 dark:hover:bg-night-700"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold">{h.skills.join(", ")}</span>
                        <span className="muted block text-xs">{new Date(h.started_at).toLocaleString()}</span>
                      </span>
                      <span className="shrink-0 text-sm font-semibold tabular-nums">
                        {h.score === null ? "Not finished" : `${h.score}/${h.total}`}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
