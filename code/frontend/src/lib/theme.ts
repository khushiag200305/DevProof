/**
 * Light / dark theme. Until the user picks one with the header toggle the
 * app follows the operating system setting; after that the choice is kept
 * in localStorage. index.html applies the same logic before the first paint.
 */
export type Theme = "light" | "dark";

const STORAGE_KEY = "devproof_theme";

function systemTheme(): Theme {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function savedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

export function currentTheme(): Theme {
  return savedTheme() ?? systemTheme();
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function saveTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage blocked (private window): the theme still applies for this visit.
  }
  applyTheme(theme);
}

/** Calls `onChange` when the OS theme changes, while the user hasn't picked one. */
export function watchSystemTheme(onChange: (theme: Theme) => void): () => void {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const listener = () => {
    if (savedTheme()) return;
    const theme = query.matches ? "dark" : "light";
    applyTheme(theme);
    onChange(theme);
  };
  query.addEventListener?.("change", listener);
  return () => query.removeEventListener?.("change", listener);
}
