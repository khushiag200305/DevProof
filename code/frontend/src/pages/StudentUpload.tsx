import { useEffect, useState } from "react";
import type { DragEvent } from "react";
import { Link } from "react-router-dom";
import { Hero, HeroStat } from "../components/Hero";
import { EyeIcon, FileIcon, GitHubIcon, TrashIcon, UploadIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { ApiError, apiDelete, apiGet, apiPut, apiUpload } from "../lib/api";

interface UploadResult {
  candidate_id: number;
  filename: string;
  status: string;
  name?: string | null;
  extracted_skills?: string[];
  projects?: string[];
  github_url?: string | null;
  github_username?: string | null;
  visible_to_recruiters?: boolean;
  error?: string;
}

interface CandidateSummary {
  candidate_id: number;
  name: string | null;
  github_username: string | null;
  created_at: string;
  skill_count: number;
  visible_to_recruiters?: boolean;
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
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [switching, setSwitching] = useState<number | null>(null);
  const [visibilityAnswered, setVisibilityAnswered] = useState(false);

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

  const makeVisible = async (candidateId: number) => {
    setSwitching(candidateId);
    setError(null);
    try {
      await apiPut(`/api/candidates/${candidateId}/visible`, {});
      setHistory((h) => h.map((c) => ({ ...c, visible_to_recruiters: c.candidate_id === candidateId })));
      if (result?.candidate_id === candidateId) setResult({ ...result, visible_to_recruiters: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change which resume recruiters see.");
    } finally {
      setSwitching(null);
    }
  };

  const deleteUpload = async (candidateId: number) => {
    setDeleting(true);
    setError(null);
    try {
      await apiDelete(`/api/candidates/${candidateId}`);
      setHistory((h) => h.filter((c) => c.candidate_id !== candidateId));
      if (result?.candidate_id === candidateId) setResult(null);
      loadHistory(); // the visible resume may have changed
      setConfirmDelete(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete the upload. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

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
      setVisibilityAnswered(false);
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
                    file ? "bg-emerald-500" : "bg-ink dark:bg-night-600"
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

                {result.visible_to_recruiters ? (
                  <p className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-brand-600/10 px-3 py-1.5 text-sm font-medium text-brand-700 dark:text-brand-300">
                    <EyeIcon className="h-4 w-4" /> Visible to recruiters
                  </p>
                ) : (
                  !visibilityAnswered && (
                    <div className="mt-4 rounded-lg border border-slate-200 p-4 dark:border-night-600">
                      <p className="text-sm font-medium">
                        Make this resume visible to recruiters instead of your current one?
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          onClick={() => makeVisible(result.candidate_id)}
                          disabled={switching !== null}
                          className="btn-primary px-3 py-1.5 text-xs"
                        >
                          Yes, make visible
                        </button>
                        <button onClick={() => setVisibilityAnswered(true)} className="btn-ghost px-3 py-1.5 text-xs">
                          Keep current
                        </button>
                      </div>
                    </div>
                  )
                )}

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
                {history.map((c, i) => {
                  const name = c.name ?? `Candidate #${c.candidate_id}`;
                  const confirming = confirmDelete === c.candidate_id;
                  return (
                    <li key={c.candidate_id} className="group/row relative">
                      <Link
                        to={`/candidate/${c.candidate_id}`}
                        className="group flex items-center gap-3 rounded-lg py-2.5 pl-3 pr-12 transition hover:bg-slate-100 dark:hover:bg-night-700"
                      >
                        <span
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white ${
                            i === 0 ? "bg-ink dark:bg-night-600" : "bg-slate-400 dark:bg-night-600"
                          }`}
                        >
                          <FileIcon className="h-4 w-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold group-hover:text-brand-700 dark:group-hover:text-brand-300">
                            {name}
                          </span>
                          <span className="muted block text-xs">
                            {new Date(c.created_at).toLocaleString()}
                          </span>
                          {c.visible_to_recruiters && (
                            <span className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 dark:text-brand-300">
                              <EyeIcon className="h-3.5 w-3.5" /> Visible to recruiters
                            </span>
                          )}
                        </span>
                        <span className="chip shrink-0 bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
                          {c.skill_count} skills
                        </span>
                      </Link>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(confirming ? null : c.candidate_id)}
                        aria-label={`Delete upload ${name}`}
                        title="Delete this upload"
                        className="absolute right-2 top-3 rounded-md p-2 text-ink-mute opacity-60 transition hover:bg-pop-500/10 hover:text-pop-600 hover:opacity-100 focus:opacity-100 group-hover/row:opacity-100"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                      {!c.visible_to_recruiters && (
                        <button
                          type="button"
                          onClick={() => makeVisible(c.candidate_id)}
                          disabled={switching !== null}
                          aria-label={`Make ${name} uploaded ${new Date(c.created_at).toLocaleDateString()} visible to recruiters`}
                          className="mb-2 ml-[3.75rem] rounded-md border border-slate-200 px-2.5 py-1 text-xs font-semibold text-ink-soft transition hover:border-brand-600 hover:text-brand-700 disabled:opacity-50 dark:border-night-600 dark:text-slate-300 dark:hover:text-brand-300"
                        >
                          {switching === c.candidate_id ? "Switching..." : "Make visible"}
                        </button>
                      )}
                      {confirming && (
                        <div role="alert" className="rise mx-3 mb-2 mt-1 rounded-lg border border-pop-500/30 bg-pop-500/5 p-3 text-sm">
                          <p>
                            Delete <span className="font-semibold">{name}</span>? Its report and resume PDF are removed and
                            can't be recovered.
                          </p>
                          <div className="mt-2.5 flex gap-2">
                            <button
                              type="button"
                              onClick={() => deleteUpload(c.candidate_id)}
                              disabled={deleting}
                              className="rounded-md bg-pop-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-pop-500 disabled:opacity-50"
                            >
                              {deleting ? "Deleting..." : "Delete upload"}
                            </button>
                            <button type="button" onClick={() => setConfirmDelete(null)} className="btn-ghost px-3 py-1.5 text-xs">
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
