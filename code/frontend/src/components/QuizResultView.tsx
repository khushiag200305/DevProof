import { CheckIcon, XIcon } from "./Icons";
import type { QuizResult } from "../lib/quiz";

/** Score per skill, then every question with the right answer and explanation. */
export function QuizResultView({ result }: { result: QuizResult }) {
  return (
    <section aria-label="Quiz result" className="space-y-6">
      <div className="panel">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="muted text-sm">Your score</p>
            <p className="mt-1 text-5xl font-bold tabular-nums">
              {result.score}
              <span className="muted text-2xl font-semibold"> / {result.total}</span>
            </p>
          </div>
          <p className="text-2xl font-semibold tabular-nums">{result.percent}%</p>
        </div>
        {result.over_time && (
          <p className="mt-3 text-sm font-medium text-pop-600 dark:text-pop-400">Submitted after the time limit.</p>
        )}
        <ul className="mt-5 space-y-3">
          {result.per_skill.map((s) => (
            <li key={s.skill}>
              <div className="flex justify-between text-sm">
                <span className="font-medium">{s.skill}</span>
                <span className="tabular-nums">
                  {s.correct}/{s.total}
                </span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-night-600" aria-hidden="true">
                <div
                  className={`h-full rounded-full ${s.correct / s.total >= 0.7 ? "bg-brand-600" : s.correct / s.total >= 0.4 ? "bg-sun-400" : "bg-pop-500"}`}
                  style={{ width: `${Math.max(3, (s.correct / s.total) * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </div>

      <ol className="space-y-3">
        {result.questions.map((q, n) => (
          <li key={q.id} aria-label={`Question ${n + 1}`} className="panel p-5 sm:p-5">
            <div className="flex items-start gap-3">
              <span
                className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white ${q.is_correct ? "bg-brand-600" : "bg-pop-500"}`}
                aria-label={q.is_correct ? "Correct" : "Incorrect"}
              >
                {q.is_correct ? <CheckIcon className="h-3.5 w-3.5" /> : <XIcon className="h-3.5 w-3.5" />}
              </span>
              <div className="min-w-0">
                <p className="muted text-xs font-semibold">{q.skill}</p>
                <p className="font-semibold">{q.question}</p>
                <ul className="mt-3 space-y-1.5 text-sm">
                  {q.options.map((option, i) => (
                    <li
                      key={i}
                      className={`rounded-md px-3 py-1.5 ${
                        i === q.correct
                          ? "bg-emerald-500/15 font-medium text-emerald-800 dark:text-emerald-200"
                          : i === q.chosen
                            ? "bg-pop-500/10 text-pop-600 line-through dark:text-pop-400"
                            : "text-ink-soft dark:text-slate-300"
                      }`}
                    >
                      {String.fromCharCode(65 + i)}. {option}
                      {i === q.correct && " (correct answer)"}
                      {i === q.chosen && i !== q.correct && " (your answer)"}
                    </li>
                  ))}
                </ul>
                {q.chosen === null && <p className="muted mt-2 text-xs">Not answered</p>}
                <p className="mt-3 text-sm text-ink-soft dark:text-slate-300">{q.explanation}</p>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
