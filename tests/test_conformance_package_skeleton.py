"""Cycle 14 PRs β-1..β-6 — back-compat + structural tests for the conformance package.

The 2 246-line ``conformance_audit.py`` was broken into a package
``vibecodekit.conformance`` over PRs β-1..β-6.  This test pins the
back-compat contract that survived every step of that refactor.

Contract checks:

  1. ``vibecodekit.conformance_audit.audit`` is importable and is the
     same callable as ``vibecodekit.conformance._runner.audit``.
  2. ``vibecodekit.conformance_audit._main`` is importable and is the
     same callable as ``vibecodekit.conformance._runner.main``.
  3. ``vibecodekit.conformance_audit._find_slash_command`` is importable
     and is the same callable as
     ``vibecodekit.conformance._helpers.find_slash_command``.
  4. ``vibecodekit.conformance_audit.PROBES`` is non-empty, sorted by
     probe-id, and every entry is a ``(str, callable)`` tuple with a
     unique id.
  5. After PR β-6, ``vibecodekit.conformance.collect_registered()``
     returns the same 92 entries as ``conformance_audit.PROBES``
     (registry is the source of truth; ``PROBES`` is its sorted view).
  6. ``vibecodekit.conformance.probe`` decorator round-trip works:
     decorating a function appends to the registry; calling
     ``collect_registered()`` after returns the new entry.  The
     surrounding production registry is preserved across the test.
  7. The runner is *probe-source agnostic* — calling
     ``audit(probes=[...custom...])`` honours the explicit list and
     does NOT fall through to the manual ``PROBES``.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List, Tuple


_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def _ok_probe(_tmp: Path) -> Tuple[bool, str]:
    return True, "ok-probe"


def _bad_probe(_tmp: Path) -> Tuple[bool, str]:
    return False, "bad-probe"


def test_audit_function_is_reexported_from_package() -> None:
    from vibecodekit import conformance_audit
    from vibecodekit.conformance import _runner

    assert conformance_audit.audit is _runner.audit


def test_main_function_is_reexported_from_package() -> None:
    from vibecodekit import conformance_audit
    from vibecodekit.conformance import _runner

    assert conformance_audit._main is _runner.main


def test_find_slash_command_is_reexported_from_package() -> None:
    from vibecodekit import conformance_audit
    from vibecodekit.conformance import _helpers

    assert conformance_audit._find_slash_command is _helpers.find_slash_command


def test_probes_list_well_formed() -> None:
    from vibecodekit.conformance_audit import PROBES

    assert isinstance(PROBES, list)
    assert len(PROBES) >= 92, f"PROBES shrank: {len(PROBES)} entries"
    seen_ids: set[str] = set()
    for entry in PROBES:
        assert isinstance(entry, tuple) and len(entry) == 2
        probe_id, fn = entry
        assert isinstance(probe_id, str) and probe_id
        assert probe_id not in seen_ids, f"duplicate probe id: {probe_id}"
        seen_ids.add(probe_id)
        assert callable(fn)
    # β-6: ``PROBES`` must be sorted by probe-id so ``"01_…"`` is first
    # and ``"92_…"`` is last (matches v0.22.x output ordering).
    ids = [pid for pid, _fn in PROBES]
    assert ids == sorted(ids), "PROBES is not sorted by probe-id"


def test_probes_list_matches_registry_after_beta_6() -> None:
    """After β-6, ``PROBES`` is a sorted snapshot of the registry —
    same 92 entries, just in canonical id order rather than registration
    order."""
    from vibecodekit.conformance import collect_registered
    from vibecodekit.conformance_audit import PROBES

    registry = collect_registered()
    assert len(registry) == len(PROBES)
    assert sorted(registry, key=lambda r: r[0]) == PROBES


def test_probe_decorator_round_trip() -> None:
    """Decorating a function appends to the registry without disturbing
    the 92 production probes registered at module-import time."""
    from vibecodekit.conformance import _registry, collect_registered, probe

    snapshot = list(_registry._REGISTRY)
    try:
        @probe("test_dummy_probe", group="test", since="v0.23.0")
        def fn(_tmp: Path) -> Tuple[bool, str]:
            return True, "ok"

        after = collect_registered()
        # Production probes preserved + dummy appended at the end.
        assert after[-1] == ("test_dummy_probe", fn)
        assert after[:-1] == snapshot
    finally:
        _registry._REGISTRY[:] = snapshot


def test_probe_decorator_rejects_duplicate_id() -> None:
    """Re-registering an existing probe-id raises ``ValueError`` so two
    probes can never accidentally share a row in the audit output."""
    from vibecodekit.conformance import _registry, probe

    snapshot = list(_registry._REGISTRY)
    try:
        @probe("dup_id_skeleton_test")
        def first(_tmp: Path) -> Tuple[bool, str]:
            return True, "first"

        import pytest
        with pytest.raises(
            ValueError, match="probe id collision: 'dup_id_skeleton_test'",
        ):
            @probe("dup_id_skeleton_test")
            def second(_tmp: Path) -> Tuple[bool, str]:
                return True, "second"
    finally:
        _registry._REGISTRY[:] = snapshot


def test_runner_honours_explicit_probes_argument() -> None:
    """Pass an explicit minimal probe list and assert the runner uses
    *only* that list — does NOT fall through to the manual PROBES."""
    from vibecodekit.conformance import audit

    custom: List[Tuple[str, Callable[[Path], Tuple[bool, str]]]] = [
        ("ok_probe", _ok_probe),
        ("bad_probe", _bad_probe),
    ]
    out = audit(threshold=0.5, probes=custom)
    assert out["total"] == 2
    assert out["passed"] == 1
    assert out["parity"] == 0.5
    assert {row["pattern"] for row in out["probes"]} == {"ok_probe", "bad_probe"}
