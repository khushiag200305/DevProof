import { GoogleLogin } from "@react-oauth/google";
import type { CredentialResponse } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { CommitGrid, GridLegend } from "../components/Hero";
import { LogoMark } from "../components/Icons";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiPost } from "../lib/api";
import type { AuthUser } from "../context/AuthContext";

interface SignInResponse {
  access_token: string;
  user: AuthUser;
}

const STEPS = [
  { title: "Upload your resume", text: "We read the skills and projects you list." },
  { title: "We check your public GitHub", text: "Every skill is matched against real code in your repositories." },
  { title: "Share the evidence", text: "Recruiters see a score for each skill and the files behind it." },
];

export function Login() {
  const { user, login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  if (user) {
    return <Navigate to={user.role === "recruiter" ? "/dashboard" : "/upload"} replace />;
  }

  const handleSuccess = async (credentialResponse: CredentialResponse) => {
    setError(null);
    if (!credentialResponse.credential) {
      setError("Google didn't return a credential. Please try again.");
      return;
    }
    try {
      const data = await apiPost<SignInResponse>("/api/auth/google", {
        credential: credentialResponse.credential,
      });
      login(data.access_token, data.user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Please try again.");
    }
  };

  return (
    <div className="relative min-h-screen p-3 sm:p-4 lg:grid lg:grid-cols-[1.1fr_1fr] lg:gap-4">
      <section className="hero flex flex-col justify-between gap-10 p-7 sm:p-12 lg:min-h-[calc(100vh-2rem)]">
        <div className="relative flex items-center gap-2.5">
          <LogoMark className="h-8 w-8" />
          <h1 className="text-lg font-semibold tracking-tight">DevProof</h1>
        </div>

        <div className="relative max-w-lg">
          <p className="text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
            Prove every skill on your resume with real code.
          </p>
          <p className="mt-5 text-base text-white/70 sm:text-lg">
            Evidence-backed skill reports from public GitHub activity.
          </p>
        </div>

        {/* What DevProof reads: a year of commits, drawn like a GitHub profile. */}
        <div className="relative">
          <div className="overflow-hidden">
            <CommitGrid seed="devproof-activity" weeks={33} tone="green" className="w-max" />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-white/50">
            <span>Commits from public repositories, the evidence behind each score</span>
            <GridLegend />
          </div>
        </div>

        <ol className="relative grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="border-t border-white/15 pt-4">
              <span className="text-sm font-medium text-brand-300">{i + 1}</span>
              <p className="mt-2 font-semibold">{step.title}</p>
              <p className="mt-1 text-sm leading-relaxed text-white/60">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <ThemeToggle className="absolute right-6 top-6 z-10 lg:right-8 lg:top-8" />
      <section className="flex items-center justify-center px-2 py-12 lg:py-0">
        <div className="w-full max-w-sm">
          <h2 className="text-3xl font-semibold tracking-tight">Sign in</h2>
          <p className="muted mt-2">Use your Google account to continue.</p>

          <div className="mt-8 flex flex-col items-center gap-4">
            <GoogleLogin
              onSuccess={handleSuccess}
              onError={() => setError("Google sign-in failed. Please try again.")}
              theme="outline"
              shape="rectangular"
              size="large"
              width="360"
            />
            {error && <p className="alert w-full text-center">{error}</p>}
          </div>

          <div className="mt-8 border-t border-slate-200 pt-6 text-sm dark:border-night-600">
            <dl className="space-y-3">
              <div className="flex gap-3">
                <dt className="w-20 shrink-0 font-semibold">Students</dt>
                <dd className="muted">Upload a resume and get your skills verified.</dd>
              </div>
              <div className="flex gap-3">
                <dt className="w-20 shrink-0 font-semibold">Recruiters</dt>
                <dd className="muted">Review candidates with the evidence behind each skill.</dd>
              </div>
            </dl>
            <p className="muted mt-5 text-xs leading-relaxed">
              Signing in with a{" "}
              <span className="font-semibold text-ink-soft dark:text-slate-200">@thapar.edu</span>{" "}
              address gives you a student account; any other address signs you in as a recruiter.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
