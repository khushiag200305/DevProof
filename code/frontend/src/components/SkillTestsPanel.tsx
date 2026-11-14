import { useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../lib/api";
import { STATUS_LABEL, STATUS_STYLE, type SkillTest, type SkillTestResult } from "../lib/skillTests";
import { QuizResultView } from "./QuizResultView";

const COUNTS = [5, 10, 15];
const TIMES = [10, 15, 20, 30];

/** Recruiter, on a candidate's report: send a skill test and see the results. */
export function SkillTestsPanel({
  candidateId,
  resumeSkills,
  suggested,
}: {
  candidateId: number;
  /** All skills on this resume. */
  resumeSkills: string[];
  /** Skills without GitHub evidence, picked by default. */
  suggested: string[];
}) {
  const [tests, setTests] = useState<SkillTest[] | null>(null);
  const [skills, setSkills] = useState<string[] | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [count, setCount] = useState(10);
  const [minutes, setMinutes] = useState(15);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [open, setOpen] = useState<SkillTestResult | null>(null);

  const load = () =>
    apiGet<SkillTest[]>(`/api/skill-tests/candidate/${candidateId}`)
      .then((t) => setTests(Array.isArray(t) ? t : []))
      .catch(() => setTests([]));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  useEffect(() => {
    apiGet<{ skills: string[] }>("/api/skill-tests/skills")
      .then((r) => {
        const bank = new Set(Array.isArray(r?.skills) ? r.skills : []);
        const testable = resumeSkills.filter((s) => bank.has(s));
        const unproven = testable.filter((s) => suggested.includes(s));
        setSkills(testable);
        setPicked((unproven.length ? unproven : testable).slice(0, 4));
      })
      .catch(() => setSkills([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  const send = async () => {
    setSending(true);
    setError(null);
    setSent(false);
    try {
      const test = await apiPost<SkillTest>("/api/skill-tests", {
        candidate_id: candidateId,
        skills: picked,
        question_count: count,
        time_limit_minutes: minutes,
        message: message.trim() || null,
      });
      setTests((t) => [test, ...(t ?? [])]);
      setSent(true);
      setMessage("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send the test.");
    } finally {
      setSending(false);
    }
  };

  const cancel = async (t: SkillTest) => {
    try {
      await apiDelete(`/api/skill-tests/${t.test_id}`);
      setTests((list) => list?.filter((x) => x.test_id !== t.test_id) ?? list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel the test.");
    }
  };

  const viewAnswers = async (t: SkillTest) => {
    try {
      setOpen(await apiGet<SkillTestResult>(`/api/skill-tests/${t.test_id}/result`));
    } catch {
      setError("Could not load the answers.");
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[22rem_1fr]">
      <section aria-label="Send a skill test" className="panel h-fit p-5 sm:p-5">
        <h2 className="text-lg font-bold">Send a skill test</h2>
        <p className="muted mt-1 text-sm">
          A short timed quiz the student takes once. Their score appears here next to the GitHub evidence.
        </p>

        {skills === null ? (
          <p className="muted mt-4 text-sm">Loading...</p>
        ) : skills.length === 0 ? (
          <p className="muted mt-4 text-sm">None of this resume's skills have test questions yet.</p>
        ) : (
          <>
            <p className="label mt-4">Skills</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {skills.map((s) => {
                const on = picked.includes(s);
                return (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setPicked((p) => (on ? p.filter((x) => x !== s) : [...p, s]))}
                    className={`chip border py-1.5 transition ${
                      on
                        ? "border-ink bg-ink text-white dark:border-white dark:bg-white dark:text-ink"
                        : "border-slate-200 text-ink-soft hover:border-slate-400 dark:border-night-600 dark:text-slate-300"
                    }`}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="test-count" className="label">Questions</label>
                <select id="test-count" value={count} onChange={(e) => setCount(Number(e.target.value))} className="field">
                  {COUNTS.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="test-minutes" className="label">Time limit</label>
                <select id="test-minutes" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} className="field">
                  {TIMES.map((n) => <option key={n} value={n}>{n} minutes</option>)}
                </select>
              </div>
            </div>
            <label htmlFor="test-message" className="label mt-4">Message (optional)</label>
            <textarea
              id="test-message"
              rows={2}
              maxLength={500}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g. Please take this before Friday's interview"
              className="field resize-y"
            />
            <button onClick={send} disabled={sending || picked.length === 0} className="btn-primary mt-4 w-full">
              {sending ? "Sending..." : "Send test"}
            </button>
            {sent && <p className="mt-2 text-sm font-medium text-brand-700 dark:text-brand-300">Sent. The student has been notified.</p>}
          </>
        )}
        {error && <p className="alert mt-3">{error}</p>}
      </section>

      <section aria-label="Skill tests sent" className="min-w-0 space-y-3">
        <h2 className="text-lg font-bold">Tests you sent</h2>
        {tests === null ? (
          <p className="muted text-sm">Loading...</p>
        ) : tests.length === 0 ? (
          <p className="muted text-sm">No tests sent to this student yet.</p>
        ) : (
          <ul className="space-y-3">
            {tests.map((t) => (
              <li key={t.test_id} aria-label={`Test on ${t.skills.join(", ")}`} className="panel p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{t.skills.join(", ")}</p>
                    <p className="muted text-xs">
                      {t.question_count} questions, {t.time_limit_minutes} min, sent {new Date(t.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`chip py-1 ${STATUS_STYLE[t.status]}`}>{STATUS_LABEL[t.status]}</span>
                    {t.score !== null && (
                      <span className="text-xl font-bold tabular-nums">
                        {t.score}/{t.total}
                      </span>
                    )}
                  </div>
                </div>
                {t.per_skill && (
                  <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
                    {t.per_skill.map((s) => (
                      <li key={s.skill}>
                        <span className="font-medium">{s.skill}</span>{" "}
                        <span className="tabular-nums">
                          {s.correct}/{s.total}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-3 flex gap-2">
                  {t.score !== null && (
                    <button onClick={() => viewAnswers(t)} className="btn-ghost px-3 py-1.5 text-xs">
                      See answers
                    </button>
                  )}
                  {t.status === "waiting" && (
                    <button onClick={() => cancel(t)} className="btn-ghost px-3 py-1.5 text-xs">
                      Cancel test
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {open && (
          <div className="pt-2">
            <div className="mb-3 flex items-center justify-between">
              <p className="font-semibold">Answers: {open.skills.join(", ")}</p>
              <button onClick={() => setOpen(null)} className="btn-ghost px-3 py-1.5 text-xs">Close</button>
            </div>
            <QuizResultView result={open.result} />
          </div>
        )}
      </section>
    </div>
  );
}
