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

Public surface (cycle 15)
=========================

  ``tailwind_colors()``       — PR-D1, theme.extend.colors dict.
  ``tailwind_font_family()``  — PR-D1, theme.extend.fontFamily dict.
  ``to_json_dict()``          — PR-D2, design-tokens.json schema-v1 dict.
  ``to_css_variables()``      — PR-D2 + PR-D4, ``:root { --vck-* }`` CSS
                                string with optional ``@media
                                (prefers-color-scheme: dark)`` twin block.
  ``dark_mode_colors()``      — PR-D4, dark-mode CP-XX twin map
                                (CP-XX → dark HEX value).
"""
from __future__ import annotations

from typing import Mapping

from . import methodology as m


# --------------------------------------------------------------------------
# Schema URL & VN typography defaults — locked in cycle 15.
# --------------------------------------------------------------------------
_SCHEMA_URL = "https://vibecodekit.dev/schemas/design-tokens-v1.json"

_VN_TYPOGRAPHY = {
    # VN-01 — body line-height ≥ 1.6 to keep diacritics from clipping.
    "body_line_height": 1.6,
    # VN-02 — headings get 1.2 to stay tight while still giving room for
    # stacked accents on top of capitals (Ấ, Ằ, Ổ, …).
    "heading_line_height": 1.2,
    # VN-03 — body min font-size guidance: 16 px on mobile, 17 px on desktop;
    # we ship the conservative floor so callers can override upward.
    "body_min_font_px": 16,
    # VN-04 — letter-spacing 0 (negative spacing collapses diacritics).
    "letter_spacing_body": "0",
}


# Stable CP-XX → Tailwind token-name map (locked cycle 15, do not rename).
_CP_TOKEN_NAMES: Mapping[str, str] = {
    "CP-01": "vck-trust",
    "CP-02": "vck-energy",
    "CP-03": "vck-growth",
    "CP-04": "vck-luxury",
    "CP-05": "vck-warning",
    "CP-06": "vck-neutral",
}


# Known serif heading fonts in :data:`vibecodekit.methodology.FONT_PAIRINGS`
# — FP-03 "Creative" (Playfair Display) and FP-05 "Elegant"
# (Cormorant Garamond).  When either is selected we must terminate the
# fallback chain with the generic ``serif`` family so a missing web font
# does not collapse to a sans face and lose the design intent.  All
# other FP-XX heading + body fonts in the methodology are sans-serif.
_KNOWN_SERIF_FAMILIES: frozenset[str] = frozenset({
    "Playfair Display",
    "Cormorant Garamond",
})


def _generic_family(family: str) -> str:
    """Return the CSS generic family (``"serif"`` or ``"sans-serif"``).

    Looks the family up against :data:`_KNOWN_SERIF_FAMILIES`; defaults
    to ``"sans-serif"`` so any unclassified family stays safe (the
    methodology FONT_PAIRINGS body fonts are all sans-serif as of
    cycle 15).
    """
    if family in _KNOWN_SERIF_FAMILIES:
        return "serif"
    return "sans-serif"


# Dark-mode CP twin (locked cycle 15 PR-D4).  Each entry is the HEX value
# the ``--vck-*`` variable flips to inside
# ``@media (prefers-color-scheme: dark)``.  Rationale per row:
#
#   CP-01 Trust    blue-600 → blue-500    — reduce tone on dark surface.
#   CP-02 Energy   orange-500 → orange-400 — brighter pop on dark.
#   CP-03 Growth   green-500 → emerald-400 — warmer green on dark.
#   CP-04 Luxury   violet-600 → violet-500 — keep saturation on dark.
#   CP-05 Warning  red-500 → red-400      — quieter so it does not scream.
#   CP-06 Neutral  gray-500 → gray-400    — lift contrast on dark surface.
_DARK_MODE_CP_TWIN: Mapping[str, str] = {
    "CP-01": "#3B82F6",
    "CP-02": "#FB923C",
    "CP-03": "#34D399",
    "CP-04": "#8B5CF6",
    "CP-05": "#F87171",
    "CP-06": "#9CA3AF",
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
        "heading": [heading, "system-ui", _generic_family(heading)],
        "body": [body, "system-ui", _generic_family(body)],
    }


def to_json_dict(
    version: str,
    pairing_id: str = "FP-01",
) -> dict[str, object]:
    """Build the ``design/tokens.json`` payload (schema v1).

    Returned dict shape::

        {
          "$schema": "https://vibecodekit.dev/schemas/design-tokens-v1.json",
          "version": "<version>",
          "source":  "vibecodekit.methodology",
          "colors":  { "vck-trust": {...}, ... },
          "typography": { "heading": {...}, "body": {...} },
          "vn_typography": { ... }
        }

    The colour entries include the originating ``cp_id`` and human-readable
    ``meaning`` so downstream design tools (Figma plugin, Style Dictionary
    importer) can preserve provenance.  The schema URL is intentionally
    versioned (``-v1``) so a future schema change can land at ``-v2`` while
    older shipped scaffolds keep validating.
    """
    if pairing_id not in m.FONT_PAIRINGS:
        raise ValueError(
            f"Unknown font pairing id: {pairing_id!r}. "
            f"Known: {sorted(m.FONT_PAIRINGS)}"
        )
    heading_family, body_family, _mood = m.FONT_PAIRINGS[pairing_id]
    colors: dict[str, dict[str, str]] = {}
    for cp_id, (meaning, hex_value) in m.COLOR_PSYCHOLOGY.items():
        token = _token_name(cp_id)
        colors[token] = {
            "hex": hex_value,
            "cp_id": cp_id,
            "meaning": meaning,
        }
    return {
        "$schema": _SCHEMA_URL,
        "version": version,
        "source": "vibecodekit.methodology",
        "colors": colors,
        "typography": {
            "heading": {
                "fp_id": pairing_id,
                "stack": [
                    heading_family,
                    "system-ui",
                    _generic_family(heading_family),
                ],
            },
            "body": {
                "fp_id": pairing_id,
                "stack": [
                    body_family,
                    "system-ui",
                    _generic_family(body_family),
                ],
            },
        },
        "vn_typography": dict(_VN_TYPOGRAPHY),
    }


def dark_mode_colors() -> dict[str, str]:
    """Return the dark-mode twin of :func:`tailwind_colors`.

    Same key shape (``vck-*``) and same ordering as the light map so a
    pure key-zip is enough to compare the two; only the HEX values
    differ.  Used by :func:`to_css_variables` to emit the
    ``@media (prefers-color-scheme: dark)`` block.

    The schema-v1 :func:`to_json_dict` does **not** currently emit a
    ``dark_colors`` section — dark-mode lives only in the CSS layer
    via the ``@media`` block.  Surface here is the canonical Python
    entry point if a downstream tool (e.g. Figma plugin) needs the
    dark map without going through CSS.
    """
    return {
        _token_name(cp_id): _DARK_MODE_CP_TWIN[cp_id]
        for cp_id in m.COLOR_PSYCHOLOGY
    }


def to_css_variables(
    pairing_id: str = "FP-01",
    *,
    dark_mode: bool = True,
) -> str:
    """Render a ``:root { --vck-* }`` CSS block as a string.

    The output is deterministic given the methodology constants; the
    moving parts are:

    - ``pairing_id`` selects which FP pair to embed in
      ``--vck-font-heading`` / ``--vck-font-body``;
    - ``dark_mode`` (default ``True``) appends a
      ``@media (prefers-color-scheme: dark)`` block that flips the six
      ``--vck-*`` colour variables to their dark-mode twin.  Set to
      ``False`` if you only want the light scheme.

    The dark-mode block re-uses the very same variable names, so any
    Tailwind class (``bg-vck-trust``) or inline ``var(--vck-trust)``
    automatically inherits the dark twin without component code
    changes.
    """
    colors = tailwind_colors()
    fonts = tailwind_font_family(pairing_id)
    lines: list[str] = [
        "/* Generated from vibecodekit.methodology — DO NOT EDIT. */",
        "/* Regenerate via:                                       */",
        "/*   python3 -m vibecodekit.cli scaffold tokens-export    */",
        "/*       --scaffold <name> --pairing FP-XX                */",
        ":root {",
    ]
    for token, hex_value in colors.items():
        lines.append(f"  --{token}: {hex_value};")
    heading_stack = ", ".join(_quote_font(f) for f in fonts["heading"])
    body_stack = ", ".join(_quote_font(f) for f in fonts["body"])
    lines.extend([
        f"  --vck-font-heading: {heading_stack};",
        f"  --vck-font-body: {body_stack};",
        f"  --vck-line-height-body: {_VN_TYPOGRAPHY['body_line_height']};",
        f"  --vck-line-height-heading: {_VN_TYPOGRAPHY['heading_line_height']};",
        "}",
        "",
    ])
    if dark_mode:
        dark = dark_mode_colors()
        lines.append("@media (prefers-color-scheme: dark) {")
        lines.append("  :root {")
        for token, hex_value in dark.items():
            lines.append(f"    --{token}: {hex_value};")
        lines.append("  }")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def _quote_font(family: str) -> str:
    """Quote font-family names that contain spaces (CSS spec)."""
    if " " in family:
        return f'"{family}"'
    return family


__all__ = [
    "tailwind_colors",
    "tailwind_font_family",
    "to_json_dict",
    "to_css_variables",
    "dark_mode_colors",
]
