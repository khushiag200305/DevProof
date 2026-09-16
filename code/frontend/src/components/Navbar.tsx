import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const homePath = user?.role === "recruiter" ? "/dashboard" : "/upload";

  return (
    <header className="border-b border-brand-100 bg-white/80 backdrop-blur sticky top-0 z-10">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to={homePath} className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            DP
          </span>
          <span className="text-lg font-semibold text-slate-800">DevProof</span>
        </Link>

        {user && (
          <div className="flex items-center gap-3">
            <span className="hidden rounded-full bg-brand-50 px-3 py-1 text-xs font-medium capitalize text-brand-700 sm:inline-block">
              {user.role}
            </span>
            {user.picture_url ? (
              <img
                src={user.picture_url}
                alt={user.name ?? user.email}
                className="h-8 w-8 rounded-full ring-1 ring-brand-200"
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                {(user.name ?? user.email).slice(0, 1).toUpperCase()}
              </span>
            )}
            <span className="hidden text-sm text-slate-600 md:inline">
              {user.name ?? user.email}
            </span>
            <button
              onClick={handleLogout}
              className="rounded-md border border-brand-200 px-3 py-1.5 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
