import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Hero } from "../components/Hero";
import { ArrowLeftIcon, CheckIcon, CopyIcon, SparkIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { ApiError, apiPost } from "../lib/api";

interface Bullet {
  text: string;
  skills: string[];
}

interface ProjectBullets {
  name: string;
  title: string;
  url: string;
  matched_skills: string[];
  bullets: Bullet[];
}

interface JobMatch {
  skills: string[];
  proven: string[];
  claimed_only: string[];
  missing: string[];
  readiness: number | null;
  tips: string[];
}

export interface BulletReport {
  job_match: JobMatch | null;
  projects: ProjectBullets[];
}

function Chips({ label, items, tone }: { label: string; items: string[]; tone: string }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold text-ink-soft dark:text-slate-300">{label}</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {items.map((s) => (
          <span key={s} className={`chip px-3 py-1 ${tone}`}>
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Suggested resume lines for the candidate's projects, optionally tailored to a job. */
export function ResumeBullets() {
  const { candidateId } = useParams<{ candidateId: string }>();
  // Coming from "Match a job" on My resumes: start with that job filled in.
  const location = useLocation();
  const [jobDescription, setJobDescription] = useState<string>(
    (location.state as { jobDescription?: string } | null)?.jobDescription ?? ""
  );
  const [report, setReport] = useState<BulletReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const generate = async () => {
    if (!candidateId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiPost<BulletReport>(`/api/candidates/${candidateId}/resume-bullets`, {
        job_description: jobDescription.trim() || null,
      });
      setReport(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate lines. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const copy = async (key: string, text: string) => {
    try {
      await navigator.clipboard?.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // Clipboard blocked: the text can still be selected and copied by hand.
    }
  };

  const match = report?.job_match;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero seed={`bullets-${candidateId}`}>
          <Link
            to={`/candidate/${candidateId}`}
            className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-sm font-semibold text-white ring-1 ring-white/25 transition hover:bg-white/25"
          >
            <ArrowLeftIcon className="h-4 w-4" /> Back to report
          </Link>
          <h1 className="mt-5 text-4xl font-bold sm:text-5xl">Resume bullet ideas</h1>
          <p className="mt-3 text-white/90 sm:text-lg">
            Specific resume lines built from what your repositories actually contain. Paste a job
            description to put the most relevant projects and lines first and see which of its
            skills you can already prove.
          </p>
        </Hero>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
            <div className="panel">
              <label htmlFor="job-description" className="label">
                Job description (optional)
              </label>
              <textarea
                id="job-description"
                rows={7}
                maxLength={10000}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the job description here, e.g. from RecruitSage"
                className="field resize-y"
              />
              <button onClick={generate} disabled={loading} className="btn-primary mt-4 w-full">
                <SparkIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Generating..." : "Generate resume lines"}
              </button>
              {error && <p className="alert mt-4">{error}</p>}
            </div>

            {match && (
              <div className="panel rise">
                <h2 className="text-2xl font-bold">Job match</h2>
                {match.readiness !== null && (
                  <div className="mt-3">
                    <div className="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600">
                      <div
                        className="bar-fill h-full rounded-full bg-brand-600"
                        style={{ width: `${Math.max(3, match.readiness)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-sm font-bold">{match.readiness}% of the job's skills proven</p>
                  </div>
                )}
                {match.skills.length === 0 ? (
                  <p className="muted mt-2 text-sm">
                    No skills from DevProof's catalog were found in this job description.
                  </p>
                ) : (
                  <>
                    <Chips label="Proven on GitHub" items={match.proven} tone="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" />
                    <Chips label="On your resume, not yet proven" items={match.claimed_only} tone="bg-sun-400/25 text-amber-700 dark:text-sun-300" />
                    <Chips label="Missing from your resume" items={match.missing} tone="bg-pop-500/10 text-pop-600 dark:text-pop-400" />
                    {match.tips.length > 0 && (
                      <ul className="mt-5 space-y-2 text-sm text-ink-soft dark:text-slate-300">
                        {match.tips.map((tip) => (
                          <li key={tip} className="flex gap-2">
                            <SparkIcon className="mt-0.5 h-4 w-4 shrink-0 text-pop-500" />
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          <div className="space-y-4">
            {!report && (
              <div className="flex h-full min-h-[14rem] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-brand-200 p-10 text-center dark:border-night-600">
                <SparkIcon className="h-10 w-10 text-pop-500" />
                <p className="mt-3 font-display text-xl font-bold">Your lines will appear here</p>
                <p className="muted mt-1 max-w-sm text-sm">
                  Generate to get two or three lines for each of your projects, ready to copy.
                </p>
              </div>
            )}
            {report && report.projects.length === 0 && (
              <p className="muted text-sm">No original projects found to write lines for.</p>
            )}
            {report?.projects.map((p, pi) => {
              const all = p.bullets.map((b) => `• ${b.text}`).join("\n");
              return (
                <section
                  key={p.name}
                  aria-label={p.title}
                  className="panel rise"
                  style={{ animationDelay: `${pi * 60}ms` }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-display text-xl font-bold hover:text-brand-700 dark:hover:text-brand-300"
                      >
                        {p.title}
                      </a>
                      {p.matched_skills.length > 0 && (
                        <p className="mt-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                          Matches the job: {p.matched_skills.join(", ")}
                        </p>
                      )}
                    </div>
                    <button onClick={() => copy(`${p.name}-all`, all)} className="btn-ghost shrink-0 px-3 py-1.5 text-xs">
                      {copied === `${p.name}-all` ? "Copied!" : "Copy all"}
                    </button>
                  </div>
                  <ul className="mt-4 space-y-2">
                    {p.bullets.map((b, i) => (
                      <li
                        key={b.text}
                        className="group flex items-start justify-between gap-3 rounded-xl bg-paper px-4 py-3 text-sm dark:bg-night-700/60"
                      >
                        <span>• {b.text}</span>
                        <button
                          onClick={() => copy(`${p.name}-${i}`, b.text)}
                          aria-label={`Copy line ${i + 1} of ${p.title}`}
                          className="flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold text-brand-700 transition hover:bg-brand-600/10 dark:text-brand-300"
                        >
                          {copied === `${p.name}-${i}` ? <CheckIcon className="h-3.5 w-3.5" /> : <CopyIcon className="h-3.5 w-3.5" />}
                          {copied === `${p.name}-${i}` ? "Copied!" : "Copy"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
