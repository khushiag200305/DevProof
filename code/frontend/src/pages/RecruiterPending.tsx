import { useState } from "react";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";

/** Shown to recruiters an admin hasn't approved yet (or rejected). */
export function RecruiterPending() {
  const { user, refresh } = useAuth();
  const [checking, setChecking] = useState(false);
  const [checked, setChecked] = useState(false);
  const rejected = user?.recruiter_status === "rejected";

  const checkAgain = async () => {
    setChecking(true);
    try {
      await refresh?.();
      setChecked(true);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-xl px-4 py-16 sm:px-6">
        <div className="panel">
          <h1 className="text-2xl font-bold">
            {rejected ? "Your recruiter account wasn't approved" : "Waiting for approval"}
          </h1>
          <p className="muted mt-3">
            {rejected
              ? "A DevProof admin didn't approve this account, so it can't see student reports. If you think this is a mistake, contact the DevProof team."
              : "Your recruiter account is waiting for approval by a DevProof admin. Student reports are only shown to approved recruiters, to keep students' data private."}
          </p>
          <p className="mt-4 text-sm">
            Signed in as <span className="font-semibold">{user?.email}</span>
          </p>
          {!rejected && (
            <div className="mt-6 flex items-center gap-3">
              <button onClick={checkAgain} disabled={checking} className="btn-primary">
                {checking ? "Checking..." : "Check again"}
              </button>
              {checked && <span className="muted text-sm">Still waiting. Try again later.</span>}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
