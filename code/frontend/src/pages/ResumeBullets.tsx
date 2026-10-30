import { useState } from "react";
import { Link, useParams } from "react-router-dom";
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
    <div className="mt-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {items.map((s) => (
          <span key={s} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}>
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
  const [jobDescription, setJobDescription] = useState("");
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
    <div className="min-h-screen bg-brand-50/40">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <Link to={`/candidate/${candidateId}`} className="text-sm font-medium text-brand-700 hover:underline">
          ← Back to report
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-slate-800">Resume bullet ideas</h1>
        <p className="mt-2 text-sm text-slate-500">
          Specific resume lines built from what your repositories actually contain. Paste a job
          description to put the most relevant projects and lines first and see which of its
          skills you can already prove.
        </p>

        <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
          <label htmlFor="job-description" className="block text-sm font-medium text-slate-700">
            Job description (optional)
          </label>
          <textarea
            id="job-description"
            rows={5}
            maxLength={10000}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here, e.g. from RecruitSage"
            className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
          />
          <button
            onClick={generate}
            disabled={loading}
            className="mt-4 rounded-md bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40"
          >
            {loading ? "Generating..." : "Generate resume lines"}
          </button>
          {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        </div>

        {match && (
          <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-800">Job match</h2>
              {match.readiness !== null && (
                <span className="text-sm font-semibold text-slate-700">
                  {match.readiness}% of the job's skills proven
                </span>
              )}
            </div>
            {match.skills.length === 0 ? (
              <p className="mt-2 text-sm text-slate-400">
                No skills from DevProof's catalog were found in this job description.
              </p>
            ) : (
              <>
                <Chips label="Proven on GitHub" items={match.proven} tone="bg-emerald-50 text-emerald-700" />
                <Chips label="On your resume, not yet proven" items={match.claimed_only} tone="bg-amber-50 text-amber-700" />
                <Chips label="Missing from your resume" items={match.missing} tone="bg-red-50 text-red-700" />
                {match.tips.length > 0 && (
                  <ul className="mt-4 list-inside list-disc space-y-1 text-xs text-slate-500">
                    {match.tips.map((tip) => (
                      <li key={tip}>{tip}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        )}

        {report && (
          <div className="mt-6 space-y-4">
            {report.projects.length === 0 && (
              <p className="text-sm text-slate-400">No original projects found to write lines for.</p>
            )}
            {report.projects.map((p) => {
              const all = p.bullets.map((b) => `• ${b.text}`).join("\n");
              return (
                <section
                  key={p.name}
                  aria-label={p.title}
                  className="rounded-2xl border border-brand-100 bg-white p-6 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-slate-800 hover:text-brand-700 hover:underline"
                      >
                        {p.title}
                      </a>
                      {p.matched_skills.length > 0 && (
                        <p className="mt-0.5 text-xs text-emerald-700">
                          Matches the job: {p.matched_skills.join(", ")}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => copy(`${p.name}-all`, all)}
                      className="shrink-0 rounded-md border border-brand-200 px-3 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50"
                    >
                      {copied === `${p.name}-all` ? "Copied!" : "Copy all"}
                    </button>
                  </div>
                  <ul className="mt-3 space-y-2">
                    {p.bullets.map((b, i) => (
                      <li key={b.text} className="flex items-start justify-between gap-3 text-sm text-slate-700">
                        <span>• {b.text}</span>
                        <button
                          onClick={() => copy(`${p.name}-${i}`, b.text)}
                          aria-label={`Copy line ${i + 1} of ${p.title}`}
                          className="shrink-0 text-xs font-medium text-brand-700 hover:underline"
                        >
                          {copied === `${p.name}-${i}` ? "Copied!" : "Copy"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
