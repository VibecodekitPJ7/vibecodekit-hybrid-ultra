"""Cycle 15 PR-D1 — unit tests for ``design_tokens_export`` Tailwind helpers.

The helper is the canonical adapter between
:mod:`vibecodekit.methodology` (single source of truth) and the
``tailwind.config.ts`` files shipped in ``assets/scaffolds/<name>/nextjs/``.
These tests pin the locked CP-XX → Tailwind token mapping and the
default FP-01 font pairing so a downstream rename gets caught early.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_tailwind_colors_returns_six_cp_tokens() -> None:
    """All 6 CP-XX entries map to a ``vck-*`` Tailwind token name."""
    from vibecodekit.design_tokens_export import tailwind_colors

    colors = tailwind_colors()
    assert len(colors) == 6
    expected = {
        "vck-trust", "vck-energy", "vck-growth",
        "vck-luxury", "vck-warning", "vck-neutral",
    }
    assert set(colors) == expected


def test_tailwind_colors_returns_methodology_hex_values() -> None:
    """Each token resolves to the HEX value declared in ``COLOR_PSYCHOLOGY``."""
    from vibecodekit import methodology as m
    from vibecodekit.design_tokens_export import tailwind_colors

    colors = tailwind_colors()
    # CP-01 is canonical Trust/Professional and pinned at #2563EB.
    assert colors["vck-trust"] == "#2563EB"
    # Spot-check the source data is the only surface — flip any HEX in
    # methodology and the helper should follow.
    cp01_hex = m.COLOR_PSYCHOLOGY["CP-01"][1]
    assert colors["vck-trust"] == cp01_hex


def test_tailwind_font_family_default_fp01() -> None:
    """Default pairing FP-01 ships Plus Jakarta Sans + Inter."""
    from vibecodekit.design_tokens_export import tailwind_font_family

    ff = tailwind_font_family()
    assert ff["heading"][0] == "Plus Jakarta Sans"
    assert ff["body"][0] == "Inter"
    # Each stack must end with a system fallback so the page still
    # renders if the web font fails to load.
    assert ff["heading"][-1] == "sans-serif"
    assert ff["body"][-1] == "sans-serif"


def test_tailwind_font_family_explicit_pairing() -> None:
    """Explicit pairing id is honoured (not silently fallbacked to FP-01)."""
    from vibecodekit import methodology as m
    from vibecodekit.design_tokens_export import tailwind_font_family

    pairing = "FP-02"  # next pairing in the methodology
    if pairing not in m.FONT_PAIRINGS:
        pytest.skip(f"{pairing} not registered in methodology")
    heading_expected, body_expected, _mood = m.FONT_PAIRINGS[pairing]
    ff = tailwind_font_family(pairing)
    assert ff["heading"][0] == heading_expected
    assert ff["body"][0] == body_expected


def test_tailwind_font_family_invalid_id_raises() -> None:
    """Unknown FP-XX ids raise ``ValueError`` (no silent fallback)."""
    from vibecodekit.design_tokens_export import tailwind_font_family

    with pytest.raises(ValueError, match="FP-99"):
        tailwind_font_family("FP-99")


def test_six_nextjs_scaffolds_wire_vck_tokens() -> None:
    """Each shipped Next.js scaffold pre-wires ≥3 ``vck-*`` Tailwind tokens.

    This is the consumer-side companion to ``tailwind_colors()`` — it
    catches the case where a future scaffold copy-paste forgets to
    populate ``theme.extend.colors`` from the methodology.
    """
    scaffolds = (
        "saas", "dashboard", "landing-page",
        "blog", "portfolio", "shop-online",
    )
    locked = (
        "vck-trust", "vck-energy", "vck-growth",
        "vck-luxury", "vck-warning", "vck-neutral",
    )
    for s in scaffolds:
        cfg = _REPO / "assets" / "scaffolds" / s / "nextjs" / "tailwind.config.ts"
        assert cfg.exists(), f"{s}: missing tailwind.config.ts"
        text = cfg.read_text(encoding="utf-8")
        token_hits = sum(1 for n in locked if n in text)
        assert token_hits >= 3, (
            f"{s}: only {token_hits}/6 vck-* tokens wired in {cfg}"
        )
        assert "heading" in text and "body" in text, (
            f"{s}: missing fontFamily heading/body in {cfg}"
        )
