"""Behaviour-based conformance audit package (since v0.23.0 / cycle 14 β-1).

Each pattern in the methodology is verified by a *probe* — a small runtime
experiment exercised against a temp directory.  A probe is ``pass`` iff
it observes the documented behaviour.  File existence is never sufficient.

Run::

    python -m vibecodekit.conformance_audit --root /path/to/project

Exit code is 0 iff the parity score ≥ ``--threshold`` (default 0.85).

Layout (cycle 14 modularization)
================================

The original 2 246-line ``conformance_audit.py`` is being split into
this package over PRs β-1 → β-6:

    conformance/
        __init__.py        — public re-exports (this file)
        _runner.py         — audit() entry point + CLI main()
        _helpers.py        — shared utilities (find_slash_command, …)
        _registry.py       — @probe decorator (populates in β-6)
        probes_runtime.py     (β-2 — probes #1-30, runtime / 5-layer)
        probes_methodology.py (β-3 — probes #31-50, RRI / methodology)
        probes_assets.py      (β-4 — probes #51-70, scaffolds / assets)
        probes_governance.py  (β-5 — probes #71-92, governance / license)

For β-1, the package only owns the runner + helpers + registry.  All 91
probes still live in ``vibecodekit.conformance_audit`` and are picked
up by name through the existing ``PROBES`` list.

Back-compat
===========

External callers should import from ``vibecodekit.conformance_audit``
just like before — that module re-exports ``audit``, ``_main``, and the
``PROBES`` list.  The new symbols listed in ``__all__`` below are
additive; no breaking change to v0.22.x consumers.
"""
from ._helpers import find_slash_command
from ._registry import collect_registered, probe
from ._runner import audit, main

__all__ = [
    "audit",
    "main",
    "find_slash_command",
    "probe",
    "collect_registered",
]
