import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiGet, apiPost } from "../lib/api";
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

export interface Roadmap {
  candidate_id: number;
  fit: number;
  proven: { skill: string; repo: string | null }[];
  claimed: { skill: string; checkable: boolean; repo: string | null; step: string }[];
  missing: { skill: string; checkable: boolean; repo: string | null; idea: string; proof: string | null }[];
  practice: string[];
}

export interface JobFitResult {
  skills: string[];
  resumes: ResumeFit[];
  best_candidate_id: number | null;
  reason: string | null;
  tips: string[];
  role?: string | null;
  roadmap?: Roadmap | null;
}

interface Role {
  name: string;
  skills: string[];
}

const practiceLink = (skills: string[]) => `/practice?skills=${encodeURIComponent(skills.join(","))}`;

/** The best resume's gaps for the job, with a concrete next step for each. */
function RoadmapView({ roadmap, target }: { roadmap: Roadmap; target: string }) {
  const todo = roadmap.claimed.length + roadmap.missing.length;
  return (
    <section aria-label="Skill gap roadmap" className="mt-5 rounded-lg bg-slate-50 p-4 dark:bg-night-700/50 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">Your roadmap for {target}</h3>
          <p className="muted text-sm">
            {todo === 0
              ? "Your best resume already proves every skill this asks for."
              : `${roadmap.proven.length} proven, ${todo} to work on, based on your best resume.`}
          </p>
        </div>
        {roadmap.practice.length > 0 && (
          <Link to={practiceLink(roadmap.practice)} className="btn-primary">
            <SparkIcon className="h-4 w-4" />
            Practise all my gaps
          </Link>
        )}
      </div>

      <ol className="mt-4 space-y-2">
        {roadmap.claimed.map((g) => (
          <li
            key={g.skill}
            aria-label={`${g.skill}: not proven`}
            className="rounded-lg border border-slate-200 border-l-4 border-l-sun-400 p-3.5 dark:border-night-600 dark:border-l-sun-400"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{g.skill}</span>
              <span className="chip bg-sun-400/25 py-0.5 text-[11px] text-amber-700 dark:text-sun-300">On resume, not proven</span>
              <Link to={practiceLink([g.skill])} className="link ml-auto text-xs font-semibold">
                Practise
              </Link>
            </div>
            <p className="mt-1 text-sm text-ink-soft dark:text-slate-300">
              {g.repo ? <>Add it to <span className="font-semibold">{g.repo}</span>. </> : null}
              {g.step}
            </p>
          </li>
        ))}
        {roadmap.missing.map((g) => (
          <li
            key={g.skill}
            aria-label={`${g.skill}: missing`}
            className="rounded-lg border border-slate-200 border-l-4 border-l-pop-500 p-3.5 dark:border-night-600 dark:border-l-pop-500"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{g.skill}</span>
              <span className="chip bg-pop-500/10 py-0.5 text-[11px] text-pop-600 dark:text-pop-400">Missing</span>
              <Link to={practiceLink([g.skill])} className="link ml-auto text-xs font-semibold">
                Practise
              </Link>
            </div>
            <p className="mt-1 text-sm text-ink-soft dark:text-slate-300">
              {g.repo ? <>Add it to <span className="font-semibold">{g.repo}</span>, or a new project: </> : <span className="font-medium">Project idea: </span>}
              {g.idea}
            </p>
            {g.proof && <p className="muted mt-1 text-xs">DevProof will see it when you: {g.proof.charAt(0).toLowerCase() + g.proof.slice(1)}</p>}
            {!g.checkable && <p className="muted mt-1 text-xs">GitHub can't show this one, so add it to your resume and be ready to explain it.</p>}
          </li>
        ))}
      </ol>

      {roadmap.proven.length > 0 && (
        <p className="mt-4 flex flex-wrap items-center gap-1.5 text-sm">
          <span className="font-semibold">Already proven:</span>
          {roadmap.proven.map((p) => (
            <span key={p.skill} className="chip bg-emerald-500/15 py-1 text-emerald-700 dark:text-emerald-300" title={p.repo ? `Proven by ${p.repo}` : undefined}>
              <CheckIcon className="mr-1 inline h-3 w-3" />
              {p.skill}
              {p.repo && <span className="font-normal opacity-75"> · {p.repo}</span>}
            </span>
          ))}
        </p>
      )}
    </section>
  );
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
  const [mode, setMode] = useState<"job" | "role">("job");
  const [roles, setRoles] = useState<Role[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [result, setResult] = useState<JobFitResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Role[]>("/api/job-fit/roles")
      .then((r) => setRoles(Array.isArray(r) ? r : []))
      .catch(() => setRoles([]));
  }, []);

  const run = async (body: { job_description: string } | { role: string }) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await apiPost<JobFitResult>("/api/job-fit", body));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not check the job. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const check = () => {
    if (job.trim()) run({ job_description: job });
  };

  const pickRole = (name: string) => {
    setRole(name);
    run({ role: name });
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
        See which of your resumes fits a job best, and get a roadmap for the skills you still need to prove.
      </p>

      {roles.length > 0 && (
        <div role="group" aria-label="Match against" className="mt-4 inline-grid grid-cols-2 gap-1 rounded-md bg-slate-100 p-1 dark:bg-night-700">
          {(
            [
              ["job", "Paste a job"],
              ["role", "Pick a role"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={mode === id}
              onClick={() => setMode(id)}
              className={`rounded px-3 py-1.5 text-sm font-semibold transition ${
                mode === id ? "bg-white text-ink shadow-sm dark:bg-night-600 dark:text-white" : "text-ink-mute"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {mode === "job" || roles.length === 0 ? (
        <>
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
        </>
      ) : (
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {roles.map((r) => (
            <button
              key={r.name}
              type="button"
              aria-pressed={role === r.name}
              onClick={() => pickRole(r.name)}
              disabled={loading}
              className={`rounded-lg border p-3 text-left transition ${
                role === r.name
                  ? "border-ink bg-ink text-white dark:border-white dark:bg-white dark:text-ink"
                  : "border-slate-200 hover:border-slate-400 dark:border-night-600"
              }`}
            >
              <span className="block font-semibold">{r.name}</span>
              <span className={`mt-0.5 block text-xs ${role === r.name ? "opacity-80" : "text-ink-mute dark:text-slate-400"}`}>
                {r.skills.slice(0, 4).join(", ")}
                {r.skills.length > 4 ? ` +${r.skills.length - 4}` : ""}
              </span>
            </button>
          ))}
        </div>
      )}

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
                <span className="font-semibold">{result.role ? `${result.role} needs:` : "This job asks for:"}</span> {result.skills.join(", ")}
              </p>
              {result.reason && <p className="muted mt-1 text-sm">{result.reason}</p>}

              {result.roadmap && <RoadmapView roadmap={result.roadmap} target={result.role ?? "this job"} />}

              {result.roadmap && <h3 className="mt-6 text-sm font-semibold">How each of your resumes compares</h3>}
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
                            state={{ jobDescription: result.role ? `${result.role}: ${result.skills.join(", ")}` : job }}
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

              {!result.roadmap && result.tips.length > 0 && (
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
