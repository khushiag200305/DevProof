import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../context/AuthContext";
import { LogoMark } from "./Icons";
import { RecruiterPending } from "../pages/RecruiterPending";

/**
 * Gates a route behind sign-in, and optionally a specific role. A
 * signed-in user visiting a route meant for the other role is sent to
 * their own home rather than shown a dead end.
 */
export function ProtectedRoute({
  role,
  admin = false,
  children,
}: {
  role?: Role;
  /** Only admins (ADMIN_EMAILS on the backend) may open this page. */
  admin?: boolean;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <LogoMark className="h-12 w-12 animate-pulse" />
        <p className="font-semibold text-brand-700 dark:text-brand-300">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (admin && !user.is_admin) {
    return <Navigate to={user.role === "student" ? "/upload" : "/dashboard"} replace />;
  }

  // Recruiters see nothing about students until an admin approves them.
  if (user.role === "recruiter" && !admin && user.recruiter_status && user.recruiter_status !== "approved") {
    return <RecruiterPending />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "student" ? "/upload" : "/dashboard"} replace />;
  }

  return <>{children}</>;
}
