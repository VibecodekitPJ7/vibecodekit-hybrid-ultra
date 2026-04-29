"""Sanity tests for the v0.15.0 master pipeline router skill.

Mirrors the structural tests in ``test_vck_skills.py`` (v0.12) and
``test_vck_skills_v014.py`` (v0.14) so the no-orphan-module probe
(#85) and the EXPECTED_COMMANDS sanity-test convention from
CONTRIBUTING.md are upheld for the new ``/vck-pipeline`` command
introduced in PR-C.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / "update-package" / ".claude" / "commands"

V015_COMMANDS = (
    "vck-pipeline",
)


@pytest.mark.parametrize("name", V015_COMMANDS)
def test_command_markdown_ships(name: str) -> None:
    p = COMMANDS_DIR / f"{name}.md"
    assert p.is_file(), f"missing {p}"
    body = p.read_text(encoding="utf-8")
    assert body.startswith("---\n"), f"{name} missing frontmatter"
    assert f"name: {name}" in body
    assert "inspired-by:" in body


def test_manifest_lists_all_v015_commands() -> None:
    manifest = json.loads(
        (REPO_ROOT / "manifest.llm.json").read_text(encoding="utf-8"))
    names = {c["name"] for c in manifest["commands"]}
    triggers = set(manifest["skill_frontmatter"]["triggers"])
    for n in V015_COMMANDS:
        assert n in names, f"manifest.llm.json missing command {n}"
        assert f"/{n}" in triggers, f"SKILL triggers missing /{n}"


def test_skill_md_lists_all_v015_triggers() -> None:
    body = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    for n in V015_COMMANDS:
        assert f"/{n}" in body, f"SKILL.md missing /{n}"


def test_intent_router_routes_all_v015_intents() -> None:
    from vibecodekit import intent_router
    want = {
        "VCK_PIPELINE": "/vck-pipeline",
    }
    for intent, slash in want.items():
        assert intent_router._INTENT_TO_SLASH[intent] == slash


def test_subagent_runtime_binds_all_v015_commands() -> None:
    """Mirrors CONTRIBUTING.md "Adding a new /vck-* skill" Step 5:
    every VCK command must have an explicit entry in
    ``DEFAULT_COMMAND_AGENT`` so callers that don't pass
    ``commands_dir`` to ``spawn_for_command`` don't get a
    ``LookupError``."""
    from vibecodekit import subagent_runtime
    binds = subagent_runtime.list_command_agent_bindings()
    for n in V015_COMMANDS:
        assert n in binds, f"no agent bound to {n}"
        role = binds[n]
        assert role in subagent_runtime.PROFILES, (
            f"{n} -> unknown role {role}"
        )
