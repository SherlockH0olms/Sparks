import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#070b14",
          900: "#0b1220",
          850: "#0e1729",
          800: "#12203a",
          700: "#1a2c4e",
          600: "#24406b",
        },
        accent: {
          400: "#38bdf8",
          500: "#0ea5e9",
          300: "#7dd3fc",
        },
        ok: "#34d399",
        bad: "#f87171",
        warn: "#fbbf24",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
