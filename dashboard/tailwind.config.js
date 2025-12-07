/** @type {import('tailwindcss').Config} */
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0B1526",
          800: "#111C2F",
          700: "#16233C",
        },
        slate: {
          700: "#1E293B",
          600: "#334155",
          500: "#475569",
        },
        accent: {
          blue: "#1FB6FF",
          cyan: "#64D2FF",
          green: "#16A34A",
          amber: "#FACC15",
        },
      },
      boxShadow: {
        card: "0 12px 28px rgba(15,23,42,0.15)",
      },
    },
  },
  plugins: [],
}
