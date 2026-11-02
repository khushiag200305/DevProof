import { useEffect, useState } from "react";
import { currentTheme, saveTheme, watchSystemTheme, type Theme } from "../lib/theme";
import { MoonIcon, SunIcon } from "./Icons";

/** Sun / moon switch. Follows the system setting until the user flips it. */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.classList.contains("dark") ? "dark" : currentTheme()
  );

  useEffect(() => watchSystemTheme(setTheme), []);

  const dark = theme === "dark";
  const toggle = () => {
    const next: Theme = dark ? "light" : "dark";
    saveTheme(next);
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
      className={`relative flex h-9 w-16 shrink-0 items-center rounded-full border border-brand-100 bg-brand-50 p-1 transition-colors dark:border-night-600 dark:bg-night-700 ${className}`}
    >
      <span
        className={`flex h-7 w-7 items-center justify-center rounded-full shadow-md transition-transform duration-300 ${
          dark ? "translate-x-7 bg-brand-500 text-white" : "translate-x-0 bg-white text-sun-500"
        }`}
      >
        {dark ? <MoonIcon className="h-4 w-4" /> : <SunIcon className="h-4 w-4" />}
      </span>
    </button>
  );
}
