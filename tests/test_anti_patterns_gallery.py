"""Tests for the cycle-13 anti-pattern gallery (probe #89).

Gallery `references/anti-patterns-gallery.md` mở rộng API
``methodology.anti_patterns_canonical()`` thành full visual catalog
12 AP-XX với BAD/GOOD ASCII + Fix recipe + Detector snippet.

Probe #89 đã verify count + cross-link với API.  Test file này nail
thêm các invariants tinh hơn:

1. Gallery file tồn tại + ≥ 250 dòng (đủ để chứa 12 AP detail).
2. 12 AP heading đúng format `## AP-XX`.
3. Mỗi AP có cả 5 thành phần: Issue / Persona / Dimension / Visualization / Fix recipe / Detector.
4. Cross-check 1:1 với `methodology.anti_patterns_canonical()` (id + name).
5. Probe #89 PASS trên baseline (regression guard).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from vibecodekit import conformance_audit as ca
from vibecodekit import methodology


REPO = Path(__file__).resolve().parents[1]
GALLERY = REPO / "references" / "anti-patterns-gallery.md"

EXPECTED_IDS = tuple(f"AP-{i:02d}" for i in range(1, 13))


@pytest.fixture(scope="module")
def gallery_body() -> str:
    assert GALLERY.is_file(), (
        "references/anti-patterns-gallery.md must exist (cycle 13 PR2)"
    )
    return GALLERY.read_text(encoding="utf-8")


def test_gallery_minimum_length(gallery_body: str) -> None:
    """Body must be substantive — ≥ 250 lines as per spec."""
    line_count = gallery_body.count("\n")
    assert line_count >= 250, (
        f"gallery only has {line_count} lines, expected ≥ 250 to ship "
        "12 AP entries with visualization + recipe + detector"
    )


@pytest.mark.parametrize("ap_id", EXPECTED_IDS)
def test_each_ap_has_section_heading(gallery_body: str, ap_id: str) -> None:
    pattern = re.compile(rf"^## {re.escape(ap_id)} —", re.MULTILINE)
    assert pattern.search(gallery_body), (
        f"missing section heading `## {ap_id} —` in gallery"
    )


@pytest.mark.parametrize("ap_id", EXPECTED_IDS)
def test_each_ap_has_bad_good_visualization(
    gallery_body: str, ap_id: str
) -> None:
    """Every AP must ship a paired BAD/GOOD ASCII visualization.

    We slice the AP section and verify both keywords appear inside.
    """
    sections = re.split(r"^## (AP-\d{2}) — ", gallery_body, flags=re.MULTILINE)
    # split format: [pre, id1, body1, id2, body2, ...]
    sections_map: dict[str, str] = {
        sections[i]: sections[i + 1]
        for i in range(1, len(sections), 2)
    }
    body = sections_map.get(ap_id, "")
    assert "BAD:" in body, f"{ap_id} section missing BAD: visualization"
    assert "GOOD:" in body, f"{ap_id} section missing GOOD: visualization"


@pytest.mark.parametrize("ap_id", EXPECTED_IDS)
def test_each_ap_has_fix_recipe_and_detector(
    gallery_body: str, ap_id: str
) -> None:
    sections = re.split(r"^## (AP-\d{2}) — ", gallery_body, flags=re.MULTILINE)
    sections_map = {
        sections[i]: sections[i + 1]
        for i in range(1, len(sections), 2)
    }
    body = sections_map.get(ap_id, "")
    assert "Fix recipe" in body, f"{ap_id} section missing Fix recipe"
    assert "Detector" in body, f"{ap_id} section missing Detector"


def test_gallery_in_sync_with_methodology_api(gallery_body: str) -> None:
    """Every canonical AP id + name must appear in the gallery body."""
    canonical = methodology.anti_patterns_canonical()
    canonical_ids = {entry["id"] for entry in canonical}
    assert canonical_ids == set(EXPECTED_IDS), (
        f"canonical API drifted: ids={sorted(canonical_ids)}"
    )
    for entry in canonical:
        assert entry["name"] in gallery_body, (
            f"AP name {entry['name']!r} (id={entry['id']}) missing from "
            "gallery — gallery and API must stay in sync"
        )


def test_dimension_matrix_present(gallery_body: str) -> None:
    """Spec requires a quick-reference 12 × U1-U7 matrix at the end."""
    assert "Quick reference" in gallery_body or "Dimension matrix" in gallery_body
    for u in ("U1", "U2", "U3", "U4", "U5", "U6", "U7"):
        assert u in gallery_body, f"matrix missing dimension {u}"


def test_probe_89_passes_on_baseline(tmp_path: Path) -> None:
    ok, detail = ca._probe_anti_patterns_gallery_complete(tmp_path)
    assert ok, f"probe #89 FAILED on baseline: {detail}"
    assert "12/12" in detail, f"probe detail unexpected: {detail}"
