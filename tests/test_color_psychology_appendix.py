"""Tests for cycle-13 PR3 ``references/37-color-psychology.md`` (probe #90).

37-color-psychology.md mở rộng `34-style-tokens.md` §2 (CP-01..CP-06
generic) thành **7 industry-tuned palettes** với WCAG + VN cultural
+ color-blind safety + dark-mode mapping.

Tests verify behaviour-based invariants so that the file cannot
silently rot if someone trims a section.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit import conformance_audit as ca
from vibecodekit import methodology


REPO = Path(__file__).resolve().parents[1]
APPENDIX = REPO / "references" / "37-color-psychology.md"

EXPECTED_INDUSTRIES = (
    "Finance",
    "Healthcare",
    "E-commerce",
    "Education",
    "SaaS B2B",
    "Government",
    "Logistics",
)


@pytest.fixture(scope="module")
def body() -> str:
    assert APPENDIX.is_file(), (
        "references/37-color-psychology.md must exist (cycle 13 PR3)"
    )
    return APPENDIX.read_text(encoding="utf-8")


@pytest.mark.parametrize("industry", EXPECTED_INDUSTRIES)
def test_each_industry_palette_present(body: str, industry: str) -> None:
    assert industry in body, (
        f"industry {industry!r} missing — appendix must ship 7 palettes"
    )


def test_wcag_section_present(body: str) -> None:
    assert "WCAG" in body
    assert "4.5" in body, "must mention 4.5:1 AA contrast threshold"


def test_vietnamese_cultural_section_present(body: str) -> None:
    """VN cultural color associations: Tết / Đỏ / Vàng / Trắng."""
    assert "Tết" in body or "Vietnamese cultural" in body
    assert "Đỏ" in body or "Vàng" in body or "Trắng" in body


def test_color_blind_safety_section_present(body: str) -> None:
    assert "Color-blind" in body or "color-blind" in body
    assert "deuteranomaly" in body.lower() or "Deuteranomaly" in body


def test_dark_mode_mapping_present(body: str) -> None:
    assert "Dark mode" in body or "dark mode" in body.lower()
    assert "950" in body, "dark-mode bg should reference Tailwind 950 step"


def test_cross_link_to_style_tokens(body: str) -> None:
    """Appendix must cross-link to 34-style-tokens.md §2."""
    assert "34-style-tokens.md" in body


def test_methodology_list_references_includes_37(body: str) -> None:
    refs = methodology.list_references()
    found = [r for r in refs if r["filename"].startswith("37-")]
    assert found, (
        "list_references() should auto-pick up 37-color-psychology.md"
    )
    assert "color" in found[0]["title"].lower()


def test_probe_90_passes_on_baseline(tmp_path: Path) -> None:
    ok, detail = ca._probe_color_psychology_appendix(tmp_path)
    assert ok, f"probe #90 FAILED on baseline: {detail}"
    assert "industries" in detail or "7" in detail
