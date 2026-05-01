"""Tests for cycle-13 PR3 ``references/38-font-pairing.md`` (probe #91).

38-font-pairing.md mở rộng `34-style-tokens.md` §1 (FP-01..FP-06
generic) thành **5 use-case font stacks** với Vietnamese subset
support, type scale ladder, loading strategy + fallback chain.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit import conformance_audit as ca
from vibecodekit import methodology


REPO = Path(__file__).resolve().parents[1]
APPENDIX = REPO / "references" / "38-font-pairing.md"

EXPECTED_FONTS = ("Inter", "Plus Jakarta Sans", "Be Vietnam Pro", "DM Sans")
EXPECTED_PAIRS = (
    "Modern SaaS",
    "Corporate",
    "Editorial",
    "Tech-forward",
    "Friendly consumer",
)


@pytest.fixture(scope="module")
def body() -> str:
    assert APPENDIX.is_file(), (
        "references/38-font-pairing.md must exist (cycle 13 PR3)"
    )
    return APPENDIX.read_text(encoding="utf-8")


@pytest.mark.parametrize("font", EXPECTED_FONTS)
def test_each_font_present(body: str, font: str) -> None:
    assert font in body, f"font {font!r} missing"


@pytest.mark.parametrize("pair", EXPECTED_PAIRS)
def test_each_use_case_pair_present(body: str, pair: str) -> None:
    assert pair in body, f"use-case pair {pair!r} missing"


def test_vietnamese_subset_section_present(body: str) -> None:
    assert "Vietnamese subset" in body
    # smoke-test paragraph for diacritic rendering
    assert "Ứng dụng quản lý" in body or "diacritic" in body.lower()


def test_type_scale_present(body: str) -> None:
    assert "Type scale" in body or "line height" in body.lower()
    # check the canonical body desktop / mobile size cue
    assert "16" in body and "px" in body


def test_loading_strategy_present(body: str) -> None:
    assert "next/font/google" in body or "display" in body.lower()
    assert "swap" in body.lower(), "must mention font-display: swap"


def test_fallback_stack_present(body: str) -> None:
    assert "fallback" in body.lower()
    # Tailwind-style fallback chain
    assert "system-ui" in body
    assert "sans-serif" in body


def test_cross_link_to_style_tokens(body: str) -> None:
    assert "34-style-tokens.md" in body


def test_methodology_list_references_includes_38(body: str) -> None:
    refs = methodology.list_references()
    found = [r for r in refs if r["filename"].startswith("38-")]
    assert found, "list_references() should auto-pick up 38-font-pairing.md"
    assert "font" in found[0]["title"].lower()


def test_probe_91_passes_on_baseline(tmp_path: Path) -> None:
    ok, detail = ca._probe_font_pairing_appendix(tmp_path)
    assert ok, f"probe #91 FAILED on baseline: {detail}"
    assert "5 pairs" in detail or "fallback" in detail
