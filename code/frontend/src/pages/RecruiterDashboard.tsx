import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/Navbar";
import { apiGet } from "../lib/api";

interface CandidateSummary {
  candidate_id: number;
  name: string | null;
  email: string | null;
  github_username: string | null;
  created_at: string;
  skill_count: number;
}

export function RecruiterDashboard() {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    apiGet<CandidateSummary[]>("/api/candidates")
      .then(setCandidates)
      .catch(() => setError("Could not load candidates."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return candidates;
    return candidates.filter(
      (c) =>
        c.name?.toLowerCase().includes(q) ||
        c.github_username?.toLowerCase().includes(q) ||
        c.email?.toLowerCase().includes(q)
    );
  }, [candidates, query]);

  return (
    <div className="min-h-screen bg-brand-50/40">
      <Navbar />

      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 sm:text-3xl">Candidates</h1>
            <p className="mt-1 text-sm text-slate-500">
              Every candidate who has uploaded a resume, with evidence-backed skill reports.
            </p>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, email, or GitHub username"
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 sm:w-80"
          />
        </div>

        {error && (
          <p className="mt-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        {loading ? (
          <p className="mt-8 text-sm text-slate-400">Loading candidates...</p>
        ) : filtered.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-dashed border-brand-200 bg-white p-10 text-center">
            <p className="text-slate-500">
              {candidates.length === 0
                ? "No candidates yet. Once a student uploads a resume, they'll appear here."
                : "No candidates match your search."}
            </p>
          </div>
        ) : (
          <div className="mt-6 overflow-hidden rounded-2xl border border-brand-100 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="bg-brand-50/60 text-xs uppercase tracking-wide text-brand-700">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Name</th>
                    <th className="px-4 py-3 font-semibold">GitHub</th>
                    <th className="px-4 py-3 font-semibold">Skills claimed</th>
                    <th className="px-4 py-3 font-semibold">Uploaded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100">
                  {filtered.map((c) => (
                    <tr key={c.candidate_id} className="transition hover:bg-brand-50/40">
                      <td className="px-4 py-3">
                        <Link
                          to={`/candidate/${c.candidate_id}`}
                          className="font-medium text-brand-700 hover:underline"
                        >
                          {c.name ?? `Candidate #${c.candidate_id}`}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-slate-500">
                        {c.github_username ? `@${c.github_username}` : "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-500">{c.skill_count}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
