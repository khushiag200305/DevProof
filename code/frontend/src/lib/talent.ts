/** Shapes for the recruiter talent search endpoints (backend: app/routers/talent.py). */

export type EvidenceLevel = "strong" | "good" | "claimed";

export interface TalentQuery {
  skills: string[];
  min_level: EvidenceLevel;
  match: "all" | "any";
  has_github: boolean;
  min_repos: number;
  active_months: number | null;
  text: string;
}

export const EMPTY_QUERY: TalentQuery = {
  skills: [],
  min_level: "good",
  match: "all",
  has_github: false,
  min_repos: 0,
  active_months: null,
  text: "",
};

export interface SkillMatch {
  skill: string;
  status: string | null;
  score: number | null;
}

export interface TalentResult {
  candidate_id: number;
  name: string | null;
  email: string | null;
  github_username: string | null;
  created_at: string;
  skill_count: number;
  original_repos: number;
  last_active: string | null;
  matched: SkillMatch[];
  missing: string[];
  match_score: number;
  shortlisted: boolean;
  is_new?: boolean;
}

export interface SavedSearch {
  search_id: number;
  name: string;
  query: TalentQuery;
  created_at: string;
  last_run_at: string | null;
  match_count: number;
  new_count: number;
}

export interface ShortlistEntry {
  candidate_id: number;
  name: string | null;
  email: string | null;
  github_username: string | null;
  note: string | null;
  added_at: string;
  skill_count: number;
  backed_skills: SkillMatch[];
}

export interface Comparison {
  candidates: {
    candidate_id: number;
    name: string | null;
    github_username: string | null;
    original_repos: number;
    last_active: string | null;
    backed_skills: number;
    skill_count: number;
  }[];
  rows: { skill: string; cells: ({ status: string | null; score: number | null } | null)[] }[];
}

/** Badge colours for an evidence status, matching the candidate report. */
export function statusChip(status: string | null): string {
  const s = status?.toLowerCase() ?? "";
  if (s.includes("strong")) return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300";
  if (s.includes("good")) return "bg-sun-400/25 text-amber-700 dark:text-sun-300";
  if (s.includes("not checkable")) return "bg-sky-500/10 text-sky-700 dark:text-sky-300";
  if (!status) return "bg-slate-500/10 text-ink-mute dark:text-slate-400";
  return "bg-pop-500/10 text-pop-600 dark:text-pop-400";
}

/** "Strong", "Good", "Needs proof", ... - short label for a status in tight spaces. */
export function shortStatus(status: string | null): string {
  if (!status) return "Not checked";
  if (status === "Strong Evidence") return "Strong";
  if (status === "Good Evidence") return "Good";
  if (status === "Not checkable on GitHub") return "Interview";
  return "Needs proof";
}

/** "3 days ago", "2 months ago" for a last-activity date. */
export function timeAgo(iso: string | null, now: Date = new Date()): string {
  if (!iso) return "No activity";
  const days = Math.floor((now.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (days < 1) return "Today";
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.floor(months / 12);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}
