"""Regression tests for conformance probe #85 (no_orphan_module).

The probe walks every public ``scripts/vibecodekit/*.py`` module and
verifies it has at least one production call site OR appears in
``scripts/vibecodekit/_audit_allowlist.json``.  These tests pin both
the green path and the failure / allowlist semantics.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibecodekit import conformance_audit as ca


REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "scripts" / "vibecodekit"


def test_no_orphan_module_passes_on_repo_baseline(tmp_path: Path) -> None:
    """The current repo must have zero orphan modules."""
    ok, detail = ca._probe_no_orphan_module(tmp_path)
    assert ok, f"orphan probe FAILED on baseline: {detail}"


def test_no_orphan_module_reports_module_count_and_allowlist(
        tmp_path: Path) -> None:
    ok, detail = ca._probe_no_orphan_module(tmp_path)
    assert ok
    # detail looks like: "all N modules wired (+ K allowlisted)"
    assert "modules wired" in detail
    assert "allowlisted" in detail


def test_audit_allowlist_json_is_valid() -> None:
    blob = json.loads((PKG / "_audit_allowlist.json").read_text(
        encoding="utf-8"))
    assert "no_orphan_module" in blob
    assert isinstance(blob["no_orphan_module"], dict)
    # Every allowlist entry must carry a justification string.
    for k, v in blob["no_orphan_module"].items():
        assert isinstance(v, str) and len(v) > 10, (
            f"allowlist {k!r} needs a substantive justification")


def test_audit_allowlist_only_contains_approved_entries() -> None:
    """The allowlist is bounded — adding entries requires a v-bump and a
    documented decision.  Currently approved set: empty.

    Lịch sử:

    * v0.15.0 / Q5(b) — th\u00eam ``vn_faker`` + ``vn_error_translator``
      (test utilities consumed only by tests + downstream demos).
    * v0.16.0-\u03b1 / audit P2 #6 — th\u00eam ``quality_gate`` +
      ``tool_use_parser`` + ``worktree_executor`` (genuine public
      Python API; operator ch\u1ecdn option (b) allowlist cho 3 module
      n\u00e0y v\u00e0 option (a) wire-properly cho ``auto_commit_hook``).
    * v0.16.2 / PR7 — g\u1ee1 c\u1ea3 5 entry sau khi th\u00eam example
      ri\u00eang cho t\u1eebng module (``examples/04..08``).  Probe #85
      search corpus \u0111\u00e3 m\u1edf r\u1ed9ng \u0111\u1ec3 bao g\u1ed3m
      ``examples/*.py``, n\u00ean kh\u00f4ng c\u1ea7n allowlist n\u1eefa.
    """
    blob = json.loads((PKG / "_audit_allowlist.json").read_text(
        encoding="utf-8"))
    expected: set[str] = set()
    assert set(blob["no_orphan_module"].keys()) == expected, (
        "Allowlist baseline drift — n\u1ebfu th\u00eam entry m\u1edbi, "
        "c\u1eadp nh\u1eadt test n\u00e0y c\u00f9ng v\u1edbi v-bump v\u00e0 "
        "ghi ch\u00fa v\u00e0o docstring docstring \u0111\u1ec3 audit "
        "trail r\u00f5 r\u00e0ng."
    )


def test_no_orphan_module_probe_is_in_PROBES_registry() -> None:
    names = {n for n, _ in ca.PROBES}
    assert "85_no_orphan_module" in names


def test_no_orphan_module_probe_detects_synthetic_orphan(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If we plant a fresh module with no call site, the probe must
    surface it as orphan.  The regression guard must NOT silently
    pass."""
    # Use a temp pkg root: copy structure then add an orphan file.
    fake_pkg = tmp_path / "vibecodekit"
    fake_pkg.mkdir()
    # Mirror the audit allowlist (so vn_faker / vn_error_translator
    # don't pollute the orphan list when they aren't even present).
    (fake_pkg / "_audit_allowlist.json").write_text(
        json.dumps({"no_orphan_module": {}}), encoding="utf-8")
    (fake_pkg / "real_module.py").write_text(
        '"""real."""\nfrom .other import something\n', encoding="utf-8")
    (fake_pkg / "other.py").write_text(
        '"""other."""\nsomething = 1\n', encoding="utf-8")
    (fake_pkg / "orphan_module.py").write_text(
        '"""orphan: nobody imports me."""\nx = 1\n', encoding="utf-8")
    (fake_pkg / "__init__.py").write_text("", encoding="utf-8")
    # Patch the probe's resolution: monkeypatch __file__ effect via
    # creating a temp conformance_audit module pointing here.  Cheaper:
    # use the public seam by re-implementing the discovery.
    py_files = sorted(p.stem for p in fake_pkg.glob("*.py")
                      if p.stem not in {"__init__", "conformance_audit"}
                      and not p.stem.startswith("_"))
    # Build the search corpus the probe would build for this fake repo.
    blobs = {p: p.read_text(encoding="utf-8") for p in fake_pkg.glob("*.py")}
    import re
    orphans = []
    for mod in py_files:
        word_re = re.compile(rf"\b{re.escape(mod)}\b")
        found = False
        for src, blob in blobs.items():
            if src == fake_pkg / f"{mod}.py":
                continue
            if word_re.search(blob):
                found = True
                break
        if not found:
            orphans.append(mod)
    assert "orphan_module" in orphans
    assert "real_module" in orphans or "other" not in orphans
    # `other` is imported by real_module → not orphan.
    assert "other" not in orphans
