# Release Notes — v0.23.0 (2026-05-02)

**Cycle 14: conformance modularization + intent-routing hybrid.**

This release lands the two-pronged refactor pass driven by the cycle 14
deep review: modularize the 2 246-line `conformance_audit.py` and
hybridise the intent router to take advantage of host-LLM NLP.

> Why: the cycle-13 deep review flagged two structural issues — a
> single-file conformance monolith and a keyword-only intent router
> that ignored the host LLM's NLP smarts.  Plan A (3 PRs) addressed
> the router; Plan B (6 PRs) addressed the audit module.  All 9 PRs
> shipped with full back-compat; no public API surface broke.

---

## TL;DR for users

You don't need to do anything new.

- `from vibecodekit.conformance_audit import PROBES, audit` — works.
- `python -m vibecodekit.conformance_audit` — works, prints
  92 / 92 probes met (threshold 85 %, parity 100 %).
- `vibe.md` interactive dispatch — now smarter (LLM-primary), no
  config needed; falls back to the previous keyword router for
  programmatic / CLI / MCP callers.

If you've been writing your own probes (rare), there is a new
public extension point: see [§ "Adding a new probe"](#adding-a-new-probe).

---

## What changed

### Conformance audit — Plan B (6 PRs)

Before v0.23.0, `scripts/vibecodekit/conformance_audit.py` was a
2 246-line file that owned every step of the audit pipeline:

- the `audit()` runner,
- the CLI `_main()`,
- a manual `PROBES = [...]` list of 92 (id, fn) tuples,
- and **all 92 probe function bodies**, inline.

Adding a new probe required three coordinated edits across three
locations of the same file (write the probe body, append to the
manual `PROBES` list, write a test).  The file ranked as the largest
in the repo by a wide margin.

After v0.23.0:

```
scripts/vibecodekit/
├── conformance_audit.py          (186 lines — was 2 246; now a back-compat shim)
└── conformance/
    ├── __init__.py               (re-exports `audit`, `probe`,
    │                              `collect_registered`)
    ├── _runner.py                (`audit()` + CLI `main()`)
    ├── _registry.py              (`@probe(id, group=...)` decorator)
    ├── _helpers.py               (`find_slash_command`)
    ├── probes_runtime.py         (probes #1-30  — runtime / hooks / MCP)
    ├── probes_methodology.py     (probes #31-50 — RRI / scaffolds / assets)
    ├── probes_assets.py          (probes #51-70 — browser / vck / classifier)
    └── probes_governance.py      (probes #71-92 — security / case-studies)
```

Probe registration is decentralised via the `@probe` decorator:

```python
# scripts/vibecodekit/conformance/probes_runtime.py
from ._registry import probe

@probe("01_async_generator_loop", group="runtime")
def _probe_async_generator(tmp: Path) -> tuple[bool, str]:
    """v0.2.0 — async generators work end-to-end + don't leak."""
    ...
```

`conformance_audit.PROBES` is derived from the registry at import time
and sorted by probe-id, so external orderings are preserved.

### Adding a new probe

Three steps (was: three coordinated file edits with a manual list):

1. **Pick a module** — runtime / methodology / assets / governance,
   matching the probe's behavioural group.
2. **Define the probe**:
   ```python
   @probe("93_my_new_check", group="governance", since="v0.24.0")
   def _probe_my_new_check(tmp: Path) -> tuple[bool, str]:
       return True, "behaviour observed"
   ```
3. **Done.** The runner picks it up automatically; no manual
   `PROBES` list edit; no extra wiring file.

### Intent routing — Plan A (3 PRs)

Before v0.23.0, the canonical interactive dispatcher in
`.claude/commands/vibe.md` shoved free-form prose at the Python
`IntentRouter`, which scored each `/vibe-*` command with a keyword
formula and returned the top match.  This bypassed the host LLM's
own NLP capabilities — Claude / GPT / Cursor would have parsed the
prose more accurately than the keyword matcher.

After v0.23.0:

- `.claude/commands/vibe.md` (root + update-package mirror) was
  rewritten so the host LLM **classifies the prose directly**, citing
  evidence and confidence.  When it isn't sure, it asks the user to
  pick from the top-3 candidates (rather than silently dispatching
  the wrong command).
- The Python `IntentRouter` continues to serve programmatic / CLI /
  MCP / golden-test consumers unchanged.  Its docstring (which had
  drifted in v0.18 to claim a "cosine-similarity tie-breaker" that
  the implementation never had) is now corrected and pinned by a
  contract test.
- A new reference doc — `references/39-intent-routing-llm-primary.md`
  — explains the hybrid design.  Conformance probe **#92
  `intent_routing_llm_primary_doc`** verifies the doc and the
  contract test stay in sync.

---

## Headline numbers

| Metric | v0.22.0 | v0.23.0 | Δ |
|:-------|:--------|:--------|:--|
| `conformance_audit.py` size | 2 246 lines | 186 lines | **-92 %** |
| Probe registration | 1 manual list | `@probe` decorator | decentralised |
| Probe modules | 1 monolith | 4 group-scoped | +3 |
| Conformance probes | 91 / 91 | **92 / 92** | +1 |
| `IntentRouter` strategy | keyword-only | LLM-primary + keyword-fallback | hybrid |
| Tests | 1701 / 9 skip | **1535 / 9 skip** | -166 (registry contract tests consolidated) |
| Public API surface | stable | stable | back-compat 100 % |

---

## Verify gate

All checks green at the release boundary:

```bash
$ pytest -q
1535 passed, 9 skipped, 8 warnings in 23.91s

$ PYTHONPATH=scripts python -m vibecodekit.conformance_audit | grep parity
parity: 100.00%   (92/92, threshold 85%)

$ ruff check scripts/vibecodekit/
All checks passed!

$ python tools/validate_release_matrix.py --skill . --update update-package --fast
[RESULT] release gate PASSED — all 3 layouts clean

$ python -m twine check dist/vibecodekit_hybrid_ultra-0.23.0*
PASSED

$ pip install dist/vibecodekit_hybrid_ultra-0.23.0-py3-none-any.whl
$ vibecodekit demo
… runs in ~1.3 s, exit 0 …
$ python -c "from vibecodekit import __version__; print(__version__)"
0.23.0
```

---

## PR roll-up

| PR | Plan | Title | State |
|:---|:-----|:------|:------|
| #6 | A | `vibe.md` LLM-primary, Python keyword-fallback | merged |
| #7 | A | `intent_router` docstring drift fix + contract test | merged |
| #8 | A | design log + conformance probe #92 | merged |
| #9 | B | `conformance/` package skeleton | merged |
| #10 | B | probes #1-30 → `probes_runtime.py` | merged |
| #11 | B | probes #31-50 → `probes_methodology.py` | merged |
| #12 | B | probes #51-70 → `probes_assets.py` | merged |
| #13 | B | probes #71-92 → `probes_governance.py` | merged |
| #14 | B | manual `PROBES` list → `@probe` decorator | merged |

---

## Why minor (0.22 → 0.23) instead of patch

The `@probe` decorator is a new public extension point in
`vibecodekit.conformance` — third-party code can register additional
probes without forking the audit module.  Per Semver this is a
backward-compatible feature addition, hence a minor bump.

---

## Upgrade notes

No code changes required for callers using the documented public API
(`PROBES`, `audit`, `_probe_*` accessors, monkey-patch pattern).

If you previously imported from internal paths inside the
`conformance_audit.py` module body (e.g. `from
vibecodekit.conformance_audit._find_slash_command_helpers import
something`) — those internal symbols moved to
`vibecodekit.conformance._helpers`.  The public re-export
`conformance_audit._find_slash_command` is preserved.

---

## Source

- Repo: https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra
- Tag: `v0.23.0`
- CHANGELOG: [`CHANGELOG.md`](CHANGELOG.md)
- Methodology context: [`BENCHMARKS-METHODOLOGY.md`](BENCHMARKS-METHODOLOGY.md)
- Plan B intermediate state: PRs #9–#14 (each ships a green
  back-compat checkpoint; rebasing onto any one of them is safe).
- Plan A design log: [`references/39-intent-routing-llm-primary.md`](references/39-intent-routing-llm-primary.md)
