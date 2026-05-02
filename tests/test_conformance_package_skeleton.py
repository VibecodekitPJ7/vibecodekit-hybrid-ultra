"""Cycle 14 PR β-1 — back-compat + structural tests for the new conformance package.

The 2 246-line ``conformance_audit.py`` is being broken into a package
``vibecodekit.conformance`` over PRs β-1..β-6.  This test pins the
back-compat contract that PRs β-2..β-5 (probe relocations) must
preserve before β-6 finally drops the manual ``PROBES`` list.

Contract checks (cycle 14 β-1):

  1. ``vibecodekit.conformance_audit.audit`` is importable and is the
     same callable as ``vibecodekit.conformance._runner.audit``.
  2. ``vibecodekit.conformance_audit._main`` is importable and is the
     same callable as ``vibecodekit.conformance._runner.main``.
  3. ``vibecodekit.conformance_audit._find_slash_command`` is importable
     and is the same callable as
     ``vibecodekit.conformance._helpers.find_slash_command``.
  4. ``vibecodekit.conformance_audit.PROBES`` is non-empty and every
     entry is a ``(str, callable)`` tuple.
  5. ``vibecodekit.conformance.collect_registered()`` is empty in β-1
     (the registry only populates in β-6).
  6. ``vibecodekit.conformance.probe`` decorator round-trip works:
     decorating a function appends to the registry; calling
     ``collect_registered()`` after returns the new entry.
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


def test_registry_is_empty_in_beta_1() -> None:
    """β-6 will populate this; until then it must stay empty so the
    runner's default behaviour (use ``PROBES``) remains correct."""
    from vibecodekit.conformance import collect_registered

    assert collect_registered() == []


def test_probe_decorator_round_trip() -> None:
    from vibecodekit.conformance import _registry, collect_registered, probe

    _registry._reset_for_tests()
    try:
        @probe("test_dummy_probe", group="test", since="v0.23.0")
        def fn(_tmp: Path) -> Tuple[bool, str]:
            return True, "ok"

        assert collect_registered() == [("test_dummy_probe", fn)]
    finally:
        _registry._reset_for_tests()


def test_probe_decorator_rejects_duplicate_id() -> None:
    from vibecodekit.conformance import _registry, probe

    _registry._reset_for_tests()
    try:
        @probe("dup_id")
        def first(_tmp: Path) -> Tuple[bool, str]:
            return True, "first"

        import pytest
        with pytest.raises(ValueError, match="probe id collision: 'dup_id'"):
            @probe("dup_id")
            def second(_tmp: Path) -> Tuple[bool, str]:
                return True, "second"
    finally:
        _registry._reset_for_tests()


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
