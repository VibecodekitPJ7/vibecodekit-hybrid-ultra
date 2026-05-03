"""Decorator-based probe registry.

Source of truth for the 92 conformance probes since cycle 14 PR β-6.
Each ``probes_*.py`` module decorates its functions with ``@probe(id,
group=...)``; the decorator appends them to the module-global
``_REGISTRY`` list at import time.  ``conformance_audit.PROBES``
exposes a sorted snapshot for back-compat.

Public API
==========

``@probe(id, *, group=..., since=...)``
    Decorator that appends ``(id, fn)`` to the global registry.  Use
    on a top-level function ``def fn(tmp: Path) -> tuple[bool, str]:``.

``collect_registered() -> list[(id, fn)]``
    Snapshot the registry in registration order.  Used by the runner
    via ``conformance_audit.PROBES`` (which sorts the snapshot by
    probe-id so the audit output preserves v0.22.x ordering).

Adding a new probe
==================

1. Pick the probes_*.py module that matches the probe's behavioural
   group (runtime / methodology / assets / governance).
2. Define ``def _probe_<canonical_name>(tmp: Path) -> tuple[bool, str]``
   and decorate with ``@probe("<NN>_<canonical_name>", group="<group>")``.
3. That's it — the runner picks it up automatically; no manual
   ``PROBES`` list edit is required.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional, Tuple

ProbeFn = Callable[[Path], Tuple[bool, "str"]]
ProbeEntry = Tuple[str, ProbeFn]

_REGISTRY: List[ProbeEntry] = []


def probe(id: str, *, group: str = "uncategorised",
          since: Optional[str] = None) -> Callable[[ProbeFn], ProbeFn]:
    """Register a probe function in the global registry.

    Parameters
    ----------
    id:
        Stable probe identifier (e.g. ``"01_async_generator_loop"``).
        Becomes the row key in audit output.  Must be unique across
        the registry.
    group:
        Logical bucket (``runtime``/``methodology``/``assets``/
        ``governance``) — used by β-3+ for filtering and reporting.
    since:
        Tool version that introduced the probe (e.g. ``"v0.22.0"``).
        Optional, currently informational only.

    Returns
    -------
    A decorator that returns the probe function unchanged after
    appending it to ``_REGISTRY``.
    """
    del group, since  # reserved for β-6+ — silences linters today

    def deco(fn: ProbeFn) -> ProbeFn:
        for existing_id, _ in _REGISTRY:
            if existing_id == id:
                raise ValueError(
                    f"probe id collision: {id!r} already registered"
                )
        _REGISTRY.append((id, fn))
        return fn

    return deco


def collect_registered() -> List[ProbeEntry]:
    """Return the registered probes in insertion order (snapshot copy)."""
    return list(_REGISTRY)


def _reset_for_tests() -> None:
    """Drop all registry entries.  Test-only helper."""
    _REGISTRY.clear()
