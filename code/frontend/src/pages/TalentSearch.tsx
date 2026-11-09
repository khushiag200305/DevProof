import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { Hero, HeroStat } from "../components/Hero";
import { ColumnsIcon, GitHubIcon, SearchIcon, StarIcon, XIcon } from "../components/Icons";
import { Navbar } from "../components/Navbar";
import { ApiError, apiDelete, apiGet, apiPost, apiPut } from "../lib/api";
import {
  EMPTY_QUERY,
  shortStatus,
  statusChip,
  timeAgo,
  type Comparison,
  type EvidenceLevel,
  type SavedSearch,
  type ShortlistEntry,
  type TalentQuery,
  type TalentResult,
} from "../lib/talent";

const LEVELS: { id: EvidenceLevel; label: string }[] = [
  { id: "strong", label: "Strong" },
  { id: "good", label: "Good+" },
  { id: "claimed", label: "On resume" },
];

const ACTIVITY: { value: string; label: string }[] = [
  { value: "", label: "Any time" },
  { value: "3", label: "Last 3 months" },
  { value: "6", label: "Last 6 months" },
  { value: "12", label: "Last 12 months" },
];

const MAX_COMPARE = 4;

type Tab = "search" | "shortlist";

/** A row of mutually exclusive buttons, e.g. the evidence level. */
function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { id: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <p className="label">{label}</p>
      <div role="group" aria-label={label} className="mt-1.5 grid auto-cols-fr grid-flow-col gap-1 rounded-md bg-slate-100 p-1 dark:bg-night-700">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            aria-pressed={value === o.id}
            onClick={() => onChange(o.id)}
            className={`rounded px-2 py-1.5 text-xs font-semibold transition ${
              value === o.id
                ? "bg-white text-ink shadow-sm dark:bg-night-600 dark:text-white"
                : "text-ink-mute hover:text-ink dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function SkillChip({ skill, status, score }: { skill: string; status: string | null; score: number | null }) {
  return (
    <span className={`chip inline-flex items-center gap-1 py-1 ${statusChip(status)}`}>
      {skill}
      <span className="font-medium opacity-75">
        {shortStatus(status)}
        {score !== null && ` ${score}`}
      </span>
    </span>
  );
}

function Empty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-slate-200 p-10 text-center dark:border-night-600">
      <p className="text-lg font-semibold">{title}</p>
      <p className="muted mx-auto mt-1 max-w-md text-sm">{children}</p>
    </div>
  );
}

function CompareView({ data, onClose }: { data: Comparison; onClose: () => void }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }, [data]);
  return (
    <section ref={ref} aria-label="Compare candidates" className="panel rise mt-6 scroll-mt-24 overflow-x-auto p-0 sm:p-0">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-night-600">
        <h2 className="text-xl font-bold">Compare candidates</h2>
        <button onClick={onClose} className="btn-ghost px-3 py-1.5 text-xs">
          <XIcon className="h-3.5 w-3.5" /> Close
        </button>
      </div>
      <table className="w-full min-w-[36rem] text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left dark:border-night-600">
            <th className="w-48 px-5 py-3 font-semibold text-ink-mute dark:text-slate-400">Skill</th>
            {data.candidates.map((c) => (
              <th key={c.candidate_id} className="px-4 py-3 align-top">
                <Link to={`/candidate/${c.candidate_id}`} className="font-semibold hover:text-brand-700 dark:hover:text-brand-300">
                  {c.name ?? `Candidate #${c.candidate_id}`}
                </Link>
                <p className="muted mt-0.5 text-xs font-normal">
                  {c.backed_skills} of {c.skill_count} skills backed, {c.original_repos} repos
                </p>
                <p className="muted text-xs font-normal">Active {timeAgo(c.last_active).toLowerCase()}</p>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.skill} className="border-b border-slate-100 last:border-0 dark:border-night-700">
              <th scope="row" className="px-5 py-2.5 text-left font-medium">
                {row.skill}
              </th>
              {row.cells.map((cell, i) => (
                <td key={i} className="px-4 py-2.5">
                  {cell ? (
                    <span className={`chip py-1 ${statusChip(cell.status)}`}>
                      {shortStatus(cell.status)}
                      {cell.score !== null && ` ${cell.score}`}
                    </span>
                  ) : (
                    <span className="muted text-xs">Not on resume</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function TalentSearch() {
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState<TalentQuery>(EMPTY_QUERY);
  const [skillInput, setSkillInput] = useState("");
  const [knownSkills, setKnownSkills] = useState<string[]>([]);
  const [results, setResults] = useState<TalentResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [activeSaved, setActiveSaved] = useState<number | null>(null);
  const [saveName, setSaveName] = useState<string | null>(null);
  const [shortlist, setShortlist] = useState<ShortlistEntry[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);

  const loadSaved = () =>
    apiGet<SavedSearch[]>("/api/talent/saved-searches").then(setSaved).catch(() => setSaved([]));
  const loadShortlist = () =>
    apiGet<ShortlistEntry[]>("/api/talent/shortlist")
      .then((entries) => {
        setShortlist(entries);
        setNotes(Object.fromEntries(entries.map((e) => [e.candidate_id, e.note ?? ""])));
      })
      .catch(() => setShortlist([]));

  const runSearch = async (q: TalentQuery) => {
    setSearching(true);
    setError(null);
    try {
      setResults(await apiPost<TalentResult[]>("/api/talent/search", q));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    apiGet<string[]>("/api/talent/skills").then(setKnownSkills).catch(() => setKnownSkills([]));
    loadSaved();
    loadShortlist();
    runSearch(EMPTY_QUERY);
  }, []);

  const update = (patch: Partial<TalentQuery>) => {
    setQuery((q) => ({ ...q, ...patch }));
    setActiveSaved(null);
  };

  const addSkill = (raw: string) => {
    const name = knownSkills.find((s) => s.toLowerCase() === raw.trim().toLowerCase()) ?? raw.trim();
    if (!name || query.skills.some((s) => s.toLowerCase() === name.toLowerCase())) {
      setSkillInput("");
      return;
    }
    update({ skills: [...query.skills, name] });
    setSkillInput("");
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const pending = skillInput.trim();
    const q =
      pending && !query.skills.some((s) => s.toLowerCase() === pending.toLowerCase())
        ? { ...query, skills: [...query.skills, knownSkills.find((s) => s.toLowerCase() === pending.toLowerCase()) ?? pending] }
        : query;
    setQuery(q);
    setSkillInput("");
    runSearch(q);
  };

  const saveSearch = async () => {
    if (!saveName?.trim()) return;
    try {
      const created = await apiPost<SavedSearch>("/api/talent/saved-searches", { name: saveName.trim(), query });
      setSaved((list) => [created, ...list]);
      setActiveSaved(created.search_id);
      setSaveName(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the search.");
    }
  };

  const openSaved = async (s: SavedSearch) => {
    setTab("search");
    setQuery(s.query);
    setActiveSaved(s.search_id);
    setSearching(true);
    setError(null);
    try {
      const run = await apiPost<{ search: SavedSearch; results: TalentResult[] }>(
        `/api/talent/saved-searches/${s.search_id}/run`
      );
      setResults(run.results);
      setSaved((list) => list.map((x) => (x.search_id === s.search_id ? { ...x, new_count: 0, match_count: run.results.length } : x)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run the saved search.");
    } finally {
      setSearching(false);
    }
  };

  const deleteSaved = async (s: SavedSearch) => {
    await apiDelete(`/api/talent/saved-searches/${s.search_id}`).catch(() => undefined);
    setSaved((list) => list.filter((x) => x.search_id !== s.search_id));
    if (activeSaved === s.search_id) setActiveSaved(null);
  };

  const toggleStar = async (candidateId: number, starred: boolean) => {
    setResults((rs) => rs?.map((r) => (r.candidate_id === candidateId ? { ...r, shortlisted: !starred } : r)) ?? rs);
    try {
      if (starred) await apiDelete(`/api/talent/shortlist/${candidateId}`);
      else await apiPut(`/api/talent/shortlist/${candidateId}`, { note: null });
      loadShortlist();
    } catch {
      setResults((rs) => rs?.map((r) => (r.candidate_id === candidateId ? { ...r, shortlisted: starred } : r)) ?? rs);
    }
  };

  const saveNote = async (candidateId: number) => {
    await apiPut(`/api/talent/shortlist/${candidateId}`, { note: notes[candidateId] ?? "" }).catch(() => undefined);
    loadShortlist();
  };

  const toggleSelected = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= MAX_COMPARE ? s : [...s, id]));

  const openComparison = async () => {
    try {
      setComparison(await apiGet<Comparison>(`/api/talent/compare?ids=${selected.join(",")}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not compare these candidates.");
    }
  };

  const suggestions = knownSkills.filter(
    (s) => !query.skills.some((q) => q.toLowerCase() === s.toLowerCase())
  );
  const newTotal = saved.reduce((n, s) => n + s.new_count, 0);

  return (
    <div className="min-h-screen pb-24">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero
          seed="talent"
          aside={
            <div className="grid grid-cols-2 gap-3">
              <HeroStat value={saved.length} label="Saved searches" />
              <HeroStat value={shortlist.length} label="Shortlisted" />
            </div>
          }
        >
          <h1 className="text-4xl font-bold sm:text-5xl">Talent search</h1>
          <p className="mt-3 max-w-xl text-white/80 sm:text-lg">
            Find students by the skills their GitHub work proves, not just the keywords on their resume.
          </p>
        </Hero>

        <div role="tablist" aria-label="Talent search sections" className="mt-6 flex gap-1 border-b border-slate-200 dark:border-night-600">
          {(
            [
              { id: "search", label: "Search", count: results?.length },
              { id: "shortlist", label: "Shortlist", count: shortlist.length },
            ] as { id: Tab; label: string; count?: number }[]
          ).map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`-mb-px flex items-center gap-2 border-b-[3px] px-4 py-3 text-sm font-semibold transition ${
                tab === t.id
                  ? "border-brand-600 text-ink dark:border-brand-400 dark:text-white"
                  : "border-transparent text-ink-mute hover:text-ink dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              {t.label}
              {t.count !== undefined && (
                <span className={`rounded px-1.5 py-0.5 text-xs ${tab === t.id ? "bg-brand-600 text-white" : "bg-slate-200/70 text-ink-soft dark:bg-night-600 dark:text-slate-300"}`}>
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {error && <p className="alert mt-4">{error}</p>}

        {/* Search: filters and saved searches on the left, results on the right. */}
        <div role="tabpanel" className={tab === "search" ? "mt-6 grid gap-6 lg:grid-cols-[20rem_1fr]" : "hidden"}>
          <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
            <form onSubmit={onSubmit} className="panel space-y-5 p-5 sm:p-5">
              <div>
                <label htmlFor="skill-input" className="label">
                  Skills
                </label>
                <div className="mt-1.5 flex gap-2">
                  <input
                    id="skill-input"
                    list="known-skills"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && skillInput.trim()) {
                        e.preventDefault();
                        addSkill(skillInput);
                      }
                    }}
                    placeholder="e.g. Python"
                    className="field mt-0"
                  />
                  <button type="button" onClick={() => addSkill(skillInput)} disabled={!skillInput.trim()} className="btn-ghost shrink-0 px-3">
                    Add
                  </button>
                </div>
                <datalist id="known-skills">
                  {suggestions.map((s) => (
                    <option key={s} value={s} />
                  ))}
                </datalist>
                {query.skills.length > 0 && (
                  <ul className="mt-2.5 flex flex-wrap gap-1.5">
                    {query.skills.map((s) => (
                      <li key={s}>
                        <button
                          type="button"
                          onClick={() => update({ skills: query.skills.filter((x) => x !== s) })}
                          aria-label={`Remove ${s}`}
                          className="chip inline-flex items-center gap-1 bg-ink py-1 text-white dark:bg-white dark:text-ink"
                        >
                          {s}
                          <XIcon className="h-3 w-3" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <Segmented label="Evidence needed" options={LEVELS} value={query.min_level} onChange={(v) => update({ min_level: v })} />
              <Segmented
                label="Match"
                options={[
                  { id: "all", label: "All skills" },
                  { id: "any", label: "Any skill" },
                ]}
                value={query.match}
                onChange={(v) => update({ match: v })}
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="active-months" className="label">
                    Active on GitHub
                  </label>
                  <select
                    id="active-months"
                    value={query.active_months ?? ""}
                    onChange={(e) => update({ active_months: e.target.value ? Number(e.target.value) : null })}
                    className="field"
                  >
                    {ACTIVITY.map((a) => (
                      <option key={a.value} value={a.value}>
                        {a.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="min-repos" className="label">
                    Min. own repos
                  </label>
                  <input
                    id="min-repos"
                    type="number"
                    min={0}
                    max={100}
                    value={query.min_repos}
                    onChange={(e) => update({ min_repos: Math.max(0, Number(e.target.value) || 0) })}
                    className="field"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2.5 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={query.has_github}
                  onChange={(e) => update({ has_github: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300 accent-brand-600"
                />
                Has a GitHub profile
              </label>

              <div>
                <label htmlFor="text-filter" className="label">
                  Name, email or GitHub username
                </label>
                <input
                  id="text-filter"
                  value={query.text}
                  onChange={(e) => update({ text: e.target.value })}
                  placeholder="Optional"
                  className="field"
                />
              </div>

              <div className="flex gap-2 border-t border-slate-200 pt-4 dark:border-night-600">
                <button type="submit" disabled={searching} className="btn-primary flex-1">
                  <SearchIcon className="h-4 w-4" />
                  {searching ? "Searching..." : "Search"}
                </button>
                <button type="button" onClick={() => setSaveName(saveName === null ? "" : null)} className="btn-ghost">
                  Save search
                </button>
              </div>

              {saveName !== null && (
                <div className="rise flex gap-2">
                  <input
                    aria-label="Saved search name"
                    autoFocus
                    value={saveName}
                    maxLength={80}
                    onChange={(e) => setSaveName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        saveSearch();
                      }
                    }}
                    placeholder="e.g. Backend interns 2026"
                    className="field mt-0"
                  />
                  <button type="button" onClick={saveSearch} disabled={!saveName.trim()} className="btn-primary shrink-0 px-3">
                    Save
                  </button>
                </div>
              )}
            </form>

            <section aria-label="Saved searches" className="panel p-5 sm:p-5">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold">Saved searches</h2>
                {newTotal > 0 && (
                  <span className="chip bg-brand-600 py-1 text-white">{newTotal} new</span>
                )}
              </div>
              {saved.length === 0 ? (
                <p className="muted mt-2 text-sm">Save a search to re-run it later and see who's new since you last looked.</p>
              ) : (
                <ul className="mt-3 space-y-1">
                  {saved.map((s) => (
                    <li key={s.search_id} className="group flex items-center gap-1">
                      <button
                        onClick={() => openSaved(s)}
                        className={`flex min-w-0 flex-1 items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition ${
                          activeSaved === s.search_id
                            ? "bg-slate-100 dark:bg-night-700"
                            : "hover:bg-slate-100 dark:hover:bg-night-700"
                        }`}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-semibold">{s.name}</span>
                          <span className="muted block text-xs">
                            {s.match_count} {s.match_count === 1 ? "match" : "matches"}
                          </span>
                        </span>
                        {s.new_count > 0 && (
                          <span className="chip shrink-0 bg-brand-600 text-white">{s.new_count} new</span>
                        )}
                      </button>
                      <button
                        onClick={() => deleteSaved(s)}
                        aria-label={`Delete saved search ${s.name}`}
                        className="rounded p-1.5 text-ink-mute opacity-60 transition hover:bg-pop-500/10 hover:text-pop-600 hover:opacity-100"
                      >
                        <XIcon className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>

          <div className="min-w-0">
            <p className="muted mb-3 text-sm">
              {results === null
                ? "Loading..."
                : query.skills.length === 0
                  ? `${results.length} candidates. Add skills to rank them by proven evidence.`
                  : `${results.length} ${results.length === 1 ? "candidate matches" : "candidates match"}, best evidence first.`}
            </p>

            {results !== null && results.length === 0 ? (
              <Empty title="Nobody matches yet">
                Try "Any skill" instead of "All skills", or lower the evidence needed to "On resume".
              </Empty>
            ) : (
              <ul className="space-y-3">
                {results?.map((r) => {
                  const name = r.name ?? `Candidate #${r.candidate_id}`;
                  const picked = selected.includes(r.candidate_id);
                  return (
                    <li
                      key={r.candidate_id}
                      aria-label={name}
                      className={`panel flex flex-col gap-4 p-4 transition sm:flex-row sm:items-center sm:p-5 ${
                        picked ? "border-ink dark:border-white" : ""
                      }`}
                    >
                      <div className="flex min-w-0 flex-1 gap-3.5">
                        <Avatar name={name} />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Link to={`/candidate/${r.candidate_id}`} className="truncate text-lg font-semibold hover:text-brand-700 dark:hover:text-brand-300">
                              {name}
                            </Link>
                            {r.is_new && <span className="chip bg-brand-600 text-white">New</span>}
                          </div>
                          <p className="muted flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
                            <span className="inline-flex items-center gap-1">
                              <GitHubIcon className="h-3 w-3" />
                              {r.github_username ? `@${r.github_username}` : "No GitHub"}
                            </span>
                            <span>{r.original_repos} own repos</span>
                            <span>Active {timeAgo(r.last_active).toLowerCase()}</span>
                          </p>
                          {(r.matched.length > 0 || r.missing.length > 0) && (
                            <div className="mt-2.5 flex flex-wrap gap-1.5">
                              {r.matched.map((m) => (
                                <SkillChip key={m.skill} {...m} />
                              ))}
                              {r.missing.map((m) => (
                                <span key={m} className="chip bg-slate-500/10 py-1 text-ink-mute line-through dark:text-slate-500">
                                  {m}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 sm:gap-4">
                        {query.skills.length > 0 && (
                          <div className="w-14 text-right">
                            <p className="text-2xl font-bold tabular-nums leading-none">{r.match_score}</p>
                            <p className="muted mt-1 text-[11px] font-medium">match</p>
                          </div>
                        )}
                        <button
                          onClick={() => toggleStar(r.candidate_id, r.shortlisted)}
                          aria-label={r.shortlisted ? `Remove ${name} from shortlist` : `Add ${name} to shortlist`}
                          aria-pressed={r.shortlisted}
                          title={r.shortlisted ? "Shortlisted" : "Add to shortlist"}
                          className={`rounded-md p-2 transition ${
                            r.shortlisted ? "text-sun-500" : "text-ink-mute hover:bg-slate-100 hover:text-ink dark:hover:bg-night-700 dark:hover:text-white"
                          }`}
                        >
                          <StarIcon filled={r.shortlisted} className="h-5 w-5" />
                        </button>
                        <label className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-ink-soft dark:text-slate-300">
                          <input
                            type="checkbox"
                            checked={picked}
                            disabled={!picked && selected.length >= MAX_COMPARE}
                            onChange={() => toggleSelected(r.candidate_id)}
                            className="h-4 w-4 accent-brand-600"
                          />
                          Compare
                        </label>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {comparison && <CompareView data={comparison} onClose={() => setComparison(null)} />}
          </div>
        </div>

        {/* Shortlist: starred candidates with private notes. */}
        <div role="tabpanel" className={tab === "shortlist" ? "mt-6" : "hidden"}>
          {shortlist.length === 0 ? (
            <Empty title="Your shortlist is empty">Star candidates in the search results to keep them here with your notes.</Empty>
          ) : (
            <ul className="grid gap-4 md:grid-cols-2">
              {shortlist.map((e) => {
                const name = e.name ?? `Candidate #${e.candidate_id}`;
                return (
                  <li key={e.candidate_id} aria-label={`${name} (shortlisted)`} className="panel flex flex-col p-5 sm:p-5">
                    <div className="flex items-start gap-3">
                      <Avatar name={name} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/candidate/${e.candidate_id}`} className="text-lg font-semibold hover:text-brand-700 dark:hover:text-brand-300">
                          {name}
                        </Link>
                        <p className="muted text-xs">
                          {e.backed_skills.length} of {e.skill_count} skills backed by GitHub
                        </p>
                      </div>
                      <button
                        onClick={() => toggleStar(e.candidate_id, true)}
                        aria-label={`Remove ${name} from shortlist`}
                        className="rounded-md p-2 text-sun-500 transition hover:bg-slate-100 dark:hover:bg-night-700"
                      >
                        <StarIcon filled className="h-5 w-5" />
                      </button>
                    </div>
                    {e.backed_skills.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {e.backed_skills.slice(0, 8).map((m) => (
                          <SkillChip key={m.skill} {...m} />
                        ))}
                      </div>
                    )}
                    <label htmlFor={`note-${e.candidate_id}`} className="label mt-4">
                      Your note
                    </label>
                    <textarea
                      id={`note-${e.candidate_id}`}
                      rows={2}
                      maxLength={2000}
                      value={notes[e.candidate_id] ?? ""}
                      onChange={(ev) => setNotes((n) => ({ ...n, [e.candidate_id]: ev.target.value }))}
                      placeholder="Only you can see this"
                      className="field resize-y"
                    />
                    {(notes[e.candidate_id] ?? "") !== (e.note ?? "") && (
                      <button onClick={() => saveNote(e.candidate_id)} className="btn-primary mt-2 self-start px-3 py-1.5 text-xs">
                        Save note
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </main>

      {tab === "search" && selected.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 backdrop-blur dark:border-night-600 dark:bg-night-800/95">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <p className="text-sm font-medium">
              {selected.length} selected
              <span className="muted"> (up to {MAX_COMPARE})</span>
            </p>
            <div className="flex gap-2">
              <button onClick={() => { setSelected([]); setComparison(null); }} className="btn-ghost">
                Clear
              </button>
              <button onClick={openComparison} disabled={selected.length < 2} className="btn-primary">
                <ColumnsIcon className="h-4 w-4" />
                Compare {selected.length}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
