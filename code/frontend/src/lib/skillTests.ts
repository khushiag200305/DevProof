/** Shapes for the skill test endpoints (backend: app/routers/skill_tests.py). */
import type { QuizResult } from "./quiz";

export type TestStatus = "waiting" | "in_progress" | "done" | "late" | "timed_out" | "expired";

export interface SkillTest {
  test_id: number;
  skills: string[];
  question_count: number;
  time_limit_minutes: number;
  message: string | null;
  created_at: string;
  expires_at: string;
  status: TestStatus;
  score: number | null;
  total: number;
  submitted_at: string | null;
  attempt_id: number | null;
  per_skill?: { skill: string; correct: number; total: number }[];
  /** Recruiter views */
  student_name?: string | null;
  candidate_id?: number | null;
  /** Student views */
  from_domain?: string | null;
}

export interface SkillTestResult extends SkillTest {
  result: QuizResult;
}

export const STATUS_LABEL: Record<TestStatus, string> = {
  waiting: "Not started",
  in_progress: "In progress",
  done: "Done",
  late: "Done, after the time limit",
  timed_out: "Time ran out",
  expired: "Expired",
};

export const STATUS_STYLE: Record<TestStatus, string> = {
  waiting: "bg-slate-500/10 text-ink-soft dark:text-slate-300",
  in_progress: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  done: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  late: "bg-sun-400/25 text-amber-700 dark:text-sun-300",
  timed_out: "bg-pop-500/10 text-pop-600 dark:text-pop-400",
  expired: "bg-slate-500/10 text-ink-mute dark:text-slate-400",
};

/** The latest finished skill test result for one skill. */
export interface SkillTestScore {
  correct: number;
  total: number;
  late: boolean;
  date: string | null;
}

/** Latest finished score per skill, from tests listed newest first. */
export function latestTestScores(tests: SkillTest[]): Record<string, SkillTestScore> {
  const out: Record<string, SkillTestScore> = {};
  for (const t of tests) {
    for (const p of t.per_skill ?? []) {
      if (!(p.skill in out)) {
        out[p.skill] = { correct: p.correct, total: p.total, late: t.status === "late", date: t.submitted_at };
      }
    }
  }
  return out;
}

