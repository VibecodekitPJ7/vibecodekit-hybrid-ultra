# Reference #42 — OSINT terminal UI template

**Status:** active (added in `osint-terminal` scaffold preset)
**Source:** field-tested in `TestPJkit02/Build-ui-git` AI Repo Tracker (PR #12 redesign,
visual reference https://www.crucix.live/).

## When to reach for this template

A user wants a "data console / intelligence dashboard / monitoring terminal"
look — pure-black canvas, monospace, cyan-on-black hierarchy, status pills,
terse all-caps headers. Common phrasings:

- "OSINT terminal", "intelligence dashboard"
- "command console", "monitoring console"
- "make it look like a terminal"
- VN: "trang điều khiển", "giao diện kiểu console"

The intent router (`scripts/vibecodekit/intent_router.py`) already includes
these phrases in the `BUILD` lane.

## What the preset gives you

```
assets/scaffolds/osint-terminal/nextjs/
├── app/
│   ├── components/
│   │   ├── Header.tsx            ← sticky nav + status pills + UTC+7 clock
│   │   └── PagePrimitives.tsx    ← <PageHeader> <KpiList> <DegradedBanner>
│   ├── globals.css               ← tokens + .panel/.label-tag-*/.status-dot-*
│   ├── layout.tsx                ← JetBrains Mono + body grid + Header + footer
│   └── page.tsx                  ← demo Module 01 wiring all primitives
├── tailwind.config.ts            ← rgb(var(--*) / <alpha-value>) color theme
├── package.json, tsconfig.json, next.config.ts, vercel.json, .gitignore, .env.example
└── README.md
```

## Design tokens — the `RGB-channel` rule

All color tokens are stored in `:root` as **space-separated R G B integer
channels** — _not_ hex strings:

```css
:root {
  --bg-canvas: 5 10 14;       /* #050a0e */
  --accent-cyan: 54 230 216;  /* #36e6d8 */
}
```

This is required for Tailwind v3.4's `<alpha-value>` placeholder to
compose: `bg-panel/80`, `bg-accent-cyan/10`, etc. With hex values behind
a CSS variable Tailwind silently drops the opacity utility.

**Mandatory consequence:** never reference these variables as bare
`var(--accent-cyan)` in raw CSS — they will resolve to invalid colors.
Always wrap with `rgb(var(--accent-cyan))` or `rgb(var(--accent-cyan) / 0.4)`.

## Anti-patterns to avoid

| Anti-pattern | Why it fails |
|---|---|
| `pathname.startsWith(item.href)` for nav active-state | `/news` matches `/new` prefix; both nav items light up. Use exact match + `pathname.startsWith(item.href + "/")` instead. |
| `style={{ borderLeftColor: "var(--accent-red)" }}` next to a Tailwind utility setting the same property | After RGB-channel migration the inline value resolves to invalid color and overrides the Tailwind utility. Drop the inline style; the utility wins. |
| `color: var(--text-muted)` in raw CSS | Same RGB-channel rule — wrap with `rgb()`. |
| `Intl.DateTimeFormat()` constructed inside the render body | Recreates the formatter on every tick (default `setInterval(1000)`). Hoist to module scope. |
| `--accent-red: #ff4d6d;` mixed in with channel tokens | Breaks the alpha-value rule for that single token. Be 100% consistent across the palette. |

## Checklist before declaring "done" on a redesign

1. `rg 'var\(--' app/ | grep -v 'rgb(var'` returns empty (no naked `var(--*)` color refs).
2. `bg-{token}/{n}` and `border-{token}/{n}` opacity utilities appear in compiled CSS bundle (`grep '\.bg-panel\\/80' .next/static/.../*.css`).
3. Nav active-state correctly highlights only the current route, not prefix collisions.
4. Live clock label renders `YYYY-MM-DD HH:mm:ss UTC+N` (or your chosen tz).
5. `prefers-reduced-motion: reduce` strips animated grid/scan-line.
6. Focus rings visible against both pure-black canvas and panel bg.

## Related references

- #18 (terminal-as-browser) — design philosophy / TUI policy (different scope).
- #34 (style tokens) — generic token design rules.
- #37 (color psychology) — how cyan/red/amber map to "signal / alert / warn".
- #38 (font pairing) — JetBrains Mono pairs with `ui-monospace` fallback chain.
