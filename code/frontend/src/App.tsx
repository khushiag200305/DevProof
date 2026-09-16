import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

interface ExtractionResult {
  candidate_id?: number;
  filename: string;
  status: string;
  name?: string | null;
  extracted_skills?: string[];
  projects?: string[];
  github_url?: string | null;
  github_username?: string | null;
  error?: string;
}

interface Repo {
  name: string;
  language: string | null;
  is_fork: boolean;
  stars: number;
  updated_at: string;
  url: string;
}

interface RepoEvidence {
  username: string;
  status: string;
  repo_count?: number;
  repos?: Repo[];
  error?: string;
}

interface FingerprintResult {
  status: string;
  detected_technologies?: Record<string, string[]>;
  error?: string;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [githubUrlOverride, setGithubUrlOverride] = useState("");
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [repoEvidence, setRepoEvidence] = useState<RepoEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [fingerprints, setFingerprints] = useState<Record<string, FingerprintResult>>({});
  const [fingerprinting, setFingerprinting] = useState<string | null>(null);

  const fetchRepoEvidence = async (username: string) => {
    setLoadingRepos(true);
    try {
      const response = await fetch(`${API_BASE}/github/${username}/repos`);
      const data = await response.json();
      setRepoEvidence(data);
    } catch (err) {
      setRepoEvidence({ username, status: "error", error: String(err) });
    } finally {
      setLoadingRepos(false);
    }
  };

  const checkFingerprint = async (username: string, repoName: string) => {
    setFingerprinting(repoName);
    try {
      const response = await fetch(
        `${API_BASE}/github/${username}/${repoName}/fingerprint`
      );
      const data = await response.json();
      setFingerprints((prev) => ({ ...prev, [repoName]: data }));
    } finally {
      setFingerprinting(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setRepoEvidence(null);
    setFingerprints({});

    const formData = new FormData();
    formData.append("file", file);
    if (githubUrlOverride.trim()) {
      formData.append("github_url_override", githubUrlOverride.trim());
    }

    try {
      const response = await fetch(`${API_BASE}/api/resume/upload`, {
        method: "POST",
        body: formData,
      });
      const data: ExtractionResult = await response.json();
      setResult(data);

      if (data.github_username) {
        await fetchRepoEvidence(data.github_username);
      }
    } catch (err) {
      setResult({ filename: file.name, status: "error", error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center px-4 py-16">
      <h1 className="text-3xl font-semibold text-slate-800">DevProof</h1>
      <p className="mt-2 text-slate-500 text-center max-w-md">
        Upload a resume PDF to extract claimed skills and GitHub evidence.
      </p>

      <div className="mt-8 bg-white rounded-lg shadow p-6 w-full max-w-md">
        <label htmlFor="resume-file" className="block text-sm font-medium text-slate-700 mb-1">
          Resume PDF
        </label>
        <input
          id="resume-file"
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-600"
        />

        <label htmlFor="github-override" className="block text-sm font-medium text-slate-700 mt-4 mb-1">
          GitHub URL (optional override)
        </label>
        <input
          id="github-override"
          type="text"
          value={githubUrlOverride}
          onChange={(e) => setGithubUrlOverride(e.target.value)}
          placeholder="github.com/username"
          className="block w-full text-sm text-slate-600 border border-slate-200 rounded-md px-3 py-2"
        />
        <p className="mt-1 text-xs text-slate-400">
          PDF extraction can miss GitHub links on multi-column or graphic-heavy
          resumes - set this if the detected link (if any) looks wrong.
        </p>

        <button
          onClick={handleSubmit}
          disabled={!file || loading}
          className="mt-4 w-full bg-slate-800 text-white rounded-md py-2 disabled:opacity-40"
        >
          {loading ? "Analyzing..." : "Upload & Analyze"}
        </button>
      </div>

      {result && (
        <div className="mt-6 bg-white rounded-lg shadow p-6 w-full max-w-md text-sm">
          <p className="font-medium text-slate-700">{result.filename}</p>
          <p className="text-slate-500 mb-3">Status: {result.status}</p>

          {result.error && <p className="text-red-600">{result.error}</p>}

          {result.name && (
            <p className="mb-3">
              <span className="font-medium text-slate-700">Candidate:</span> {result.name}
            </p>
          )}

          {result.extracted_skills && (
            <div className="mb-3">
              <p className="font-medium text-slate-700">Detected skills:</p>
              <div className="flex flex-wrap gap-2 mt-1">
                {result.extracted_skills.length > 0 ? (
                  result.extracted_skills.map((skill) => (
                    <span
                      key={skill}
                      className="bg-slate-100 text-slate-700 rounded px-2 py-1 text-xs"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-slate-400 text-xs">None detected</span>
                )}
              </div>
            </div>
          )}

          {result.projects && result.projects.length > 0 && (
            <div className="mb-3">
              <p className="font-medium text-slate-700">Detected projects:</p>
              <ul className="mt-1 list-disc list-inside text-slate-600">
                {result.projects.map((project) => (
                  <li key={project}>{project}</li>
                ))}
              </ul>
            </div>
          )}

          {result.github_url && (
            <div>
              <p className="font-medium text-slate-700">GitHub:</p>
              <a
                href={`https://${result.github_url.replace(/^https?:\/\//, "")}`}
                target="_blank"
                rel="noreferrer"
                className="block text-blue-600 underline text-xs"
              >
                {result.github_url}
              </a>
            </div>
          )}
        </div>
      )}

      {loadingRepos && (
        <p className="mt-4 text-slate-400 text-sm">Fetching GitHub repositories...</p>
      )}

      {repoEvidence && repoEvidence.status === "ok" && (
        <div className="mt-6 bg-white rounded-lg shadow p-6 w-full max-w-md text-sm">
          <p className="font-medium text-slate-700">
            @{repoEvidence.username}'s public repos ({repoEvidence.repo_count})
          </p>
          <div className="mt-3 space-y-2">
            {repoEvidence.repos && repoEvidence.repos.length > 0 ? (
              repoEvidence.repos.map((repo) => (
                <div key={repo.name} className="border-b border-slate-100 pb-2">
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 underline font-medium"
                  >
                    {repo.name}
                  </a>
                  <div className="text-xs text-slate-500 flex gap-2 flex-wrap mt-1">
                    <span>{repo.language ?? "No language detected"}</span>
                    {repo.is_fork && <span className="text-amber-600">Fork</span>}
                    <span>⭐ {repo.stars}</span>
                    <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
                  </div>

                  <button
                    onClick={() => checkFingerprint(repoEvidence.username, repo.name)}
                    disabled={fingerprinting === repo.name}
                    className="mt-1 text-xs text-slate-500 underline"
                  >
                    {fingerprinting === repo.name ? "Checking..." : "Check tech fingerprint"}
                  </button>

                  {fingerprints[repo.name] && (
                    <div className="mt-1 text-xs">
                      {fingerprints[repo.name].detected_technologies &&
                      Object.keys(fingerprints[repo.name].detected_technologies!).length > 0 ? (
                        Object.entries(fingerprints[repo.name].detected_technologies!).map(
                          ([tech, items]) => (
                            <div key={tech} className="text-green-700">
                              ✓ {tech}: {items.join(", ")}
                            </div>
                          )
                        )
                      ) : (
                        <span className="text-slate-400">No fingerprint matches found</span>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-slate-400 text-xs">No public repositories found.</p>
            )}
          </div>
        </div>
      )}

      {repoEvidence && repoEvidence.status === "error" && (
        <p className="mt-4 text-red-600 text-sm">{repoEvidence.error}</p>
      )}
    </div>
  );
}

export default App;