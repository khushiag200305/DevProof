import { GoogleLogin } from "@react-oauth/google";
import type { CredentialResponse } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { CommitGrid } from "../components/Hero";
import { CheckIcon, GitHubIcon, LogoMark } from "../components/Icons";
import { ThemeToggle } from "../components/ThemeToggle";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiPost } from "../lib/api";
import type { AuthUser } from "../context/AuthContext";

interface SignInResponse {
  access_token: string;
  user: AuthUser;
}

const POINTS = [
  "Every skill on the resume is checked against real code",
  "Each score lists the repositories and files behind it",
  "Students get a shareable portfolio and resume lines",
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
    <div className="relative min-h-screen p-3 sm:p-4 lg:grid lg:grid-cols-[1.15fr_1fr] lg:gap-4">
      <section className="hero flex flex-col justify-between gap-10 p-7 sm:p-10 lg:min-h-[calc(100vh-2rem)]">
        <div className="pointer-events-none absolute -bottom-32 -right-24 h-96 w-96 rounded-full bg-sun-400/30 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <LogoMark className="h-11 w-11 drop-shadow-lg" />
          <span className="text-sm font-semibold text-white/85">Skill reports backed by GitHub</span>
        </div>

        <div className="relative">
          <h1 className="font-display text-6xl font-extrabold leading-[0.9] sm:text-8xl">DevProof</h1>
          <p className="mt-5 max-w-md text-lg text-white/90 sm:text-xl">
            Evidence-backed skill reports from public GitHub activity.
          </p>
          <ul className="mt-8 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sm font-medium sm:text-base">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-brand-700">
                  <CheckIcon className="h-4 w-4" />
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-end justify-between gap-6">
          <CommitGrid seed="devproof" weeks={26} className="max-w-full overflow-hidden" />
          <GitHubIcon className="hidden h-10 w-10 shrink-0 opacity-80 sm:block" />
        </div>
      </section>

      <ThemeToggle className="absolute right-6 top-6 z-10 lg:right-8 lg:top-8" />
      <section className="flex items-center justify-center px-2 py-10 lg:py-0">
        <div className="w-full max-w-sm">
          <h2 className="font-display text-3xl font-extrabold sm:text-4xl">Sign in</h2>
          <p className="muted mt-2">Sign in with Google to continue.</p>

          <div className="panel mt-8 flex flex-col items-center gap-5">
            <GoogleLogin
              onSuccess={handleSuccess}
              onError={() => setError("Google sign-in failed. Please try again.")}
              theme="outline"
              shape="pill"
              size="large"
              width="300"
            />
            {error && <p className="alert w-full text-center">{error}</p>}
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-2xl bg-brand-600/10 p-4 dark:bg-brand-500/15">
              <p className="font-display text-lg font-bold text-brand-700 dark:text-brand-200">Student</p>
              <p className="muted mt-1 text-xs">Upload your resume and prove your skills.</p>
            </div>
            <div className="rounded-2xl bg-pop-500/10 p-4">
              <p className="font-display text-lg font-bold text-pop-600 dark:text-pop-400">Recruiter</p>
              <p className="muted mt-1 text-xs">Review candidates with the evidence.</p>
            </div>
          </div>

          <p className="muted mt-5 text-xs leading-relaxed">
            Signing in with a{" "}
            <span className="font-semibold text-ink-soft dark:text-slate-200">@thapar.edu</span>{" "}
            address gives you a student account; any other address signs you in as a recruiter.
          </p>
        </div>
      </section>
    </div>
  );
}
