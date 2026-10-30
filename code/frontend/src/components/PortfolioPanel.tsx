import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPut } from "../lib/api";
import { portfolioUrl, type PortfolioSettings } from "../lib/portfolio";
import { PortfolioView } from "./PortfolioView";

interface Props {
  candidateId: number;
  /** Changes when the analysis is re-run, so the preview refreshes. */
  refreshKey: number;
}

/** Student-only: publish the portfolio page, set a headline, copy the link, preview. */
export function PortfolioPanel({ candidateId, refreshKey }: Props) {
  const [settings, setSettings] = useState<PortfolioSettings | null>(null);
  const [headline, setHeadline] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    apiGet<PortfolioSettings>(`/api/candidates/${candidateId}/portfolio`)
      .then((s) => {
        setSettings(s);
        setHeadline(s.headline ?? "");
      })
      .catch(() => setError("Could not load portfolio settings."));
  }, [candidateId, refreshKey]);

  const save = async (isPublic: boolean) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await apiPut<PortfolioSettings>(`/api/candidates/${candidateId}/portfolio`, {
        is_public: isPublic,
        headline: headline.trim() || null,
      });
      setSettings(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const copyLink = async (url: string) => {
    try {
      await navigator.clipboard?.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the link is still visible to copy by hand.
    }
  };

  if (!settings) {
    return error ? (
      <p className="mt-6 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
    ) : null;
  }

  const url = settings.slug ? portfolioUrl(settings.slug) : null;

  return (
    <div className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Portfolio page</h2>
          <p className="mt-1 text-sm text-slate-400">
            A shareable page with your GitHub-verified skills and best projects.
          </p>
        </div>
        <span
          className={`shrink-0 self-start rounded-full px-3 py-1 text-xs font-medium ${
            settings.is_public ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
          }`}
        >
          {settings.is_public ? "Public" : "Private"}
        </span>
      </div>

      <label htmlFor="portfolio-headline" className="mt-5 block text-sm font-medium text-slate-700">
        Headline
      </label>
      <input
        id="portfolio-headline"
        type="text"
        maxLength={120}
        value={headline}
        onChange={(e) => setHeadline(e.target.value)}
        placeholder="e.g. Backend developer · Python, FastAPI, PostgreSQL"
        className="mt-1 block w-full rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400"
      />

      <div className="mt-4 flex flex-wrap gap-3">
        {settings.is_public ? (
          <>
            <button
              onClick={() => save(true)}
              disabled={saving}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40"
            >
              Save headline
            </button>
            <button
              onClick={() => save(false)}
              disabled={saving}
              className="rounded-md border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-40"
            >
              Make private
            </button>
          </>
        ) : (
          <button
            onClick={() => save(true)}
            disabled={saving}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40"
          >
            {saving ? "Publishing..." : "Publish portfolio"}
          </button>
        )}
        <button
          onClick={() => setShowPreview((v) => !v)}
          className="rounded-md border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
        >
          {showPreview ? "Hide preview" : "Preview"}
        </button>
      </div>

      {settings.is_public && url && (
        <div className="mt-4 flex flex-col gap-2 rounded-md bg-brand-50 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
          <a href={url} target="_blank" rel="noreferrer" className="break-all text-brand-700 hover:underline">
            {url}
          </a>
          <button
            onClick={() => copyLink(url)}
            className="shrink-0 rounded-md border border-brand-200 bg-white px-3 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50"
          >
            {copied ? "Copied!" : "Copy link"}
          </button>
        </div>
      )}

      {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {showPreview && (
        <div className="mt-6 rounded-2xl bg-brand-50/40 p-4">
          <PortfolioView data={settings.portfolio} />
        </div>
      )}
    </div>
  );
}
