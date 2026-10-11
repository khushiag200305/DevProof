import { GoogleLogin } from "@react-oauth/google";
import type { CredentialResponse } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError, apiPost } from "../lib/api";
import type { AuthUser } from "../context/AuthContext";

interface SignInResponse {
  access_token: string;
  user: AuthUser;
}

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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 via-white to-brand-100 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-xl font-bold text-white shadow-lg shadow-brand-600/20">
            DP
          </div>
          <h1 className="mt-4 text-2xl font-bold text-slate-800 sm:text-3xl">DevProof</h1>
          <p className="mt-2 text-sm text-slate-500 sm:text-base">
            Evidence-backed skill reports from public GitHub activity.
          </p>
        </div>

        <div className="rounded-2xl border border-brand-100 bg-white p-6 shadow-xl shadow-brand-900/5 sm:p-8">
          <h2 className="text-center text-lg font-semibold text-slate-800">Sign in</h2>
          <p className="mt-1 text-center text-sm text-slate-500">
            Sign in with Google to continue.
          </p>

          <div className="mt-6 flex justify-center">
            <GoogleLogin
              onSuccess={handleSuccess}
              onError={() => setError("Google sign-in failed. Please try again.")}
              theme="outline"
              shape="pill"
              size="large"
              width="300"
            />
          </div>

          {error && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-center text-sm text-red-700">
              {error}
            </p>
          )}

          <p className="mt-6 text-center text-xs text-slate-400">
            Signing in with a <span className="font-medium text-slate-500">@thapar.edu</span>{" "}
            address gives you a student account; any other address signs you in as a recruiter.
          </p>
        </div>
      </div>
    </div>
  );
}
