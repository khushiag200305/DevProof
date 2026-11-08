/** Initials badge; the colour is picked from the name so it stays stable. */
const SWATCHES = ["bg-brand-600", "bg-pop-500", "bg-sun-400 text-ink", "bg-sky-700", "bg-slate-500"];

export function Avatar({ name, className = "h-11 w-11 text-base" }: { name: string; className?: string }) {
  let sum = 0;
  for (const ch of name) sum += ch.charCodeAt(0);
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase())
      .join("") || "?";
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-lg font-display font-semibold text-white ${
        SWATCHES[sum % SWATCHES.length]
      } ${className}`}
    >
      {initials}
    </span>
  );
}
