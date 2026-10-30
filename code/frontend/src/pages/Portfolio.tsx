import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PortfolioView } from "../components/PortfolioView";
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
    <div className="min-h-screen bg-brand-50/40">
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        {!data && !error && <p className="text-sm text-slate-400">Loading...</p>}
        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}
        {data && <PortfolioView data={data} />}
        <p className="mt-10 text-center text-xs text-slate-400">
          Skills verified against public GitHub work with DevProof
        </p>
      </main>
    </div>
  );
}
