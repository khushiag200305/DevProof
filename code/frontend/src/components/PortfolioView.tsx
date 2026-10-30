import type { PortfolioData } from "../lib/portfolio";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-brand-100 bg-white px-4 py-3">
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}

/** The portfolio page body, shared by the public page and the owner's preview. */
export function PortfolioView({ data }: { data: PortfolioData }) {
  return (
    <div>
      <section className="rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-3xl font-bold text-slate-800">{data.name}</h1>
        {data.headline && <p className="mt-1 text-lg text-slate-600">{data.headline}</p>}
        {data.github_url && (
          <a
            href={data.github_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-sm font-medium text-brand-700 hover:underline"
          >
            github.com/{data.github_username}
          </a>
        )}
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="GitHub-verified skills" value={data.stats.verified_skills} />
          <Stat label="Original projects" value={data.stats.original_repos} />
          <Stat label="Commits" value={data.stats.commits} />
          <Stat label="Top languages" value={data.stats.top_languages.join(", ") || "-"} />
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-slate-800">Verified skills</h2>
        <p className="mt-1 text-sm text-slate-400">
          Each skill below is backed by code in the candidate's public repositories.
        </p>
        {data.skill_groups.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">
            {data.analyzed ? "No skills verified yet." : "GitHub analysis hasn't been run yet."}
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {data.skill_groups.map((group) => (
              <div key={group.category}>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {group.category}
                </h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {group.skills.map((s) => (
                    <span
                      key={s.name}
                      className={`rounded-full px-3 py-1 text-sm font-medium ${
                        s.status === "Strong Evidence"
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {s.name}
                      {s.score !== null && ` · ${s.score}`}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {data.also_listed.length > 0 && (
          <p className="mt-5 text-sm text-slate-500">
            <span className="font-medium text-slate-600">Also on resume:</span>{" "}
            {data.also_listed.join(", ")}
          </p>
        )}
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
        {data.projects.length === 0 ? (
          <p className="mt-2 text-sm text-slate-400">No projects to show yet.</p>
        ) : (
          <ul className="mt-3 grid gap-4 sm:grid-cols-2">
            {data.projects.map((p) => (
              <li
                key={p.name}
                className="flex flex-col rounded-2xl border border-brand-100 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-slate-800 hover:text-brand-700 hover:underline"
                  >
                    {p.name}
                  </a>
                  {p.language && (
                    <span className="shrink-0 text-xs text-slate-400">{p.language}</span>
                  )}
                </div>
                {p.description && <p className="mt-1 text-sm text-slate-600">{p.description}</p>}
                {p.technologies.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {p.technologies.map((t) => (
                      <span
                        key={t}
                        className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {p.highlights.length > 0 && (
                  <ul className="mt-3 space-y-0.5 text-xs text-slate-500">
                    {p.highlights.map((h) => (
                      <li key={h}>✓ {h}</li>
                    ))}
                  </ul>
                )}
                <div className="mt-auto flex flex-wrap gap-x-4 gap-y-1 pt-4 text-xs text-slate-400">
                  <span>{p.commit_count} commits</span>
                  {p.active && <span>{p.active}</span>}
                  {p.stars > 0 && <span>★ {p.stars}</span>}
                  {p.homepage && (
                    <a
                      href={p.homepage}
                      target="_blank"
                      rel="noreferrer"
                      className="font-medium text-brand-700 hover:underline"
                    >
                      Live demo
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
