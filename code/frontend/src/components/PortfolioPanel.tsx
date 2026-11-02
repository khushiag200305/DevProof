import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPut } from "../lib/api";
import { portfolioUrl, type PortfolioSettings } from "../lib/portfolio";
import { CheckIcon, CopyIcon, GlobeIcon } from "./Icons";
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
    return error ? <p className="alert">{error}</p> : null;
  }

  const url = settings.slug ? portfolioUrl(settings.slug) : null;

  return (
    <div className="panel h-full">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-pop-500 text-white">
            <GlobeIcon className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-2xl font-bold">Portfolio page</h2>
            <p className="muted mt-1 text-sm">
              A shareable page with your GitHub-verified skills and best projects.
            </p>
          </div>
        </div>
        <span
          className={`chip inline-flex shrink-0 items-center gap-1.5 self-start px-3 py-1 ${
            settings.is_public
              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
              : "bg-slate-500/10 text-ink-mute dark:text-slate-400"
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${settings.is_public ? "animate-pulse bg-emerald-500" : "bg-slate-400"}`}
            aria-hidden="true"
          />
          {settings.is_public ? "Public" : "Private"}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <div>
          <label htmlFor="portfolio-headline" className="label">
            Headline
          </label>
          <input
            id="portfolio-headline"
            type="text"
            maxLength={120}
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="e.g. Backend developer, Python and FastAPI"
            className="field"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {settings.is_public ? (
            <>
              <button onClick={() => save(true)} disabled={saving} className="btn-primary">
                Save headline
              </button>
              <button onClick={() => save(false)} disabled={saving} className="btn-ghost py-2.5">
                Make private
              </button>
            </>
          ) : (
            <button onClick={() => save(true)} disabled={saving} className="btn-primary">
              {saving ? "Publishing..." : "Publish portfolio"}
            </button>
          )}
        </div>
      </div>

      {settings.is_public && url && (
        <div className="rise mt-4 flex flex-col gap-2 rounded-xl bg-brand-600/10 px-4 py-3 text-sm dark:bg-brand-500/15 sm:flex-row sm:items-center sm:justify-between">
          <a href={url} target="_blank" rel="noreferrer" className="link break-all">
            {url}
          </a>
          <button
            onClick={() => copyLink(url)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 shadow-sm transition hover:shadow dark:bg-night-700 dark:text-brand-200"
          >
            {copied ? <CheckIcon className="h-3.5 w-3.5" /> : <CopyIcon className="h-3.5 w-3.5" />}
            {copied ? "Copied!" : "Copy link"}
          </button>
        </div>
      )}

      {error && <p className="alert mt-4">{error}</p>}

      <button
        onClick={() => setShowPreview((v) => !v)}
        aria-expanded={showPreview}
        className="btn-ghost mt-5 w-full"
      >
        {showPreview ? "Hide preview" : "Preview"}
      </button>

      {showPreview && (
        <div className="rise mt-5 rounded-2xl bg-paper p-3 ring-1 ring-brand-100 dark:bg-night dark:ring-night-600 sm:p-4">
          <PortfolioView data={settings.portfolio} />
        </div>
      )}
    </div>
  );
}
