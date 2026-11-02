import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { Hero, HeroStat } from "../components/Hero";
import { GitHubIcon, SearchIcon } from "../components/Icons";
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

type Sort = "newest" | "skills" | "name";

const SORTS: { id: Sort; label: string }[] = [
  { id: "newest", label: "Newest" },
  { id: "skills", label: "Most skills" },
  { id: "name", label: "Name" },
];

export function RecruiterDashboard() {
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("newest");

  useEffect(() => {
    apiGet<CandidateSummary[]>("/api/candidates")
      .then(setCandidates)
      .catch(() => setError("Could not load candidates."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = q
      ? candidates.filter(
          (c) =>
            c.name?.toLowerCase().includes(q) ||
            c.github_username?.toLowerCase().includes(q) ||
            c.email?.toLowerCase().includes(q)
        )
      : [...candidates];
    return matches.sort((a, b) =>
      sort === "skills"
        ? b.skill_count - a.skill_count
        : sort === "name"
          ? (a.name ?? "").localeCompare(b.name ?? "")
          : new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [candidates, query, sort]);

  const withGithub = candidates.filter((c) => c.github_username).length;
  const maxSkills = Math.max(1, ...candidates.map((c) => c.skill_count));

  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero
          seed="candidates"
          aside={
            <div className="grid grid-cols-2 gap-3">
              <HeroStat value={loading ? "-" : candidates.length} label="Candidates" />
              <HeroStat value={loading ? "-" : withGithub} label="With a GitHub profile" />
            </div>
          }
        >
          <h1 className="text-4xl font-extrabold sm:text-5xl">Candidates</h1>
          <p className="mt-3 text-white/90 sm:text-lg">
            Every candidate who has uploaded a resume, with evidence-backed skill reports.
          </p>
          <div className="relative mt-6 max-w-lg">
            <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-brand-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, email, or GitHub username"
              aria-label="Search candidates"
              className="w-full rounded-full border-0 bg-white py-3.5 pl-12 pr-4 text-sm text-ink shadow-lg shadow-black/10 placeholder:text-ink-mute focus:outline-none focus:ring-4 focus:ring-white/40"
            />
          </div>
        </Hero>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <p className="muted text-sm font-medium">
            {loading ? "" : `${filtered.length} of ${candidates.length} shown`}
          </p>
          <div role="group" aria-label="Sort candidates" className="flex gap-1 rounded-full bg-white p-1 shadow-sm ring-1 ring-brand-100 dark:bg-night-800 dark:ring-night-600">
            {SORTS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSort(s.id)}
                aria-pressed={sort === s.id}
                className={`rounded-full px-3.5 py-1.5 text-sm font-semibold transition ${
                  sort === s.id
                    ? "bg-brand-600 text-white shadow"
                    : "text-ink-soft hover:bg-brand-50 dark:text-slate-300 dark:hover:bg-night-700"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="alert mt-6">{error}</p>}

        {loading ? (
          <p className="muted mt-8 text-sm">Loading candidates...</p>
        ) : filtered.length === 0 ? (
          <div className="mt-6 rounded-2xl border-2 border-dashed border-brand-200 p-12 text-center dark:border-night-600">
            <p className="font-display text-xl font-bold">
              {candidates.length === 0 ? "No candidates yet" : "Nobody matches that search"}
            </p>
            <p className="muted mt-2">
              {candidates.length === 0
                ? "No candidates yet. Once a student uploads a resume, they'll appear here."
                : "No candidates match your search."}
            </p>
          </div>
        ) : (
          <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((c, i) => {
              const name = c.name ?? `Candidate #${c.candidate_id}`;
              return (
                <li
                  key={c.candidate_id}
                  className="rise group relative flex flex-col rounded-2xl border border-brand-100 bg-white p-5 transition hover:-translate-y-1 hover:border-brand-300 hover:shadow-xl hover:shadow-brand-600/10 dark:border-night-600 dark:bg-night-800 dark:hover:border-brand-500"
                  style={{ animationDelay: `${Math.min(i, 12) * 35}ms` }}
                >
                  <div className="flex items-center gap-3">
                    <Avatar name={name} />
                    <div className="min-w-0">
                      <Link
                        to={`/candidate/${c.candidate_id}`}
                        className="block truncate font-display text-lg font-bold after:absolute after:inset-0 after:rounded-2xl group-hover:text-brand-700 dark:group-hover:text-brand-300"
                      >
                        {name}
                      </Link>
                      <p className="muted flex items-center gap-1.5 truncate text-sm">
                        <GitHubIcon className="h-3.5 w-3.5 shrink-0" />
                        {c.github_username ? `@${c.github_username}` : "No GitHub"}
                      </p>
                    </div>
                  </div>
                  <div className="mt-5">
                    <div className="flex items-baseline justify-between text-sm">
                      <span className="font-semibold">{c.skill_count} skills claimed</span>
                      <span className="muted text-xs">{new Date(c.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-brand-50 dark:bg-night-700">
                      <div
                        className="bar-fill h-full rounded-full bg-gradient-to-r from-brand-500 via-pop-500 to-sun-400"
                        style={{ width: `${Math.max(6, (c.skill_count / maxSkills) * 100)}%` }}
                      />
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </div>
  );
}
