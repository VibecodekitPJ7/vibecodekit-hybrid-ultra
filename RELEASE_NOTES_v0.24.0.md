# Release Notes — v0.24.0 (2026-05-03)

**Cycle 15: design-apply polish.**

This release closes the "scaffolds chưa apply design tokens" gap surfaced
by the cycle 14 PJ8 audit.  After v0.24.0, a developer who runs
`vibe scaffold apply <preset>` for the 6 Next.js presets gets a
**token-driven theme**, **shipped design-token files**, **a sample
component library** (`saas` + `dashboard`), and a **dark-mode twin**
out-of-the-box — no manual Tailwind / shadcn / dark-theme wiring.

> Why: cycle 14 ended with `methodology.FONT_PAIRINGS` + `COLOR_PSYCHOLOGY`
> being canonical Python constants but **not exported** to the JS / CSS
> layers consumers actually use.  Scaffolds shipped with empty
> `theme.extend: {}`, no `design/tokens.{json,css}` files, no sample
> components, and no dark-mode token mapping.  Cycle 15 ships 4
> sequential PRs (D1 → D4) that wire everything end-to-end.

---

## TL;DR for users

You don't need to do anything new.  Existing scaffolds keep working; new
clones pick up the design layer automatically.

- `from vibecodekit.conformance_audit import PROBES, audit` — works.
- `python -m vibecodekit.conformance_audit` — works, prints
  **95 / 95** probes met (threshold 85 %, parity 100 %).
- `from vibecodekit.design_tokens_export import (
    tailwind_colors, tailwind_font_family, to_json_dict,
    to_css_variables, dark_mode_colors,
  )` — new public adapter module (5 helpers).
- Existing project on v0.23.0 wants the new design files?  Run the new
  adapter directly: `python3 -c "from vibecodekit.design_tokens_export
  import to_css_variables; print(to_css_variables())" >
  src/design/tokens.css`.

---

## What changed

### PR-D1 — Tailwind theme pre-wire (#16)

`tailwind.config.ts` for **all 6 Next.js scaffolds** (saas, dashboard,
landing-page, blog, portfolio, shop-online) now ships with a populated
`theme.extend`:

- `theme.extend.colors` → 6 `vck-*` tokens (`vck-trust`, `vck-energy`,
  `vck-growth`, `vck-luxury`, `vck-warning`, `vck-neutral`) sourced from
  `methodology.COLOR_PSYCHOLOGY`.
- `theme.extend.fontFamily.heading / body` → FP-01 "Modern Tech"
  (Plus Jakarta Sans + Inter) with system fallbacks.
- `theme.extend.lineHeight.vn-body / vn-heading` → VN-01 (1.6) and VN-02
  (1.2) so Vietnamese diacritics never clip.

New helper module `scripts/vibecodekit/design_tokens_export.py` is the
canonical adapter:

```python
from vibecodekit.design_tokens_export import tailwind_colors, tailwind_font_family

tailwind_colors()                # → {"vck-trust": "#2563EB", ...}
tailwind_font_family("FP-01")    # → {"heading": [...], "body": [...]}
```

The CP-XX → token-name mapping is **locked at cycle 15** so consumers can
rely on stable class names across releases.

Conformance probe `93_tailwind_prewire_design_tokens` verifies all 6
scaffolds wire ≥ 3 / 6 CP tokens + heading/body fontFamily.

### PR-D2 — design/tokens.{json,css} shipped (#17)

Each Next.js scaffold now ships **2 new files**:

- `design/tokens.json` (schema v1, `$schema` URL pinned) with full
  provenance (cp_id, meaning, fp_id, VN typography defaults).
- `design/tokens.css` (`:root { --vck-* }` block) so non-Tailwind code
  paths (inline SVG `stroke`, third-party widget config) can use
  `var(--vck-trust)`.

The 6 scaffold manifests register the new files in `files[]` and
`success_criteria[]` so `vibe scaffold preview` includes them.

New helpers:

```python
from vibecodekit.design_tokens_export import to_json_dict, to_css_variables

to_json_dict("0.24.0")        # → schema-v1 dict
to_css_variables("FP-01")     # → ":root { --vck-* }" CSS string
```

Conformance probe `94_design_tokens_files_shipped` verifies all 6
scaffolds ship both files with a 6-colour entry list and `:root` block.

### PR-D3 — sample shadcn-style component library (#18)

