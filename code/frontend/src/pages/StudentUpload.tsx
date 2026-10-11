import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { ApiError, apiGet, apiUpload } from "../lib/api";

interface UploadResult {
  candidate_id: number;
  filename: string;
  status: string;
  name?: string | null;
  extracted_skills?: string[];
  projects?: string[];
  github_url?: string | null;
  github_username?: string | null;
  error?: string;
}

interface CandidateSummary {
  candidate_id: number;
  name: string | null;
  github_username: string | null;
  created_at: string;
  skill_count: number;
}

export function StudentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [githubUrlOverride, setGithubUrlOverride] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<CandidateSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const loadHistory = () => {
    setHistoryLoading(true);
    apiGet<CandidateSummary[]>("/api/candidates/me")
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    if (githubUrlOverride.trim()) {
      formData.append("github_url_override", githubUrlOverride.trim());
    }

    try {
      const data = await apiUpload<UploadResult>("/api/resume/upload", formData);
      setResult(data);
      loadHistory();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-50/40">
      <Navbar />

      <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <h1 className="text-2xl font-bold text-slate-800 sm:text-3xl">Upload your resume</h1>
        <p className="mt-2 text-sm text-slate-500 sm:text-base">
          We'll extract your skills and cross-check them against your public GitHub
          activity to build an evidence-backed report you can share with recruiters.
        </p>

        <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
          <label htmlFor="resume-file" className="block text-sm font-medium text-slate-700">
            Resume PDF
          </label>
          <input
            id="resume-file"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
          />

          <label
            htmlFor="github-override"
            className="mt-5 block text-sm font-medium text-slate-700"
          >
            GitHub URL (optional override)
          </label>
          <input
            id="github-override"
            type="text"
            value={githubUrlOverride}
            onChange={(e) => setGithubUrlOverride(e.target.value)}
            placeholder="github.com/username"
            className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
          />
          <p className="mt-1 text-xs text-slate-400">
            PDF extraction can miss GitHub links on multi-column or graphic-heavy resumes -
            set this if needed.
          </p>

          <button
            onClick={handleSubmit}
            disabled={!file || loading}
            className="mt-5 w-full rounded-md bg-brand-600 py-2.5 font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto sm:px-8"
          >
            {loading ? "Analyzing..." : "Upload & Analyze"}
          </button>

          {error && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}
        </div>

        {result && (
          <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
            <p className="text-sm text-slate-500">Analyzed {result.filename}</p>
            {result.name && (
              <p className="mt-1 text-lg font-semibold text-slate-800">{result.name}</p>
            )}

            {result.extracted_skills && result.extracted_skills.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-slate-700">Detected skills</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {result.extracted_skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <Link
              to={`/candidate/${result.candidate_id}`}
              className="mt-5 inline-block rounded-md border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
            >
              View full report
            </Link>
          </div>
        )}

        <div className="mt-10">
          <h2 className="text-lg font-semibold text-slate-800">Your upload history</h2>
          {historyLoading ? (
            <p className="mt-2 text-sm text-slate-400">Loading...</p>
          ) : history.length === 0 ? (
            <p className="mt-2 text-sm text-slate-400">No resumes uploaded yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-brand-100 overflow-hidden rounded-xl border border-brand-100 bg-white">
              {history.map((c) => (
                <li key={c.candidate_id}>
                  <Link
                    to={`/candidate/${c.candidate_id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition hover:bg-brand-50/60"
                  >
                    <span className="font-medium text-slate-700">
                      {c.name ?? `Candidate #${c.candidate_id}`}
                    </span>
                    <span className="text-xs text-slate-400">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
