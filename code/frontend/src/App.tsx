import { useState } from "react";

interface ExtractionResult {
  filename: string;
  status: string;
  extracted_skills?: string[];
  github_links?: string[];
  text_preview?: string;
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

interface SkillScore {
  skill: string;
  score: number;
  classification: string;
  reasons: string[];
  interview_question?: string;
}

interface ScoreResult {
  status: string;
  username?: string;
  repos_analyzed?: number;
  skill_scores?: SkillScore[];
  error?: string;
}

function extractUsername(link: string): string {
  const match = link.match(/github\.com\/([A-Za-z0-9_-]+)/i);
  return match ? match[1] : link;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [repoEvidence, setRepoEvidence] = useState<RepoEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [fingerprints, setFingerprints] = useState<Record<string, FingerprintResult>>({});
  const [fingerprinting, setFingerprinting] = useState<string | null>(null);
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null);
  const [scoring, setScoring] = useState(false);

  const fetchRepoEvidence = async (githubLink: string) => {
    const username = extractUsername(githubLink);
    setLoadingRepos(true);
    try {
      const response = await fetch(`http://127.0.0.1:8000/github/${username}/repos`);
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
        `http://127.0.0.1:8000/github/${username}/${repoName}/fingerprint`
      );
      const data = await response.json();
      setFingerprints((prev) => ({ ...prev, [repoName]: data }));
    } finally {
      setFingerprinting(null);
    }
  };

  const runScoring = async () => {
    if (!repoEvidence || repoEvidence.status !== "ok" || !result?.extracted_skills) return;
    setScoring(true);
    setScoreResult(null);
    try {
      const response = await fetch("http://127.0.0.1:8000/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: repoEvidence.username,
          skills: result.extracted_skills,
        }),
      });
      const data = await response.json();
      setScoreResult(data);
    } catch (err) {
      setScoreResult({ status: "error", error: String(err) });
    } finally {
      setScoring(false);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setRepoEvidence(null);
    setFingerprints({});
    setScoreResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/resumes/upload", {
        method: "POST",
        body: formData,
      });
      const data: ExtractionResult = await response.json();
      setResult(data);

      if (data.github_links && data.github_links.length > 0) {
        await fetchRepoEvidence(data.github_links[0]);
      }
    } catch (err) {
      setResult({ filename: file.name, status: "error", error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  const classificationColor = (classification: string) => {
    if (classification === "Strong Evidence") return "text-green-700";
    if (classification === "Good Evidence") return "text-amber-600";
    return "text-red-600";
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center px-4 py-16">
      <h1 className="text-3xl font-semibold text-slate-800">DevProof</h1>
      <p className="mt-2 text-slate-500 text-center max-w-md">
        Upload a resume PDF to extract claimed skills and GitHub evidence.
      </p>

      <div className="mt-8 bg-white rounded-lg shadow p-6 w-full max-w-md">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-600"
        />
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

          {result.github_links && result.github_links.length > 0 && (
            <div>
              <p className="font-medium text-slate-700">GitHub links:</p>
              {result.github_links.map((link) => (
                <a
                  key={link}
                  href={`https://${link.replace(/^https?:\/\//, "")}`}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-blue-600 underline text-xs"
                >
                  {link}
                </a>
              ))}
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

      {repoEvidence && repoEvidence.status === "ok" && result?.extracted_skills && (
        <div className="mt-6 w-full max-w-md">
          <button
            onClick={runScoring}
            disabled={scoring}
            className="w-full bg-green-700 text-white rounded-md py-2 disabled:opacity-40"
          >
            {scoring ? "Scoring..." : "Run Evidence Scoring"}
          </button>

          {scoreResult && scoreResult.status === "ok" && scoreResult.skill_scores && (
            <div className="mt-4 bg-white rounded-lg shadow p-6 text-sm space-y-4">
              {scoreResult.skill_scores.map((s) => (
                <div key={s.skill} className="border-b border-slate-100 pb-3">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-slate-800">{s.skill}</span>
                    <span className={`font-semibold ${classificationColor(s.classification)}`}>
                      {s.classification} ({s.score}/100)
                    </span>
                  </div>
                  <ul className="mt-1 text-xs text-slate-500 list-disc list-inside">
                    {s.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                  {s.interview_question && (
                    <p className="mt-1 text-xs text-blue-700 italic">
                      Suggested question: {s.interview_question}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {scoreResult && scoreResult.status === "error" && (
            <p className="mt-4 text-red-600 text-sm">{scoreResult.error}</p>
          )}
        </div>
      )}

      {repoEvidence && repoEvidence.status === "error" && (
        <p className="mt-4 text-red-600 text-sm">{repoEvidence.error}</p>
      )}
    </div>
  );
}

export default App;