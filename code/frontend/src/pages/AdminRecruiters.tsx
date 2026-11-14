import { useEffect, useState } from "react";
import { Avatar } from "../components/Avatar";
import { Navbar } from "../components/Navbar";
import { ApiError, apiGet, apiPut } from "../lib/api";

type Status = "pending" | "approved" | "rejected";

interface RecruiterAccount {
  user_id: number;
  email: string;
  name: string | null;
  picture_url: string | null;
  domain: string;
  created_at: string;
  status: Status;
}

const STATUS_STYLE: Record<Status, string> = {
  pending: "bg-sun-400/25 text-amber-700 dark:text-sun-300",
  approved: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  rejected: "bg-pop-500/10 text-pop-600 dark:text-pop-400",
};

const STATUS_LABEL: Record<Status, string> = {
  pending: "Waiting",
  approved: "Approved",
  rejected: "Rejected",
};

/** Admin-only: approve or reject recruiter accounts. */
export function AdminRecruiters() {
  const [recruiters, setRecruiters] = useState<RecruiterAccount[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<number | null>(null);

  useEffect(() => {
    apiGet<RecruiterAccount[]>("/api/admin/recruiters")
      .then(setRecruiters)
      .catch(() => setError("Could not load recruiter accounts."));
  }, []);

  const setStatus = async (r: RecruiterAccount, status: Status) => {
    setSaving(r.user_id);
    setError(null);
    try {
      const updated = await apiPut<RecruiterAccount>(`/api/admin/recruiters/${r.user_id}`, { status });
      setRecruiters((list) => list?.map((x) => (x.user_id === r.user_id ? updated : x)) ?? list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update this account.");
    } finally {
      setSaving(null);
    }
  };

  const waiting = recruiters?.filter((r) => r.status === "pending").length ?? 0;

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <h1 className="text-3xl font-bold">Recruiter requests</h1>
        <p className="muted mt-2">
          Recruiters can see student reports only after you approve them.
          {recruiters && ` ${waiting} waiting.`}
        </p>

        {error && <p className="alert mt-4">{error}</p>}

        {recruiters === null && !error && <p className="muted mt-6 text-sm">Loading...</p>}
        {recruiters?.length === 0 && (
          <div className="mt-6 rounded-xl border-2 border-dashed border-slate-200 p-10 text-center dark:border-night-600">
            <p className="font-semibold">No recruiter accounts yet</p>
            <p className="muted mt-1 text-sm">When someone signs in with a non-Thapar Google account, they appear here.</p>
          </div>
        )}

        {recruiters && recruiters.length > 0 && (
          <ul className="mt-6 space-y-3">
            {recruiters.map((r) => {
              const name = r.name ?? r.email;
              return (
                <li key={r.user_id} aria-label={name} className="panel flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <Avatar name={name} />
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 font-semibold">
                        {name}
                        <span className={`chip py-1 ${STATUS_STYLE[r.status]}`}>{STATUS_LABEL[r.status]}</span>
                      </p>
                      <p className="muted truncate text-sm">{r.email}</p>
                      <p className="muted text-xs">
                        Company domain {r.domain}, signed up {new Date(r.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {r.status !== "approved" && (
                      <button onClick={() => setStatus(r, "approved")} disabled={saving === r.user_id} className="btn-primary px-3 py-1.5 text-xs">
                        Approve
                      </button>
                    )}
                    {r.status !== "rejected" && (
                      <button onClick={() => setStatus(r, "rejected")} disabled={saving === r.user_id} className="btn-ghost px-3 py-1.5 text-xs">
                        {r.status === "approved" ? "Revoke" : "Reject"}
                      </button>
                    )}
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
