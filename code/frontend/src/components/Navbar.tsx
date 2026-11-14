import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogoMark, LogoutIcon } from "./Icons";
import { NotificationBell } from "./NotificationBell";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const homePath = user?.role === "recruiter" ? "/dashboard" : "/upload";
  const waiting = user?.role === "recruiter" && !!user.recruiter_status && user.recruiter_status !== "approved";
  const links =
    waiting
      ? []
      : user?.role === "recruiter"
      ? [
          { to: "/dashboard", label: "Candidates" },
          { to: "/talent", label: "Talent search" },
        ]
      : [
          { to: "/upload", label: "My resumes" },
          { to: "/practice", label: "Practice" },
        ];
  if (user?.is_admin) links.push({ to: "/admin", label: "Recruiter requests" });

  return (
    <header className="sticky top-0 z-20 border-b border-brand-100/70 bg-paper/80 backdrop-blur-xl dark:border-night-600/70 dark:bg-night/80">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link to={homePath} className="group flex items-center gap-2.5 rounded-xl">
            <LogoMark className="h-8 w-8" />
            <span className="text-lg font-semibold tracking-tight">DevProof</span>
          </Link>
          {user && (
            <nav className="hidden gap-1 sm:flex">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                      isActive
                        ? "bg-slate-200/70 text-ink dark:bg-night-700 dark:text-white"
                        : "text-ink-soft hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-night-700"
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {user && !waiting && <NotificationBell />}
          <ThemeToggle />
          {user && (
            <>
              <span className="hidden rounded-md bg-slate-200/70 px-2 py-0.5 text-xs font-medium capitalize text-ink-soft dark:bg-night-700 dark:text-slate-300 md:inline-block">
                {user.role}
              </span>
              {user.picture_url ? (
                <img
                  src={user.picture_url}
                  alt={user.name ?? user.email}
                  className="h-9 w-9 rounded-full ring-2 ring-brand-200 dark:ring-night-600"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700 dark:bg-night-700 dark:text-brand-200">
                  {(user.name ?? user.email).slice(0, 1).toUpperCase()}
                </span>
              )}
              <span className="hidden text-sm font-medium text-ink-soft dark:text-slate-300 lg:inline">
                {user.name ?? user.email}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 rounded-full px-3 py-2 text-sm font-semibold text-ink-soft transition hover:bg-pop-500/10 hover:text-pop-600 dark:text-slate-300 dark:hover:text-pop-400"
              >
                <LogoutIcon className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
