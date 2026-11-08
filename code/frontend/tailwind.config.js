/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  // Dark mode is switched by a "dark" class on <html> (see src/lib/theme.ts).
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Verified green - the one brand colour: links, selected states, evidence.
        brand: {
          50: "#eefbf1",
          100: "#d5f5dd",
          200: "#aee9be",
          300: "#7bd696",
          400: "#45bb6a",
          500: "#23a04f",
          600: "#1a7f37",
          700: "#166b2e",
          800: "#145527",
          900: "#124622",
          950: "#06260f",
        },
        // Rust and amber: "needs proof" and "good evidence".
        pop: { 400: "#e2735a", 500: "#c9472b", 600: "#a8371f" },
        sun: { 300: "#e7c35c", 400: "#d4a017", 500: "#b8860b" },
        // Text and surfaces. "paper" is the light page, "night" the dark one.
        ink: { DEFAULT: "#16181d", soft: "#454a54", mute: "#6b7280" },
        paper: "#f6f6f4",
        night: { DEFAULT: "#0e1013", 800: "#16191e", 700: "#1e2228", 600: "#2c313a" },
      },
      fontFamily: {
        display: ['"Geist"', "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        sans: ['"Geist"', "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        hero: "0.75rem",
      },
    },
  },
  plugins: [],
};
