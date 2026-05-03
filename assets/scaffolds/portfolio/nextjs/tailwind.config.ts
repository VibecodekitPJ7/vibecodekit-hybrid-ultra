import type { Config } from "tailwindcss";

// Generated from vibecodekit.methodology (FONT_PAIRINGS / COLOR_PSYCHOLOGY).
// Regenerate via:
//   python3 -m vibecodekit.cli scaffold tokens-export --scaffold portfolio
// Source of truth: scripts/vibecodekit/design_tokens_export.py
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,js,jsx,mdx}",
    "./components/**/*.{ts,tsx,js,jsx,mdx}",
  ],
  theme: {
    extend: {
      // CP-01..CP-06 from methodology.COLOR_PSYCHOLOGY (single source of truth).
      // portfolio designers often pick CP-04 (luxury) or CP-06 (neutral) as primary.
      colors: {
        "vck-trust":   "#2563EB", // CP-01 Trust/Professional
        "vck-energy":  "#F97316", // CP-02 Energy/Action
        "vck-growth":  "#22C55E", // CP-03 Growth/Health
        "vck-luxury":  "#7C3AED", // CP-04 Luxury/Premium
        "vck-warning": "#EF4444", // CP-05 Warning/Urgency
        "vck-neutral": "#6B7280", // CP-06 Neutral/Modern
      },
      // FP-01 Modern Tech.
      fontFamily: {
        heading: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        body:    ["Inter",            "system-ui", "sans-serif"],
      },
      // VN-01 / VN-02 — Vietnamese diacritics safety.
      lineHeight: {
        "vn-body":    "1.6",
        "vn-heading": "1.2",
      },
    },
  },
  plugins: [],
};
export default config;
