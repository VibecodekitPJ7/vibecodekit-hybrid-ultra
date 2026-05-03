# OSINT-style intelligence terminal — VibecodeKit scaffold

Pure-black canvas, JetBrains Mono, bordered panels, all-caps headers and status pills.
Heavily inspired by intelligence/OSINT command consoles (e.g. crucix.live).

## Stack

- Next.js 15 (App Router) + React 19 + TypeScript
- Tailwind CSS 3.4 with `<alpha-value>` opacity support on CSS-variable colors
- JetBrains Mono via `next/font/google`
- Recharts (optional — add yourself when wiring data viz)

## Run

```sh
npm install
npm run dev
```

Open http://localhost:3000 — the demo page renders a sample "Module 01" with all primitives wired up.

## What's in the box

| Layer | File | What it gives you |
|---|---|---|
| Tokens | `app/globals.css` | RGB-channel CSS variables (`--bg-canvas`, `--accent-cyan`, …), component classes (`.panel`, `.label-tag-*`, `.status-dot-*`, `.terminal-chip`) |
| Theme | `tailwind.config.ts` | Color tokens exposed via `rgb(var(--*) / <alpha-value>)` so utilities like `bg-panel/80`, `bg-accent-cyan/10` work |
| Layout | `app/layout.tsx` | JetBrains Mono font, scan-line body grid, fixed `Header` + footer |
| Header | `app/components/Header.tsx` | Sticky nav with active-state, status pills (`SOURCES`, `TOKEN`, live UTC+7 clock) |
| Primitives | `app/components/PagePrimitives.tsx` | `PageHeader`, `KpiList`, `DegradedBanner` — drop-in section building blocks |
| Demo | `app/page.tsx` | Module 01 example page wiring all primitives together |

## Customizing

- **Colors**: edit `:root` channels in `app/globals.css`. Use `rgb(var(--accent-cyan) / 0.4)` not `var(--accent-cyan)` (the latter resolves to an invalid color).
- **Nav items**: edit `NAV_ITEMS` in `app/components/Header.tsx`.
- **Module tag/heading**: pass `moduleTag`, `moduleLabel`, `title`, `subtitle` to `<PageHeader>`.
- **Token clock**: switch the `timeZone` string in `Header.tsx`'s `CLOCK_FORMATTER`.

## Notes

- The active-state matcher uses **exact match + segment-aware prefix** (`pathname === item.href || pathname.startsWith(item.href + "/")`) to avoid `/news` matching the `/new` prefix. Don't simplify back to `startsWith(item.href)`.
- All color CSS variables are stored as space-separated R G B channels (e.g. `--bg-panel: 12 18 24` not `#0c1218`). This is required for Tailwind's `<alpha-value>` placeholder to work. If you add new tokens, follow the same pattern.
