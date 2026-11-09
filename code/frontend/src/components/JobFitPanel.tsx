import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import { CheckIcon, EyeIcon, SparkIcon } from "./Icons";

export interface ResumeFit {
  candidate_id: number;
  name: string | null;
  created_at: string;
  analyzed: boolean;
  visible_to_recruiters: boolean;
  proven: string[];
  claimed_only: string[];
  missing: string[];
  fit: number;
  best: boolean;
}

export interface JobFitResult {
  skills: string[];
  resumes: ResumeFit[];
  best_candidate_id: number | null;
  reason: string | null;
  tips: string[];
}

function Chips({ items, tone, label }: { items: string[]; tone: string; label: string }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="w-24 shrink-0 text-xs font-semibold text-ink-mute dark:text-slate-400">{label}</span>
      {items.map((s) => (
        <span key={s} className={`chip py-1 ${tone}`}>
          {s}
        </span>
      ))}
    </div>
  );
}

/**
 * "Which of my resumes fits this job?" The student pastes a job
 * description; each upload is scored against the skills it asks for.
 */
export function JobFitPanel({
  onMakeVisible,
}: {
  /** Makes an upload visible to recruiters; resolves once saved. */
  onMakeVisible: (candidateId: number) => Promise<boolean>;
}) {
  const [job, setJob] = useState("");
  const [result, setResult] = useState<JobFitResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = async () => {
    if (!job.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await apiPost<JobFitResult>("/api/job-fit", { job_description: job }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not check the job. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const makeVisible = async (candidateId: number) => {
    if (await onMakeVisible(candidateId)) {
      setResult((r) =>
        r && {
          ...r,
          resumes: r.resumes.map((x) => ({ ...x, visible_to_recruiters: x.candidate_id === candidateId })),
        }
      );
    }
  };

  return (
    <section aria-labelledby="job-fit-heading" className="panel">
      <h2 id="job-fit-heading" className="text-xl font-bold">
        Match a job
      </h2>
      <p className="muted mt-1 text-sm">
        Paste a job description to see which of your resumes fits it best, and what's missing.
      </p>

      <label htmlFor="job-fit-text" className="label mt-4">
        Job description
      </label>
      <textarea
        id="job-fit-text"
        rows={5}
        maxLength={10000}
        value={job}
        onChange={(e) => setJob(e.target.value)}
        placeholder="Paste the job description here, e.g. from RecruitSage"
        className="field resize-y"
      />
      <button onClick={check} disabled={loading || !job.trim()} className="btn-primary mt-3">
        <SparkIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Checking..." : "Find my best resume"}
      </button>

      {error && <p className="alert mt-4">{error}</p>}

      {result && (
        <div className="rise mt-6 border-t border-slate-200 pt-5 dark:border-night-600">
          {result.skills.length === 0 ? (
            <p className="muted text-sm">
              No skills from DevProof's catalog were found in this job description, so there's nothing to compare yet.
            </p>
          ) : result.resumes.length === 0 ? (
            <p className="muted text-sm">Upload a resume first, then check it against this job.</p>
          ) : (
            <>
              <p className="text-sm">
                <span className="font-semibold">This job asks for:</span> {result.skills.join(", ")}
              </p>
              {result.reason && <p className="muted mt-1 text-sm">{result.reason}</p>}

              <ul className="mt-4 space-y-3">
                {result.resumes.map((r) => {
                  const label = `${r.name ?? "Resume"}, uploaded ${new Date(r.created_at).toLocaleDateString()}`;
                  return (
                    <li
                      key={r.candidate_id}
                      aria-label={label}
                      className={`rounded-lg border p-4 ${
                        r.best ? "border-brand-600 bg-brand-600/[0.04] dark:border-brand-400" : "border-slate-200 dark:border-night-600"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="flex flex-wrap items-center gap-2 font-semibold">
                            {label}
                            {r.best && (
                              <span className="chip inline-flex items-center gap-1 bg-brand-600 py-1 text-white">
                                <CheckIcon className="h-3 w-3" /> Best for this job
                              </span>
                            )}
                          </p>
                          <p className="muted mt-0.5 flex flex-wrap gap-x-3 text-xs">
                            {r.visible_to_recruiters && (
                              <span className="inline-flex items-center gap-1 font-semibold text-brand-700 dark:text-brand-300">
                                <EyeIcon className="h-3.5 w-3.5" /> Visible to recruiters
                              </span>
                            )}
                            {!r.analyzed && <span>Not analyzed yet - run the analysis for a fair score</span>}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold tabular-nums leading-none">{r.fit}</p>
                          <p className="muted mt-1 text-[11px] font-medium">fit</p>
                        </div>
                      </div>

                      <div className="mt-3 space-y-1.5">
                        <Chips label="Proven" items={r.proven} tone="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" />
                        <Chips label="Not proven" items={r.claimed_only} tone="bg-sun-400/25 text-amber-700 dark:text-sun-300" />
                        <Chips label="Missing" items={r.missing} tone="bg-pop-500/10 text-pop-600 dark:text-pop-400" />
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {!r.visible_to_recruiters && (
                          <button onClick={() => makeVisible(r.candidate_id)} className="btn-ghost px-3 py-1.5 text-xs">
                            Make visible
                          </button>
                        )}
                        <Link to={`/candidate/${r.candidate_id}`} className="btn-ghost px-3 py-1.5 text-xs">
                          Open report
                        </Link>
                        {r.analyzed && (
                          <Link
                            to={`/candidate/${r.candidate_id}/bullets`}
                            state={{ jobDescription: job }}
                            className="btn-ghost px-3 py-1.5 text-xs"
                          >
                            Get resume lines for this job
                          </Link>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>

              {result.tips.length > 0 && (
                <div className="mt-5">
                  <p className="text-sm font-semibold">To improve your best resume for this job</p>
                  <ul className="mt-2 space-y-1.5 text-sm text-ink-soft dark:text-slate-300">
                    {result.tips.map((tip) => (
                      <li key={tip} className="flex gap-2">
                        <SparkIcon className="mt-0.5 h-4 w-4 shrink-0 text-brand-600 dark:text-brand-300" />
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
