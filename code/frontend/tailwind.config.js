/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // DevProof brand ramp - a warm crimson, not an alarm-red - used
        // for primary actions, links, and accents throughout the app.
        brand: {
          50: "#fef2f2",
          100: "#fde4e4",
          200: "#facdcd",
          300: "#f5a8a8",
          400: "#ec7878",
          500: "#dd4b4b",
          600: "#c22f34",
          700: "#a3232a",
          800: "#861f27",
          900: "#711e25",
          950: "#3e0b10",
        },
      },
    },
  },
  plugins: [],
};
