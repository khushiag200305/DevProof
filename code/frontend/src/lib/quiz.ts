/** Shapes for the quiz endpoints (backend: app/routers/quiz.py). */

export interface QuizSkill {
  name: string;
  category: string;
  questions: number;
}

export interface QuizQuestion {
  id: string;
  skill: string;
  question: string;
  options: string[];
}

export interface GradedQuestion extends QuizQuestion {
  chosen: number | null;
  correct: number;
  is_correct: boolean;
  explanation: string;
}

export interface QuizInProgress {
  attempt_id: number;
  kind: string;
  status: "in_progress";
  skills: string[];
  questions: QuizQuestion[];
  time_limit_seconds: number | null;
  started_at: string;
  deadline: string | null;
}

export interface QuizResult {
  attempt_id: number;
  kind: string;
  status: "submitted";
  skills: string[];
  started_at: string;
  submitted_at: string;
  over_time: boolean;
  score: number;
  total: number;
  percent: number;
  per_skill: { skill: string; correct: number; total: number }[];
  questions: GradedQuestion[];
}

export interface AttemptSummary {
  attempt_id: number;
  skills: string[];
  score: number | null;
  total: number;
  started_at: string;
  submitted_at: string | null;
}
