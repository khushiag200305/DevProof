import type { PortfolioData } from "../lib/portfolio";
import { Avatar } from "./Avatar";
import { Hero, HeroStat } from "./Hero";
import { CheckIcon, ExternalIcon, GitHubIcon } from "./Icons";

const GROUP_TONES = [
  "bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-100",
  "bg-pop-500/10 text-pop-600 dark:text-pop-400",
  "bg-sun-400/20 text-amber-700 dark:text-sun-300",
  "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  "bg-sky-500/10 text-sky-700 dark:text-sky-300",
];

const PROJECT_BANDS = [
  "from-brand-500 to-brand-700",
  "from-pop-500 to-sun-400",
  "from-emerald-400 to-sky-500",
  "from-sun-400 to-brand-500",
];

/** The portfolio page body, shared by the public page and the owner's preview. */
export function PortfolioView({ data }: { data: PortfolioData }) {
  return (
    <div>
      <Hero
        seed={data.name}
        aside={
          <div className="grid grid-cols-2 gap-3 lg:w-[22rem]">
            <HeroStat label="GitHub-verified skills" value={data.stats.verified_skills} />
            <HeroStat label="Original projects" value={data.stats.original_repos} />
            <HeroStat label="Commits" value={data.stats.commits} />
            <HeroStat
              label="Top languages"
              value={<span className="block text-base leading-snug sm:text-lg">{data.stats.top_languages.join(", ") || "-"}</span>}
            />
          </div>
        }
      >
        <div className="flex items-center gap-4">
          <Avatar name={data.name} className="h-16 w-16 text-2xl ring-4 ring-white/30" />
          <div className="min-w-0">
            <h1 className="break-words text-3xl font-bold leading-tight sm:text-5xl">{data.name}</h1>
            {data.headline && <p className="mt-1 text-lg text-white/90">{data.headline}</p>}
          </div>
        </div>
        {data.github_url && (
          <a
            href={data.github_url}
            target="_blank"
            rel="noreferrer"
            className="mt-5 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-ink shadow-md transition hover:-translate-y-0.5"
          >
            <GitHubIcon className="h-4 w-4" />
            github.com/{data.github_username}
          </a>
        )}
      </Hero>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_2fr]">
        <section className="panel h-fit">
          <h2 className="text-2xl font-bold">Verified skills</h2>
          <p className="muted mt-1 text-sm">
            Each skill below is backed by code in the candidate's public repositories.
          </p>
          {data.skill_groups.length === 0 ? (
            <p className="muted mt-4 text-sm">
              {data.analyzed ? "No skills verified yet." : "GitHub analysis hasn't been run yet."}
            </p>
          ) : (
            <div className="mt-5 space-y-5">
              {data.skill_groups.map((group, gi) => (
                <div key={group.category}>
                  <h3 className="text-base font-bold">{group.category}</h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {group.skills.map((s) => (
                      <span
                        key={s.name}
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ${
                          GROUP_TONES[gi % GROUP_TONES.length]
                        }`}
                      >
                        {s.status === "Strong Evidence" && <CheckIcon className="h-3.5 w-3.5" />}
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
            <p className="muted mt-6 border-t border-slate-100 pt-4 text-sm dark:border-night-600">
              <span className="font-semibold text-ink-soft dark:text-slate-300">Also on resume:</span>{" "}
              {data.also_listed.join(", ")}
            </p>
          )}
        </section>

        <section>
          <h2 className="text-2xl font-bold">Projects</h2>
          {data.projects.length === 0 ? (
            <p className="muted mt-2 text-sm">No projects to show yet.</p>
          ) : (
            <ul className="mt-4 grid gap-4 md:grid-cols-2">
              {data.projects.map((p, i) => (
                <li
                  key={p.name}
                  className="tile group relative flex flex-col overflow-hidden p-5 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-600/10"
                >
                  <span
                    className={`absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r ${PROJECT_BANDS[i % PROJECT_BANDS.length]}`}
                    aria-hidden="true"
                  />
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-display text-lg font-bold leading-snug hover:text-brand-700 dark:hover:text-brand-300"
                      >
                        {p.resume_title ?? p.name}
                      </a>
                      {p.resume_title && <p className="muted text-xs">github.com/…/{p.name}</p>}
                    </div>
                    {p.language && (
                      <span className="chip shrink-0 bg-slate-500/10 text-ink-soft dark:text-slate-300">
                        {p.language}
                      </span>
                    )}
                  </div>
                  {p.description && (
                    <p className="mt-2 text-sm text-ink-soft dark:text-slate-300">{p.description}</p>
                  )}
                  {p.technologies.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {p.technologies.map((t) => (
                        <span key={t} className="chip bg-brand-600/10 text-brand-700 dark:bg-brand-500/20 dark:text-brand-200">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {p.highlights.length > 0 && (
                    <ul className="mt-3 space-y-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                      {p.highlights.map((h) => (
                        <li key={h} className="flex items-center gap-1.5">
                          <CheckIcon className="h-3.5 w-3.5" />
                          {h}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="muted mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 pt-4 text-xs font-medium">
                    <span>{p.commit_count} commits</span>
                    {p.active && <span>{p.active}</span>}
                    {p.stars > 0 && <span>★ {p.stars}</span>}
                    {p.homepage && (
                      <a
                        href={p.homepage}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-full bg-pop-500 px-2.5 py-1 font-semibold text-white transition hover:bg-pop-600"
                      >
                        Live demo
                        <ExternalIcon className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
