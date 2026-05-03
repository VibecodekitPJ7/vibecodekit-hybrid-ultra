# Release Notes — v0.25.0 (2026-05-01)

**Cycle 16: 11th scaffold preset — `osint-terminal`.**

This release adds a single, distinct UI/UX scaffold preset that none of
the existing 10 presets covered: a **cyan-on-black command-console
look** (OSINT terminal / intelligence dashboard / monitoring console).
Distilled from the field-tested production app
[`TestPJkit02/Build-ui-git`](https://www.crucix.live/) PR #12 redesign.

After v0.25.0, a developer who types
*"make me an osint terminal"*, *"build intelligence dashboard"*,
*"trang điều khiển"*, or *"command console"* into the LLM-driven
`/vibe-scaffold` flow gets a runnable Next.js 15 + Tailwind v3.4 +
JetBrains Mono shell with three reusable layout primitives and an
`<alpha-value>`-aware token system out of the box.

> Why: the existing 10 presets all lean modern-SaaS / docs / portfolio.
> When a user wants a "data console / monitoring terminal" look the
> tool had no template — the LLM would either improvise (drift) or
> reach for `npx shadcn-ui init` and hard-code HEX colours (anti-pattern
> from cycle 15 ref #41).  Cycle 16 closes that gap with one new preset
> + one new reference doc + 10 new BUILD-lane intent keywords + a
> conformance probe that locks the design contract.

---

## TL;DR for users

You don't need to do anything new.  Existing scaffolds keep working;
new clones pick up the new preset automatically.

- `from vibecodekit.scaffold_engine import ScaffoldEngine`
  — `engine.list_presets()` now returns **11** presets (was 10).
- `engine.apply("osint-terminal", target, "nextjs")` writes 14 files,
  0 verify issues; `npm install && next build` produces 4 static
  routes with the OSINT terminal look.
- `python -m vibecodekit.conformance_audit` — works, prints
  **96 / 96** probes met (threshold 85 %, parity 100 %).
- `from vibecodekit.intent_router import IntentRouter` — phrases like
  *"make me an osint terminal"* now route to `BUILD`;
  *"tạo trang điều khiển"* / *"build intelligence dashboard"* route
  to the full `SCAN → VISION → RRI → BUILD → VERIFY` pipeline.

---

## What's in PR-E1 (single PR this cycle)

### 1. `osint-terminal` scaffold preset (11th preset)

Path: `assets/scaffolds/osint-terminal/`

```
osint-terminal/
├── manifest.json                          # name + description + nextjs files + 16 success_criteria
└── nextjs/
    ├── package.json                       # next ^15, react ^19, tailwindcss ^3.4
    ├── tsconfig.json
    ├── next.config.ts
    ├── postcss.config.js
    ├── tailwind.config.ts                 # rgb(var(--*) / <alpha-value>) colour theme
    ├── vercel.json
    ├── .env.example                       # HAS_TOKEN=0|1
    ├── .gitignore
    ├── README.md
    └── app/
        ├── layout.tsx                     # JetBrains Mono via next/font + Header + footer
        ├── page.tsx                       # MOD-01 demo wiring 3 primitives
        ├── globals.css                    # RGB-channel tokens + scan-line bg
        └── components/
            ├── Header.tsx                 # sticky nav + UTC+7 clock + status pills
            └── PagePrimitives.tsx         # <PageHeader>, <KpiList>, <DegradedBanner>
```

14 files copied verbatim by `engine.apply()`; `engine.verify()`
returns 0 issues.

### 2. Design contract — RGB-channel pattern

Colour tokens live in `app/globals.css :root` as **space-separated
R G B integer channels** (no `rgb()` wrapper, no `#hex`):

```css
:root {
  --bg-canvas: 5 10 14;          /* #050a0e */
  --bg-panel:  12 18 24;         /* #0c1218 */
  --accent-cyan:  54 230 216;    /* #36e6d8 */
  --accent-amber: 255 193 77;    /* #ffc14d */
  --accent-red:   255  77 109;   /* #ff4d6d */
  --accent-green: 110 231 183;   /* #6ee7b7 */
}
```

`tailwind.config.ts` consumes them via
`rgb(var(--accent-cyan) / <alpha-value>)`, which is the precondition
for Tailwind v3.4 opacity utilities like `bg-panel/80` and
`bg-accent-cyan/10` to compose correctly.  Naked `var(--accent-cyan)`
in raw CSS resolves to an invalid colour — see ref #42 anti-pattern
table for the trap.

### 3. Reference doc `references/42-osint-terminal-template.md`

~80 lines covering:
- When to reach for this template (English + VN phrasings)
- Required tooling (Next.js 15, Tailwind v3.4+, JetBrains Mono)
- Design tokens — the RGB-channel rule
- Layout primitives (`<PageHeader>`, `<KpiList>`, `<DegradedBanner>`)
- Anti-patterns checklist (e.g. `pathname.startsWith(item.href)` for
  nav active-state — `/news` matches `/new` prefix; both nav items
  light up — use exact match + `pathname.startsWith(item.href + "/")`
  instead).

> Note on numbering: bundle shipped this as `references/41-…` but
> cycle 15 PR-D3 already claimed slot 41 with the
> `component-library-pattern.md` reference.  The osint-terminal ref
> was renumbered to 42 to avoid the collision.

### 4. Intent router — 10 new keywords + 10 new pipeline phrases

`scripts/vibecodekit/intent_router.py`:

- **BUILD lane** (single-step scaffold): `osint`, `osint terminal`,
  `intelligence dashboard`, `command console`, `monitoring console`,
  `trang điều khiển`, `trang dieu khien` (no-diacritic),
  `giao diện kiểu console`, `giao dien kieu console`,
  `make it look like a terminal`, `terminal ui`.
- **FULL_BUILD lane** (full SCAN→VISION→RRI→BUILD→VERIFY pipeline):
  `build osint`, `build osint terminal`, `tạo osint`, `tao osint`,
  `build intelligence dashboard`, `tạo trang điều khiển`,
  `tao trang dieu khien`, `build command console`,
  `build monitoring console`, `build terminal ui`.

`benchmarks/intent_router_0.25.0.json` regenerated:
`set_inclusion_accuracy=0.98`, `exact_match_accuracy=0.89`,
`per_locale={'en': 0.96, 'vi': 1.0}`.

### 5. Conformance probe #96 `osint_terminal_scaffold_ship`

Path: `scripts/vibecodekit/conformance/probes_governance.py`

Beyond mere file presence the probe verifies four contract pieces:

1. `app/globals.css` declares space-separated R G B channel variables
   (regex `--bg-canvas:\s*\d+\s+\d+\s+\d+\s*;` matched).
2. `app/layout.tsx` imports `JetBrains_Mono` from `next/font/google`.
3. `app/components/PagePrimitives.tsx` exports the three named
   primitives `PageHeader`, `KpiList`, `DegradedBanner`.
4. `tailwind.config.ts` consumes RGB channels via
   `rgb(var(--*) / <alpha-value>)` (not bare `var(--*)`).

Audit total: 95 → 96 met=true at v0.25.0.

### 6. Banner / count synchronisation (boring but mandatory)

Forward-facing surfaces all bumped:

- `README.md`: 95/95 → 96/96, 10 presets → 11 presets, v0.24.0 → v0.25.0.
- `USAGE_GUIDE.md` + `update-package/USAGE_GUIDE.md`: same + "10 preset
  × 3 stack = 30 starter project" → "11 preset × 3 stack = 33 starter
  project".
- `update-package/README.md`, `update-package/CLAUDE.md`,
  `docs/GUIDE_NONTECH_BEGINNER.md`, `QUICKSTART.md`: probe count + version.
- `SKILL.md`, `examples/README.md`, `tools.json`,
  `scripts/vibecodekit/mcp_servers/core.py`,
  `references/00-overview.md`: preset count.
- `update-package/.claude/commands/vibe-scaffold.md`: frontmatter
  description "9 presets × 3 stacks" → "11 presets × 3 stacks".

`CHANGELOG.md`, `RELEASE_NOTES_v0.{22,23,24}.0.md`, and historical
sections of `references/{34,41}-*.md` keep their original v0.24.0 /
95-probe text — they describe past releases and must remain frozen.

---

## What this release explicitly does NOT include

- **No data layer.**  The `osint-terminal` preset ships a UI shell
  with KPI/feed demo data only — no GitHub/HN/RSS fetching, no auth,
  no analytics, no DB.  Consumers wire their own data sources into
  the `<KpiList>` / feed slots.
- **No fastapi or expo stack variant.**  The original osint look is
  inherently a browser dashboard; ports to other stacks are
  out-of-scope.  Other 9 nextjs presets continue to cover modern-SaaS /
  docs / portfolio looks.
- **No dark-mode toggle.**  The preset is dark-only by design (it's a
  command console).  The 6 cycle-15 design-token presets continue to
  ship the prefers-color-scheme dark twin for sites that need both.
- **No core runtime touch.**  `permission_engine`, `scaffold_engine`,
  `verb_router`, `denial_store`, `_audit_log`, `tool_executor`,
  `team_mode`, `task_runtime`, `subagent_runtime` — all unchanged.

---

## Verification matrix

| Check | Expected | Result |
|:------|:--------:|:------:|
| `pytest tests/ -q` | 1740+ pass at v0.24.0 baseline | **see CI** |
| `python -m vibecodekit.conformance_audit` | **96 / 96** met=true | ✓ |
| `validate_release_matrix --fast` | L1 / L2 / L3 PASSED | **see CI** |
| `engine.list_presets()` count | **11** | ✓ |
| `engine.apply("osint-terminal", …, "nextjs")` | 14 files, 0 verify issues | ✓ |
| `globals.css` RGB-channel regex | `--bg-canvas: 5 10 14;` matched | ✓ |
| `layout.tsx` JetBrains Mono | `next/font/google` import present | ✓ |
| `tailwind.config.ts` `<alpha-value>` | `rgb(var(--*) / <alpha-value>)` present | ✓ |
| Intent router benchmark | set_inclusion ≥ 0.95 at v0.25.0 | **0.98** ✓ |

---

## Upgrade

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.25.0
# or, from source:
git pull origin main
git checkout v0.25.0
pip install -e .
```

No migration steps; no breaking changes; no public API removal.
