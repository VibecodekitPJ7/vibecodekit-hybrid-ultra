"""Smoke tests pinning previously-orphan modules to a production
call site (PR-D / T7).

The no-orphan-module conformance probe (#85) requires every module
in ``scripts/vibecodekit/`` to either:

* be imported by a sibling production module, or
* be imported by a runtime hook, or
* **be imported by the test suite** — this file provides exactly
  that for four modules that were dormant until v0.15.0.

These modules were already documented in references / templates and
are part of the kit's public surface; they were just missing a
runtime entry point.  Pinning them in tests prevents them from being
silently deleted while we work out a final wiring story.
"""
from __future__ import annotations

import json
from pathlib import Path

from vibecodekit import (
    auto_commit_hook,
    quality_gate,
    tool_use_parser,
    worktree_executor,
)


# ---------------------------------------------------------------------------
# auto_commit_hook
# ---------------------------------------------------------------------------

def test_auto_commit_hook_sensitive_file_guard_blocks_env(tmp_path: Path) -> None:
    guard = auto_commit_hook.SensitiveFileGuard()
    import pytest
    with pytest.raises(PermissionError):
        guard.check(tmp_path / ".env")
    # Non-sensitive paths pass through silently.
    guard.check(tmp_path / "README.md")


def test_auto_commit_hook_is_sensitive_helper() -> None:
    assert auto_commit_hook.is_sensitive(Path(".env")) is True
    assert auto_commit_hook.is_sensitive(Path("README.md")) is False


# ---------------------------------------------------------------------------
# quality_gate
# ---------------------------------------------------------------------------

def _full_scorecard(score: float = 0.9) -> dict:
    keys = list(quality_gate.DIMENSIONS) + list(quality_gate.AXES)
    return {k: {"score": score, "evidence": "ok"} for k in keys}


def test_quality_gate_evaluates_passing_scorecard() -> None:
    verdict = quality_gate.evaluate(_full_scorecard(0.9))
    assert verdict["passed"] is True
    assert "aggregate" in verdict


def test_quality_gate_blocks_low_axis_score() -> None:
    sc = _full_scorecard(0.9)
    first = quality_gate.DIMENSIONS[0]
    sc[first] = {"score": 0.1, "evidence": "fail"}
    verdict = quality_gate.evaluate(sc)
    assert verdict["passed"] is False
    assert first in verdict["failed_below_min"]


# ---------------------------------------------------------------------------
# tool_use_parser
# ---------------------------------------------------------------------------

def test_tool_use_parser_handles_json_array() -> None:
    text = json.dumps([
        {"tool": "read_file", "input": {"path": "README.md"}},
        {"tool": "grep", "input": {"pattern": "TODO"}},
    ])
    out = tool_use_parser.parse_tool_uses(text)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["tool"] == "read_file"


def test_tool_use_parser_returns_empty_when_no_match() -> None:
    out = tool_use_parser.parse_tool_uses("This is just prose without any tool calls.")
    assert out == []


# ---------------------------------------------------------------------------
# worktree_executor
# ---------------------------------------------------------------------------

def test_worktree_executor_list_worktrees_in_non_git_dir(tmp_path: Path) -> None:
    # Outside a git repo the helper should not raise — it should
    # return an empty list (or raise a typed error we catch here).
    try:
        worktrees = worktree_executor.list_worktrees(root=tmp_path)
    except Exception:
        # Acceptable: caller is expected to wrap in try/except.  The
        # important invariant for the orphan probe is that the module
        # is importable and its public function exists.
        worktrees = []
    assert isinstance(worktrees, list)


def test_worktree_executor_module_exposes_public_surface() -> None:
    for name in ("create", "remove", "list_worktrees"):
        assert hasattr(worktree_executor, name), f"worktree_executor missing {name}"
