#!/usr/bin/env python3
"""Example: spawn an isolated git worktree (Pattern #8) then clean up.

Run from the repo root:
    PYTHONPATH=./scripts python examples/08_worktree_executor.py

Demonstrates ``vibecodekit.worktree_executor`` create / list / remove
on a *temporary* git repo (``tempfile.mkdtemp``) so the example never
pollutes the outer checkout.  Cleanup is always run (try/finally).

Use case: parallel sub-agents need to mutate the same repo without
stepping on each other.  Each agent gets its own worktree under
``.vibecode/runtime/worktrees/<slug>-<ts>/``.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from vibecodekit.worktree_executor import create, list_worktrees, remove


def init_temp_repo() -> Path:
    """Create an empty git repo in a temp dir + 1 initial commit."""
    tmp = Path(tempfile.mkdtemp(prefix="vck-worktree-demo-"))
    subprocess.run(["git", "-C", str(tmp), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp), "config", "user.email", "demo@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp), "config", "user.name", "Demo"], check=True)
    (tmp / "README.md").write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp), "commit", "-q", "-m", "init"], check=True)
    return tmp


if __name__ == "__main__":
    repo = init_temp_repo()
    try:
        print(f"Temp repo : {repo}")

        result = create(repo, slug="agent-builder")
        assert result["returncode"] == 0, result["stderr"]
        worktree_rel = result["worktree"]
        print(f"Created   : {worktree_rel}  (branch={result['branch']})")

        listing = list_worktrees(repo)
        n_lines = len([ln for ln in listing["stdout"].splitlines() if ln.strip()])
        print(f"List      : {n_lines} worktree entries (main + 1 spawned)")
        assert n_lines >= 2

        cleanup = remove(repo, worktree_rel)
        assert cleanup["returncode"] == 0, cleanup["stderr"]
        print(f"Removed   : {worktree_rel}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    print("\nOK")