`saas` + `dashboard` (the 2 presets whose Vision recommends "Tailwind +
shadcn/ui") now ship a **hand-rolled** sample library:

- `lib/cn.ts` — canonical shadcn helper (`clsx + tailwind-merge`).
- `components/ui/button.tsx` — 3 variants (primary / secondary / ghost)
  × 3 sizes (sm / md / lg).
- `components/ui/input.tsx` — 3 states (default / error / disabled),
  `aria-invalid="true"` set automatically when `state="error"`.
- `components/ui/card.tsx` — 3 variants (default / elevated / bordered) +
  `Card` / `CardTitle` / `CardBody` composition.

Every component consumes `vck-*` tokens (e.g. `bg-vck-trust`,
`focus-visible:ring-vck-trust`, `text-vck-warning`) and imports `cn()`
from `@/lib/cn`.  Token rename → focus broken at **build time**, not in
production.

The `app/page.tsx` of both scaffolds was refactored to demo the
component library:

- `saas`: hero + nav + newsletter form (Button + Input) + 2 Card
  variants.
- `dashboard`: KPI cards using `<Card variant="elevated">` with delta
  colour switching between `vck-growth` (positive) and `vck-warning`
  (negative).

**Why hand-rolled, not `npx shadcn-ui init`?**  Zero new dependencies
beyond the shadcn-canonical `clsx` + `tailwind-merge`, no Radix
sub-package chain, direct token consumption (no `--primary` indirection
in `globals.css`), and a 4-file diff humans can read in 5 minutes.  The
project can still adopt full shadcn registry later — the cn-style API
shape is identical.

New reference doc:
[`references/41-component-library-pattern.md`](references/41-component-library-pattern.md)
(~150 lines: hand-roll vs init, anti-patterns, extension path to Radix).

Conformance probe `95_shadcn_samples_ship` verifies both scaffolds ship
all 3 components + cn() helper, each referencing at least one `vck-*`
token.

### PR-D4 — dark-mode twin + cross-link fix + release (this PR)

- New helper `dark_mode_colors()` returning the dark-mode twin map.
- `to_css_variables(..., dark_mode=True)` (default `True`) now appends a
  `@media (prefers-color-scheme: dark)` block that flips the 6 `--vck-*`
  variables to their dark twin.  The Tailwind class
  `bg-vck-trust` and inline `var(--vck-trust)` both inherit
  automatically — no component changes needed.
- All 6 `tokens.css` files regenerated with the dark block.
- `tokens.json` `version` bumped 0.23.0 → 0.24.0 for all 6 scaffolds.
- `references/anti-patterns-gallery.md` cross-links repaired
  (`13-rri-ux-critique.md` → `32-rri-ux-critique.md` after cycle 13
  reorg; `26-ui-checklist.md` (deleted) → `33-rri-ui-design.md`;
  `24-ux-vibecode-master.md` (renamed) → `30-vibecode-master.md`).
- `references/34-style-tokens.md` § 6 "Dark mode CP twin (v0.24.0)" added
  with rationale, programmatic access, and toggle-strategy guidance
  (`prefers-color-scheme` vs `.dark` class).
- Bug fix folded from PR-D3 Devin Review: saas `app/page.tsx` newsletter
  signup now uses `<form action="/api/newsletter" method="post">`
  instead of `<section>` — `<Button type="submit">` is no longer
  inert.

---

## Metrics

| Metric | v0.23.0 | v0.24.0 | Δ |
|:-------|:-------:|:-------:|:-:|
| Conformance probes | 92 / 92 | 95 / 95 | +3 |
| Test count | 1726 | ≥ 1735 | +9+ |
| Coverage TOTAL | ≥ 90 % | ≥ 90 % | = |
| Demo speed (`vibe demo`) | 1.27 s | ≤ 1.5 s | unchanged |
| Public API helpers (`design_tokens_export`) | 0 | 5 | +5 |
| Reference docs (style / UX) | 7 | 8 | +1 |
| Scaffolds with token theme pre-wired | 0 / 10 | 6 / 10 | +6 |
| Scaffolds shipping `design/tokens.{json,css}` | 0 / 10 | 6 / 10 | +6 |
| Scaffolds shipping sample component library | 0 / 10 | 2 / 10 | +2 |
| Dark-mode CP twins | 0 | 6 | +6 |

---

## Migration

**Non-breaking.**  Scaffolds shipped pre-v0.24.0 keep working without
touching anything; their `tailwind.config.ts` just stays empty.  To
back-port the design layer to an existing project, copy the relevant
file from a fresh scaffold preview or call the helpers directly:

```bash
# 1. Tailwind theme dict
PYTHONPATH=$(python3 -c "import vibecodekit; print(vibecodekit.__path__[0])")/.. \
  python3 -c "from vibecodekit.design_tokens_export import tailwind_colors; \
              import json; print(json.dumps(tailwind_colors(), indent=2))"

# 2. tokens.css
python3 -c "from vibecodekit.design_tokens_export import to_css_variables; \
            print(to_css_variables())" > src/design/tokens.css

# 3. tokens.json (locked to whatever vibecodekit version is installed)
python3 -c "from vibecodekit.design_tokens_export import to_json_dict; \
            from vibecodekit import __version__; \
            import json; print(json.dumps(to_json_dict(__version__), indent=2))" \
            > src/design/tokens.json
```

`methodology.__all__` is **unchanged** at 29 symbols — no symbol was
renamed or removed.  `design_tokens_export.__all__` grew from 0 to 5.

---

## Detailed PR list

| Plan | PR | Title | State |
|:-----|:---|:------|:------|
| D1 | #16 | Cycle 15 PR-D1: Tailwind theme pre-wire từ FP-01 + CP-01..CP-06 (probe #93) | merged |
| D2 | #17 | Cycle 15 PR-D2: ship design/tokens.json + tokens.css trong 6 scaffold (probe #94) | merged |
| D3 | #18 | Cycle 15 PR-D3: sample shadcn-style Button/Input/Card cho saas+dashboard (probe #95) | merged |
| D4 | (this) | Cycle 15 PR-D4: dark-mode CP twin + cross-link fix + release v0.24.0 | this release |

---

## Adding a new probe

(Pattern unchanged from v0.23.0.)  Add a `@probe("96_my_new_probe", group="...")`-decorated function in the appropriate
`scripts/vibecodekit/conformance/probes_*.py` module, returning
`Tuple[bool, str]`.  The decorator handles registration; the back-compat
shim picks it up via the registry on next import.  Then add a
`_probe_my_new_probe` re-export to `conformance_audit.py` so any
external monkey-patching keeps working.
