"""Decorator-based probe registry.

Empty-by-design in β-1.  The current 92 probes still live in
``vibecodekit.conformance_audit`` and are wired through the manual
``PROBES`` list defined there.  PRs β-2 → β-5 will move probes into
sibling modules (still using the manual list).  PR β-6 will switch the
manual list out for ``@probe`` decorators on each probe function.

Public API
==========

``@probe(id, *, group=..., since=...)``
    Decorator that appends ``(id, fn)`` to the global registry.  Use
    on a top-level function ``def fn(tmp: Path) -> tuple[bool, str]:``.

``collect_registered() -> list[(id, fn)]``
    Snapshot the registry in registration order.  Used by the runner
    once β-6 is shipped.

Until β-6 the registry stays empty.  External callers should still go
through ``vibecodekit.conformance_audit.PROBES`` for the canonical
probe list, which the runner (`_runner.audit`) consumes by default.
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
