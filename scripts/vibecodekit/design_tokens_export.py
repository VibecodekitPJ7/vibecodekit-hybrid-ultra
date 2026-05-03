"""Export FP / CP / VN methodology constants to Tailwind / CSS-friendly shapes.

The single source of truth for design tokens lives in
:mod:`vibecodekit.methodology` (``FONT_PAIRINGS`` and
``COLOR_PSYCHOLOGY``).  This module is the consumer-side adapter that
converts those Python constants into the shapes downstream tools
(Tailwind config, CSS variables, design-tokens JSON) expect.

The CP-XX → Tailwind token name mapping is **locked** at cycle 15 so
projects can rely on stable class names (``bg-vck-trust`` etc.) across
releases.  Adding a new CP-NN must extend ``_CP_TOKEN_NAMES`` rather
than rename existing entries.
"""
from __future__ import annotations

from typing import Mapping

from . import methodology as m


# Stable CP-XX → Tailwind token-name map (locked cycle 15, do not rename).
_CP_TOKEN_NAMES: Mapping[str, str] = {
    "CP-01": "vck-trust",
    "CP-02": "vck-energy",
    "CP-03": "vck-growth",
    "CP-04": "vck-luxury",
    "CP-05": "vck-warning",
    "CP-06": "vck-neutral",
}


def _token_name(cp_id: str) -> str:
    """Return the locked Tailwind token name for a CP-XX id."""
    if cp_id not in _CP_TOKEN_NAMES:
        raise ValueError(
            f"Unknown color-psychology id: {cp_id!r}. "
            f"Known: {sorted(_CP_TOKEN_NAMES)}"
        )
    return _CP_TOKEN_NAMES[cp_id]


def tailwind_colors() -> dict[str, str]:
    """Return the Tailwind ``theme.extend.colors`` dict.

    Keys are the locked ``vck-*`` token names; values are HEX colours
    pulled directly from :data:`vibecodekit.methodology.COLOR_PSYCHOLOGY`.

    Example:
        >>> sorted(tailwind_colors())  # doctest: +ELLIPSIS
        ['vck-energy', 'vck-growth', 'vck-luxury', 'vck-neutral', 'vck-trust', 'vck-warning']
    """
    return {
        _token_name(cp_id): hex_value
        for cp_id, (_meaning, hex_value) in m.COLOR_PSYCHOLOGY.items()
    }


def tailwind_font_family(pairing_id: str = "FP-01") -> dict[str, list[str]]:
    """Return the Tailwind ``theme.extend.fontFamily`` dict for a pairing.

    The pairing is read from :data:`vibecodekit.methodology.FONT_PAIRINGS`
    (default ``FP-01`` "Modern Tech": Plus Jakarta Sans + Inter).  Each
    family is returned as a stack with system fallbacks so the page
    still renders if the web font fails to load.
    """
    if pairing_id not in m.FONT_PAIRINGS:
        raise ValueError(
            f"Unknown font pairing id: {pairing_id!r}. "
            f"Known: {sorted(m.FONT_PAIRINGS)}"
        )
    heading, body, _mood = m.FONT_PAIRINGS[pairing_id]
    return {
        "heading": [heading, "system-ui", "sans-serif"],
        "body": [body, "system-ui", "sans-serif"],
    }


__all__ = [
    "tailwind_colors",
    "tailwind_font_family",
]
