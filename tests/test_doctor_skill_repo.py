"""Regression test for v0.16.1 audit recheck Finding E.

When ``vibe doctor`` is invoked from inside the skill bundle's source
tree, the advisory files (``CLAUDE.md``, ``.claude/commands``, etc.)
are *expected* to live under ``update-package/`` rather than the
project root.  Doctor must recognise this layout via
``_is_skill_repo()`` and report all advisories as present, with a new
``skill_repo: True`` flag in the output envelope.

Source: ``docs/audits/v0.15.4-recheck.md`` recheck (Finding E).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from vibecodekit import doctor  # noqa: E402


def test_doctor_recognises_skill_repo_root() -> None:
    """Doctor invoked at the skill-repo root sees update-package/ overlay
    and reports zero advisory_missing."""
    out = doctor.check(REPO)
    assert out["skill_repo"] is True, out
    assert out["advisory_missing"] == [], (
        "skill repo root must have all advisories satisfied via "
        f"update-package/ fallback (got missing: {out['advisory_missing']})"
    )
    # All 6 advisories must be reported as present.
    assert sorted(out["advisory_present"]) == sorted([
        ".claw.json",
        "CLAUDE.md",
        ".claude/commands",
        ".claude/agents",
        "ai-rules/vibecodekit",
        ".claw/hooks",
    ]), out


def test_doctor_skill_repo_flag_false_for_normal_project(tmp_path: Path) -> None:
    """A directory without update-package/ is NOT a skill repo."""
    (tmp_path / "some_file").write_text("noop")
    out = doctor.check(tmp_path)
    assert out["skill_repo"] is False, out
    # Nothing was satisfied via the skill-repo fallback, so the usual
    # advisory_missing list should still be populated.
    assert "CLAUDE.md" in out["advisory_missing"], out
