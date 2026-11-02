import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LogoMark } from "../components/Icons";
import { PortfolioView } from "../components/PortfolioView";
import { ThemeToggle } from "../components/ThemeToggle";
import { ApiError, apiGet } from "../lib/api";
import type { PortfolioData } from "../lib/portfolio";

/** Public portfolio page at /p/:slug - no login needed. */
export function Portfolio() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<PortfolioData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    apiGet<PortfolioData>(`/api/portfolio/${slug}`)
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 404
            ? "This portfolio is private or doesn't exist."
            : "Could not load this portfolio."
        )
      );
  }, [slug]);

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-4 pt-5 sm:px-6">
        <span className="flex items-center gap-2">
          <LogoMark className="h-8 w-8" />
          <span className="font-display text-lg font-bold">DevProof</span>
        </span>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        {!data && !error && <p className="muted text-sm">Loading...</p>}
        {error && <p className="alert">{error}</p>}
        {data && <PortfolioView data={data} />}
        <p className="muted mt-12 text-center text-xs">
          Skills verified against public GitHub work with DevProof
        </p>
      </main>
    </div>
  );
}
