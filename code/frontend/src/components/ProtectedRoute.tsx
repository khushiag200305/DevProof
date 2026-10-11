import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { Role } from "../context/AuthContext";

/**
 * Gates a route behind sign-in, and optionally a specific role. A
 * signed-in user visiting a route meant for the other role is sent to
 * their own home rather than shown a dead end.
 */
export function ProtectedRoute({
  role,
  children,
}: {
  role?: Role;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-50">
        <p className="text-brand-700">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "student" ? "/upload" : "/dashboard"} replace />;
  }

  return <>{children}</>;
}
