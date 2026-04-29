"""Regression tests for v0.15.1 audit-tool + cleanup PR.

Pins the four v0.15.1 fixes from the v0.15.0 deep-dive audit:

    Bug #1 — ``_find_slash_command`` now finds ``update-package/`` when
             it is a child of ``here`` (typical local-dev layout).
    Bug #4 — ``learnings.recent_for_prompt`` returns a markdown
             addendum; ``load_recent`` accepts a ``scopes`` filter.
    Bug #5 — ``docs/AUDIT-v0.14.0.md`` references the v0.15 closure of
             D1–D4 dormant findings.
    Bug #6 — ``vibe team`` / ``vibe learn`` / ``vibe pipeline`` CLI
             pass-throughs work end-to-end.

The tests live in their own file so the existing ``test_pipeline_v015_*``
modules stay scoped to PR-A/B/C/D semantics.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "scripts"
sys.path.insert(0, str(_PKG))

from vibecodekit import learnings  # noqa: E402
from vibecodekit.conformance_audit import _find_slash_command  # noqa: E402


class FindSlashCommandWalksHereItself(unittest.TestCase):
    """Bug #1 — repo-root layout (update-package/ is a child of `here`)."""

    def test_finds_vibe_refine_md_without_env_var(self) -> None:
        env_save = os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)
        try:
            here = _REPO
            found = _find_slash_command(here, "vibe-refine.md")
            self.assertIsNotNone(found,
                "Expected to find update-package/.claude/commands/vibe-refine.md "
                "as a *child* of repo root without VIBECODE_UPDATE_PACKAGE set.")
            self.assertTrue(str(found).endswith(
                "update-package/.claude/commands/vibe-refine.md"))
        finally:
            if env_save is not None:
                os.environ["VIBECODE_UPDATE_PACKAGE"] = env_save

    def test_finds_vibe_module_md_without_env_var(self) -> None:
        env_save = os.environ.pop("VIBECODE_UPDATE_PACKAGE", None)
        try:
            here = _REPO
            found = _find_slash_command(here, "vibe-module.md")
            self.assertIsNotNone(found)
            self.assertTrue(str(found).endswith(
                "update-package/.claude/commands/vibe-module.md"))
        finally:
            if env_save is not None:
                os.environ["VIBECODE_UPDATE_PACKAGE"] = env_save

    def test_audit_passes_threshold_1_without_env_var(self) -> None:
        """Run the full audit (threshold 1.0) without the CI env var.

        This is the canonical regression for Bug #1 — before the fix
        this command exited 1 because probes #40 + #44 reported FAIL.
        """
        env = {**os.environ}
        env.pop("VIBECODE_UPDATE_PACKAGE", None)
        env["PYTHONPATH"] = str(_PKG)
        proc = subprocess.run(
            [sys.executable, "-m", "vibecodekit.conformance_audit",
             "--threshold", "1.0"],
            cwd=str(_REPO), env=env, capture_output=True, text=True,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"audit failed without VIBECODE_UPDATE_PACKAGE:\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}")
        self.assertIn("100.00%", proc.stdout)


class LearningsRecentForPrompt(unittest.TestCase):
    """Bug #4 — markdown addendum + scope filter on load_recent."""

    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed(self) -> None:
        learnings.project_store(self.root).append(
            learnings.Learning(text="proj 1", scope="project", tags=("api",)))
        learnings.team_store(self.root).append(
            learnings.Learning(text="team 1", scope="team"))
        learnings.user_store(self.home).append(
            learnings.Learning(text="user 1", scope="user"))

    def test_recent_for_prompt_returns_markdown_addendum(self) -> None:
        self._seed()
        md = learnings.recent_for_prompt(limit=10, root=self.root, home=self.home)
        self.assertIn("## Prior learnings", md)
        # All three scopes present.
        self.assertIn("[project]", md)
        self.assertIn("[team]", md)
        self.assertIn("[user]", md)
        # Tags rendered inline.
        self.assertIn("`#api`", md)

    def test_recent_for_prompt_empty_returns_empty_string(self) -> None:
        md = learnings.recent_for_prompt(limit=10, root=self.root, home=self.home)
        self.assertEqual(md, "")

    def test_load_recent_scope_filter(self) -> None:
        self._seed()
        only_project = learnings.load_recent(
            limit=10, root=self.root, home=self.home, scopes=("project",))
        self.assertEqual({l.scope for l in only_project}, {"project"})

        project_user = learnings.load_recent(
            limit=10, root=self.root, home=self.home,
            scopes=("project", "user"))
        self.assertEqual({l.scope for l in project_user}, {"project", "user"})

    def test_load_recent_unknown_scope_dropped(self) -> None:
        self._seed()
        result = learnings.load_recent(
            limit=10, root=self.root, home=self.home,
            scopes=("project", "bogus"))
        self.assertEqual({l.scope for l in result}, {"project"})

    def test_recent_for_prompt_respects_scopes(self) -> None:
        self._seed()
        md = learnings.recent_for_prompt(
            limit=10, scopes=("project",), root=self.root, home=self.home)
        self.assertIn("[project]", md)
        self.assertNotIn("[team]", md)
        self.assertNotIn("[user]", md)


class AuditV014DocReferencesV015Closure(unittest.TestCase):
    """Bug #5 — the v0.14.0 audit doc cross-references the v0.15 closure."""

    def test_doc_mentions_v015_closure(self) -> None:
        body = (_REPO / "docs" / "AUDIT-v0.14.0.md").read_text(encoding="utf-8")
        self.assertIn("v0.15.0", body)
        self.assertIn("INTEGRATION-PLAN-v0.15.md", body)
        # D1-D4 dormant-code findings explicitly named.
        self.assertIn("D1", body)
        self.assertIn("dormant", body.lower())


class CliPassthroughs(unittest.TestCase):
    """Bug #6 — ``vibe team`` / ``vibe learn`` / ``vibe pipeline`` work."""

    def _vibe(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONPATH": str(_PKG)}
        return subprocess.run(
            [sys.executable, "-m", "vibecodekit.cli", *args],
            cwd=str(_REPO), env=env, capture_output=True, text=True,
        )

    def test_vibe_help_lists_new_subcommands(self) -> None:
        proc = self._vibe("--help")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("team", proc.stdout)
        self.assertIn("learn", proc.stdout)
        self.assertIn("pipeline", proc.stdout)

    def test_vibe_pipeline_list_emits_three_buckets(self) -> None:
        proc = self._vibe("pipeline", "list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        codes = {p["code"] for p in data}
        self.assertEqual(codes, {"A", "B", "C"})

    def test_vibe_team_check_no_op_outside_team_repo(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            env = {**os.environ, "PYTHONPATH": str(_PKG)}
            proc = subprocess.run(
                [sys.executable, "-m", "vibecodekit.cli", "team", "check"],
                cwd=td, env=env, capture_output=True, text=True,
            )
            # No team.json in tmp → exit 0 (no-op).
            self.assertEqual(proc.returncode, 0,
                             f"stdout={proc.stdout} stderr={proc.stderr}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
