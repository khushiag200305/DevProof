import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiGet, apiPost } from "../lib/api";

interface SkillEntry {
  skill_name: string;
  status: string | null;
  score: number | null;
  reasons: string[];
  interview_question: string | null;
}

interface ProjectEntry {
  project_name: string;
  description: string | null;
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

function statusBadgeClasses(status: string | null): string {
  if (!status) return "bg-slate-100 text-slate-500";
  const normalized = status.toLowerCase();
  if (normalized.includes("strong")) return "bg-emerald-50 text-emerald-700";
  if (normalized.includes("good")) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
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
    } catch (err) {
      setAnalyzeError(
        err instanceof ApiError ? err.message : "Analysis failed. Please try again."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-50/40">
      <Navbar />

      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <Link to={homePath} className="text-sm font-medium text-brand-700 hover:underline">
          ← Back
        </Link>

        {loading && <p className="mt-6 text-sm text-slate-400">Loading...</p>}
        {error && (
          <p className="mt-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        {candidate && (
          <>
            <div className="mt-4 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
              <h1 className="text-2xl font-bold text-slate-800">
                {candidate.name ?? `Candidate #${candidate.candidate_id}`}
              </h1>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                {candidate.email && <span>{candidate.email}</span>}
                {candidate.github_username && (
                  <a
                    href={`https://github.com/${candidate.github_username}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    @{candidate.github_username}
                  </a>
                )}
                <span>Uploaded {new Date(candidate.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">Claimed skills</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {candidate.analyzed
                      ? `Scored against ${candidate.repos_analyzed} public GitHub ${
                          candidate.repos_analyzed === 1 ? "repository" : "repositories"
                        }. Every score lists the evidence behind it.`
                      : "Run the analysis to check each skill against public GitHub evidence."}
                  </p>
                </div>
                {candidate.github_username ? (
                  <button
                    onClick={runAnalysis}
                    disabled={analyzing}
                    className="shrink-0 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {analyzing
                      ? "Analyzing GitHub..."
                      : candidate.analyzed
                        ? "Re-run analysis"
                        : "Analyze GitHub evidence"}
                  </button>
                ) : (
                  <p className="shrink-0 text-xs text-slate-400">
                    No GitHub username on this resume
                  </p>
                )}
              </div>

              {analyzeError && (
                <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
                  {analyzeError}
                </p>
              )}

              {candidate.skills.length === 0 ? (
                <p className="mt-4 text-sm text-slate-400">No skills detected.</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {candidate.skills.map((s) => (
                    <li
                      key={s.skill_name}
                      className="rounded-lg border border-slate-100 px-4 py-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-slate-700">{s.skill_name}</span>
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-medium ${statusBadgeClasses(s.status)}`}
                        >
                          {s.status ?? "Pending Analysis"}
                          {s.score !== null && ` · ${s.score}/100`}
                        </span>
                      </div>
                      {s.reasons.length > 0 && (
                        <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-slate-500">
                          {s.reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      )}
                      {s.interview_question && (
                        <p className="mt-2 rounded-md bg-brand-50 px-3 py-2 text-xs text-brand-700">
                          <span className="font-medium">Suggested interview question:</span>{" "}
                          {s.interview_question}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {candidate.projects.length > 0 && (
              <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
                <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
                <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-slate-600">
                  {candidate.projects.map((p) => (
                    <li key={p.project_name}>{p.project_name}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
