/** Colourful initials badge; the colour is picked from the name so it stays stable. */
const SWATCHES = [
  "from-brand-500 to-brand-700",
  "from-pop-400 to-pop-600",
  "from-sun-300 to-sun-500 text-ink",
  "from-emerald-400 to-teal-600",
  "from-sky-400 to-indigo-500",
  "from-fuchsia-400 to-brand-600",
];

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
      className={`flex shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br font-display font-bold text-white ${
        SWATCHES[sum % SWATCHES.length]
      } ${className}`}
    >
      {initials}
    </span>
  );
}
