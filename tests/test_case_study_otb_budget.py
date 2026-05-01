"""Tests for the cycle-13 OTB Budget pre-baked case study (probe #88).

Bài case study được ship dưới ``references/examples/01-otb-budget-module/``
phục vụ onboarding cho team mới: 11 file `.md`/`.jsonl` + 2 sub-folder
``05-tips/`` và ``06-completion-reports/``.  Conformance probe #88 đã
verify file existence + 2 RRI gates, nhưng các test dưới đây nail
thêm:

1. Toàn bộ file kỳ vọng tồn tại (file tree contract).
2. ``07-rri-t-results.jsonl`` parse + gate=PASS qua ``methodology.evaluate_rri_t``.
3. ``08-rri-ux-results.jsonl`` parse + gate=PASS qua ``methodology.evaluate_rri_ux``.
4. README cross-link tới mọi file con (anchor sanity).
5. Probe #88 PASS trên baseline (regression guard nếu ai đó xoá file).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vibecodekit import conformance_audit as ca
from vibecodekit import methodology


REPO = Path(__file__).resolve().parents[1]
CASE_STUDY = REPO / "references" / "examples" / "01-otb-budget-module"

EXPECTED_FILES = (
    "README.md",
    "00-scan-report.md",
    "01-rri-requirements.md",
    "02-vision.md",
    "03-blueprint.md",
    "04-task-graph.md",
    "07-rri-t-results.jsonl",
    "08-rri-ux-results.jsonl",
    "09-coverage-matrix.md",
    "10-verify-report.md",
)


def test_case_study_directory_exists() -> None:
    assert CASE_STUDY.is_dir(), (
        "Case study root references/examples/01-otb-budget-module/ "
        "must exist (cycle-13 PR1 contract)."
    )


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_case_study_required_file_present(filename: str) -> None:
    path = CASE_STUDY / filename
    assert path.is_file(), f"missing case-study file: {filename}"
    assert path.stat().st_size > 0, f"case-study file is empty: {filename}"


def test_case_study_subfolders_have_content() -> None:
    tips = CASE_STUDY / "05-tips"
    reports = CASE_STUDY / "06-completion-reports"
    assert tips.is_dir() and any(tips.iterdir()), (
        "05-tips/ must ship at least one TIP spec"
    )
    assert reports.is_dir() and any(reports.iterdir()), (
        "06-completion-reports/ must ship at least one completion report"
    )
    tip_files = sorted(p.name for p in tips.glob("tip-*-spec.md"))
    report_files = sorted(p.name for p in reports.glob("tip-*-report.md"))
    assert len(tip_files) >= 3, f"need ≥3 TIP specs, found {tip_files}"
    assert len(report_files) >= 3, (
        f"need ≥3 completion reports, found {report_files}"
    )


def test_rri_t_results_gate_pass() -> None:
    out = methodology.evaluate_rri_t(CASE_STUDY / "07-rri-t-results.jsonl")
    assert out["gate"] == "PASS", (
        f"RRI-T gate FAIL: reasons={out['reasons']} "
        f"per_dim={out['per_dimension']}"
    )
    assert not out["missing_dimensions"], (
        f"RRI-T missing dimensions: {out['missing_dimensions']}"
    )
    assert out["summary"]["total"] >= 15, (
        "RRI-T sample should ship ≥15 entries to be a meaningful example, "
        f"got {out['summary']['total']}"
    )


def test_rri_ux_results_gate_pass() -> None:
    out = methodology.evaluate_rri_ux(CASE_STUDY / "08-rri-ux-results.jsonl")
    assert out["gate"] == "PASS", (
        f"RRI-UX gate FAIL: reasons={out['reasons']} "
        f"per_dim={out['per_dimension']}"
    )
    assert not out["missing_dimensions"], (
        f"RRI-UX missing dimensions: {out['missing_dimensions']}"
    )
    assert out["summary"]["total"] >= 15, (
        "RRI-UX sample should ship ≥15 entries to be a meaningful example, "
        f"got {out['summary']['total']}"
    )


def test_readme_cross_links_to_every_file() -> None:
    readme = (CASE_STUDY / "README.md").read_text(encoding="utf-8")
    # Each numbered file must appear as a link target in the README so
    # newcomers can navigate the case study without guessing.
    for fname in EXPECTED_FILES:
        if fname == "README.md":
            continue
        assert fname in readme, (
            f"README.md missing cross-link to {fname!r}"
        )
    # Also link the two subfolders.
    assert "05-tips" in readme and "06-completion-reports" in readme, (
        "README.md must reference both 05-tips/ and 06-completion-reports/"
    )


def test_probe_88_passes_on_baseline(tmp_path: Path) -> None:
    """Regression guard: probe #88 must PASS on shipped baseline."""
    ok, detail = ca._probe_case_study_otb_budget(tmp_path)
    assert ok, f"probe #88 FAILED on baseline: {detail}"
    assert "rri_t=PASS" in detail and "rri_ux=PASS" in detail, (
        f"probe detail should reference both gates, got: {detail}"
    )
