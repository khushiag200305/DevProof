import type { CSSProperties, ReactNode } from "react";

/** Small deterministic hash so the same seed always draws the same grid. */
function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Activity level (0-4) for each day cell, week by week. Same seed, same grid. */
function gridLevels(seed: string, weeks: number): number[] {
  let state = hash(seed) || 1;
  const cells: number[] = [];
  for (let w = 0; w < weeks; w++) {
    // Activity ramps up towards recent weeks, like a real busy profile.
    const ramp = 0.35 + (w / weeks) * 0.65;
    for (let d = 0; d < 7; d++) {
      state ^= state << 13;
      state ^= state >>> 17;
      state ^= state << 5;
      const r = ((state >>> 0) / 4294967296) * ramp;
      cells.push(r < 0.3 ? 0 : r < 0.45 ? 1 : r < 0.58 ? 2 : r < 0.7 ? 3 : 4);
    }
  }
  return cells;
}

const LEVELS = {
  white: ["bg-white/10", "bg-white/25", "bg-white/45", "bg-white/70", "bg-white"],
  // GitHub's contribution greens, tuned for a dark background.
  green: ["bg-white/[0.07]", "bg-brand-900", "bg-brand-700", "bg-brand-500", "bg-brand-400"],
};

/**
 * A GitHub-style contribution grid, drawn from a seed (a name or page
 * title) so each page and each candidate gets its own pattern. Purely
 * decorative.
 */
export function CommitGrid({
  seed,
  weeks = 18,
  tone = "white",
  className = "",
}: {
  seed: string;
  weeks?: number;
  tone?: keyof typeof LEVELS;
  className?: string;
}) {
  const cells = gridLevels(seed, weeks);
  return (
    <div
      aria-hidden="true"
      className={`grid grid-flow-col grid-rows-7 gap-[5px] ${className}`}
    >
      {cells.map((level, i) => (
        <span
          key={i}
          className={`grid-cell h-3 w-3 rounded-[2px] sm:h-3.5 sm:w-3.5 ${LEVELS[tone][level]}`}
          style={{ "--i": Math.floor(i / 7) * 2 + (i % 7) } as CSSProperties}
        />
      ))}
    </div>
  );
}

/**
 * The banner at the top of each page: content on the left, an
 * optional aside (stats, a score) on the right, and the commit grid
 * glowing behind it.
 */
/** "Less [] [] [] [] [] More" key under a commit grid, as on GitHub profiles. */
export function GridLegend({ tone = "green" }: { tone?: keyof typeof LEVELS }) {
  return (
    <div aria-hidden="true" className="flex items-center gap-1 text-xs text-white/50">
      <span className="mr-1">Less</span>
      {LEVELS[tone].map((c) => (
        <span key={c} className={`h-3 w-3 rounded-[2px] ${c}`} />
      ))}
      <span className="ml-1">More</span>
    </div>
  );
}

export function Hero({
  seed,
  children,
  aside,
  className = "",
}: {
  seed: string;
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`hero ${className}`}>
      {!aside && (
        <CommitGrid
          seed={seed}
          weeks={20}
          className="pointer-events-none absolute right-8 top-1/2 hidden -translate-y-1/2 opacity-50 [mask-image:linear-gradient(to_right,transparent,black_40%)] lg:grid"
        />
      )}
      <div className="relative flex flex-col gap-6 p-6 sm:p-9 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 max-w-2xl">{children}</div>
        {aside && <div className="relative shrink-0">{aside}</div>}
      </div>
    </section>
  );
}

/** Frosted stat block used inside the hero. */
export function HeroStat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <div className="rounded-lg border border-white/15 px-4 py-3">
      <p className="font-display text-2xl font-bold leading-none sm:text-3xl">{value}</p>
      <p className="mt-1 text-xs font-medium text-white/60">{label}</p>
    </div>
  );
}
