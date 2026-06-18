import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(240 5.9% 90%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(240 10% 3.9%)",
        muted: { DEFAULT: "hsl(240 4.8% 95.9%)", foreground: "hsl(240 3.8% 46.1%)" },
        primary: { DEFAULT: "hsl(240 5.9% 10%)", foreground: "hsl(0 0% 98%)" },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: { lg: "0.65rem", md: "0.5rem", sm: "0.375rem" },
    },
  },
  plugins: [],
} satisfies Config;
