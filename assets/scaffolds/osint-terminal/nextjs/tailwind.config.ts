import type { Config } from "tailwindcss";

// Colors are stored in :root as space-separated R G B channels (see globals.css)
// and consumed here via `rgb(var(--*) / <alpha-value>)` so utilities like
// `bg-panel/80` and `bg-accent-cyan/10` work correctly on Tailwind v3.4+.
const config: Config = {
  content: ["./app/**/*.{ts,tsx,js,jsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--bg-canvas) / <alpha-value>)",
        panel: "rgb(var(--bg-panel) / <alpha-value>)",
        "panel-elev": "rgb(var(--bg-panel-elev) / <alpha-value>)",
        border: "rgb(var(--border) / <alpha-value>)",
        "border-strong": "rgb(var(--border-strong) / <alpha-value>)",
        "text-base": "rgb(var(--text-base) / <alpha-value>)",
        "text-mute": "rgb(var(--text-mute) / <alpha-value>)",
        "text-muted": "rgb(var(--text-muted) / <alpha-value>)",
        "accent-cyan": "rgb(var(--accent-cyan) / <alpha-value>)",
        "accent-amber": "rgb(var(--accent-amber) / <alpha-value>)",
        "accent-red": "rgb(var(--accent-red) / <alpha-value>)",
        "accent-green": "rgb(var(--accent-green) / <alpha-value>)",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        wider: ".05em",
        widest: ".18em",
      },
    },
  },
  plugins: [],
};

export default config;
