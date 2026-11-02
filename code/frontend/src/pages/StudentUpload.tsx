import { useEffect, useState } from "react";
import type { DragEvent } from "react";
import { Link } from "react-router-dom";
import { Hero, HeroStat } from "../components/Hero";
import { FileIcon, GitHubIcon, UploadIcon } from "../components/Icons";
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

const CHIP_TONES = [
  "bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-200",
  "bg-pop-500/10 text-pop-600 dark:text-pop-400",
  "bg-sun-400/20 text-amber-700 dark:text-sun-300",
  "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
];

export function StudentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [githubUrlOverride, setGithubUrlOverride] = useState("");
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<CandidateSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [dragging, setDragging] = useState(false);

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

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  };

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

  const latest = history[0];

  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero
          seed="upload"
          aside={
            <div className="grid grid-cols-2 gap-3">
              <HeroStat value={historyLoading ? "-" : history.length} label="Resumes uploaded" />
              <HeroStat value={latest ? latest.skill_count : "-"} label="Skills on the latest" />
            </div>
          }
        >
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">Upload your resume</h1>
          <p className="mt-3 max-w-xl text-white/90 sm:text-lg">
            We'll extract your skills and cross-check them against your public GitHub activity to
            build an evidence-backed report you can share with recruiters.
          </p>
        </Hero>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
          <div className="space-y-6">
            <div className="panel">
              <label
                htmlFor="resume-file"
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`group flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition focus-within:ring-4 focus-within:ring-brand-500/20 ${
                  dragging
                    ? "scale-[1.01] border-pop-500 bg-pop-500/5"
                    : file
                      ? "border-emerald-400 bg-emerald-500/5"
                      : "border-brand-200 hover:border-brand-400 hover:bg-brand-50/60 dark:border-night-600 dark:hover:border-brand-400 dark:hover:bg-night-700/50"
                }`}
              >
                <span
                  className={`flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-lg transition-transform group-hover:-translate-y-1 ${
                    file ? "bg-emerald-500" : "bg-gradient-to-br from-brand-500 to-brand-700"
                  }`}
                >
                  {file ? <FileIcon className="h-7 w-7" /> : <UploadIcon className="h-7 w-7" />}
                </span>
                <span className="font-display text-lg font-bold">Resume PDF</span>
                <span className="muted text-sm">
                  {file ? file.name : "Drop your PDF here, or click to choose a file"}
                </span>
                <input
                  id="resume-file"
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="sr-only"
                />
              </label>

              <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
                <div>
                  <label htmlFor="github-override" className="label">
                    GitHub URL (optional override)
                  </label>
                  <div className="relative">
                    <GitHubIcon className="pointer-events-none absolute left-3.5 top-1/2 mt-[3px] h-4 w-4 -translate-y-1/2 text-ink-mute" />
                    <input
                      id="github-override"
                      type="text"
                      value={githubUrlOverride}
                      onChange={(e) => setGithubUrlOverride(e.target.value)}
                      placeholder="github.com/username"
                      className="field pl-10"
                    />
                  </div>
                </div>
                <button onClick={handleSubmit} disabled={!file || loading} className="btn-primary h-[46px] px-7">
                  {loading ? "Analyzing..." : "Upload & Analyze"}
                </button>
              </div>
              <p className="muted mt-2 text-xs">
                PDF extraction can miss GitHub links on multi-column or graphic-heavy resumes - set
                this if needed.
              </p>

              {error && <p className="alert mt-4">{error}</p>}
            </div>

            {result && (
              <div className="rise relative overflow-hidden rounded-2xl border-2 border-emerald-400/60 bg-white p-6 dark:bg-night-800 sm:p-7">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="muted text-sm">Analyzed {result.filename}</p>
                    {result.name && (
                      <p className="mt-1 font-display text-2xl font-bold">{result.name}</p>
                    )}
                  </div>
                  <Link to={`/candidate/${result.candidate_id}`} className="btn-primary shrink-0">
                    View full report
                  </Link>
                </div>

                {result.extracted_skills && result.extracted_skills.length > 0 && (
                  <div className="mt-5">
                    <p className="label">Detected skills</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.extracted_skills.map((skill, i) => (
                        <span
                          key={skill}
                          className={`rise chip px-3 py-1 ${CHIP_TONES[i % CHIP_TONES.length]}`}
                          style={{ animationDelay: `${i * 30}ms` }}
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <aside className="panel h-fit">
            <h2 className="text-xl font-bold">Your upload history</h2>
            {historyLoading ? (
              <p className="muted mt-3 text-sm">Loading...</p>
            ) : history.length === 0 ? (
              <p className="muted mt-3 text-sm">
                No resumes uploaded yet. Your reports will show up here.
              </p>
            ) : (
              <ul className="mt-4 space-y-2">
                {history.map((c, i) => (
                  <li key={c.candidate_id}>
                    <Link
                      to={`/candidate/${c.candidate_id}`}
                      className="group flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-brand-50 dark:hover:bg-night-700"
                    >
                      <span
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white ${
                          i === 0 ? "bg-gradient-to-br from-brand-500 to-brand-700" : "bg-brand-300 dark:bg-night-600"
                        }`}
                      >
                        <FileIcon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold group-hover:text-brand-700 dark:group-hover:text-brand-300">
                          {c.name ?? `Candidate #${c.candidate_id}`}
                        </span>
                        <span className="muted block text-xs">
                          {new Date(c.created_at).toLocaleString()}
                        </span>
                      </span>
                      <span className="chip shrink-0 bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
                        {c.skill_count} skills
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
