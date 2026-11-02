/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  // Dark mode is switched by a "dark" class on <html> (see src/lib/theme.ts).
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Electric violet - primary actions, links, focus rings.
        brand: {
          50: "#f3f0ff",
          100: "#e8e1ff",
          200: "#d3c6ff",
          300: "#b49dff",
          400: "#936cff",
          500: "#7c47ff",
          600: "#6c3bff",
          700: "#5a24e6",
          800: "#4a1fbd",
          900: "#3d1c96",
          950: "#230e5e",
        },
        // Hot pink and sunshine - the other two stops of the hero gradient.
        pop: { 400: "#ff7aa8", 500: "#ff4f8b", 600: "#e8336f" },
        sun: { 300: "#ffd36e", 400: "#ffc23d", 500: "#ffb627" },
        // Text and surfaces. "paper" is the light page, "night" the dark one.
        ink: { DEFAULT: "#170f2e", soft: "#4b4466", mute: "#7d7697" },
        paper: "#f6f4fe",
        night: { DEFAULT: "#110a22", 800: "#1b1333", 700: "#261c45", 600: "#352a5c" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        hero: "2rem",
      },
    },
  },
  plugins: [],
};
