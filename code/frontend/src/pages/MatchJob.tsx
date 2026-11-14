import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Hero, HeroStat } from "../components/Hero";
import { JobFitPanel } from "../components/JobFitPanel";
import { Navbar } from "../components/Navbar";
import { ApiError, apiGet, apiPut } from "../lib/api";

interface Upload {
  candidate_id: number;
  visible_to_recruiters?: boolean;
}

/** Student: match resumes against a job or a ready-made role, with a skill gap roadmap. */
export function MatchJob() {
  const [uploads, setUploads] = useState<Upload[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Upload[]>("/api/candidates/me")
      .then((u) => setUploads(Array.isArray(u) ? u : []))
      .catch(() => setUploads([]));
  }, []);

  const makeVisible = async (candidateId: number): Promise<boolean> => {
    setError(null);
    try {
      await apiPut(`/api/candidates/${candidateId}/visible`, {});
      setUploads((u) => u?.map((c) => ({ ...c, visible_to_recruiters: c.candidate_id === candidateId })) ?? u);
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change which resume recruiters see.");
      return false;
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
        <Hero
          seed="match-a-job"
          aside={
            <div className="grid grid-cols-2 gap-3">
              <HeroStat value={uploads?.length ?? "-"} label="Resumes to compare" />
              <HeroStat value={6} label="Ready-made roles" />
            </div>
          }
        >
          <h1 className="text-4xl font-bold sm:text-5xl">Match a job</h1>
          <p className="mt-3 max-w-xl text-white/80 sm:text-lg">
            Pick a role or paste a job description. See which resume fits best and what to build next to prove the rest.
          </p>
        </Hero>

        {error && <p className="alert mt-4">{error}</p>}

        <div className="mt-6 max-w-4xl">
          {uploads === null ? (
            <p className="muted text-sm">Loading...</p>
          ) : uploads.length === 0 ? (
            <div className="panel">
              <h2 className="text-xl font-bold">Upload a resume first</h2>
              <p className="muted mt-1 text-sm">
                Matching compares your resumes with a job, so you need at least one. Run the GitHub analysis too for a fair score.
              </p>
              <Link to="/upload" className="btn-primary mt-4">
                Go to My resumes
              </Link>
            </div>
          ) : (
            <JobFitPanel onMakeVisible={makeVisible} title="Choose a job or role" />
          )}
        </div>
      </main>
    </div>
  );
}
