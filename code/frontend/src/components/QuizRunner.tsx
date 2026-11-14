import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiPost } from "../lib/api";
import type { QuizInProgress, QuizResult } from "../lib/quiz";

function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/**
 * Takes one quiz: a question at a time, with a progress bar and an
 * optional countdown that submits automatically when time runs out.
 */
export function QuizRunner({
  attempt,
  onDone,
}: {
  attempt: QuizInProgress;
  onDone: (result: QuizResult) => void;
}) {
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number | null>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [left, setLeft] = useState<number | null>(() =>
    attempt.deadline ? (new Date(attempt.deadline).getTime() - Date.now()) / 1000 : null
  );
  // The latest answers, readable from the timer's auto-submit.
  const answersRef = useRef<Record<string, number | null>>({});
  const submittedRef = useRef(false);

  const submit = useCallback(async () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      onDone(await apiPost<QuizResult>(`/api/quiz/attempts/${attempt.attempt_id}/submit`, { answers: answersRef.current }));
    } catch (err) {
      submittedRef.current = false;
      setError(err instanceof ApiError ? err.message : "Could not submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }, [attempt.attempt_id, onDone]);

  useEffect(() => {
    if (!attempt.deadline) return;
    const deadline = new Date(attempt.deadline).getTime();
    const timer = setInterval(() => {
      const remaining = (deadline - Date.now()) / 1000;
      setLeft(remaining);
      if (remaining <= 0) {
        clearInterval(timer);
        submit();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [attempt.deadline, submit]);

  const q = attempt.questions[index];
  const total = attempt.questions.length;
  const answered = Object.values(answers).filter((a) => a !== null && a !== undefined).length;
  const last = index === total - 1;

  return (
    <section aria-label="Quiz" className="panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold">
          Question {index + 1} of {total}
        </p>
        {left !== null && (
          <p
            aria-label="Time left"
            className={`rounded-md px-2.5 py-1 text-sm font-semibold tabular-nums ${
              left < 60 ? "bg-pop-500/10 text-pop-600 dark:text-pop-400" : "bg-slate-100 dark:bg-night-700"
            }`}
          >
            {clock(left)}
          </p>
        )}
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600" aria-hidden="true">
        <div className="h-full rounded-full bg-brand-600 transition-all" style={{ width: `${((index + 1) / total) * 100}%` }} />
      </div>

      <p className="muted mt-6 text-xs font-semibold">{q.skill}</p>
      <h2 className="mt-1 text-xl font-semibold leading-snug">{q.question}</h2>

      <div role="radiogroup" aria-label="Answers" className="mt-5 space-y-2">
        {q.options.map((option, i) => {
          const picked = answers[q.id] === i;
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={picked}
              onClick={() => {
                const next = { ...answersRef.current, [q.id]: i };
                answersRef.current = next;
                setAnswers(next);
              }}
              className={`flex w-full items-start gap-3 rounded-lg border px-4 py-3 text-left text-sm transition ${
                picked
                  ? "border-ink bg-ink/[0.03] font-medium dark:border-white dark:bg-white/5"
                  : "border-slate-200 hover:border-slate-400 dark:border-night-600 dark:hover:border-slate-400"
              }`}
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold ${
                  picked ? "border-ink bg-ink text-white dark:border-white dark:bg-white dark:text-ink" : "border-slate-300 dark:border-night-600"
                }`}
                aria-hidden="true"
              >
                {String.fromCharCode(65 + i)}
              </span>
              <span>{option}</span>
            </button>
          );
        })}
      </div>

      {error && <p className="alert mt-4">{error}</p>}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-night-600">
        <button onClick={() => setIndex((i) => i - 1)} disabled={index === 0} className="btn-ghost">
          Previous
        </button>
        <span className="muted text-xs">
          {answered} of {total} answered
        </span>
        {last ? (
          <button onClick={submit} disabled={submitting} className="btn-primary">
            {submitting ? "Submitting..." : "Submit answers"}
          </button>
        ) : (
          <button onClick={() => setIndex((i) => i + 1)} className="btn-primary">
            Next
          </button>
        )}
      </div>
    </section>
  );
}
