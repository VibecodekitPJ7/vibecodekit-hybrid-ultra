"""Shared helpers used by multiple conformance probes.

Extracted from ``conformance_audit.py`` in cycle 14 PR β-1.  The public
function names are kept stable so that external callers (and the
back-compat shim in ``conformance_audit``) continue to work.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional


def find_slash_command(here: Path, name: str) -> Optional[Path]:
    """Locate a ``.claude/commands/<name>`` shipped alongside the skill bundle.

    v0.15.3 fix (Bug #1 from the v0.15.0 deep-dive audit): probes #40 and
    #44 used to call this with ``here = repo_root`` and the loop walked
    ``here.parents[level]`` which never inspects ``here`` itself.  Since
    the canonical source-tree layout has ``update-package/`` as a *child*
    of the repo root (not a sibling of any ancestor), the lookup
    silently returned ``None`` whenever ``VIBECODE_UPDATE_PACKAGE`` was
    not exported — which is the typical local-dev case.  The function
    now walks ``here`` first, then its parents, so both layouts work.

    Resolution order:

      1) honour ``$VIBECODE_UPDATE_PACKAGE`` if set;
      2) walk ``here`` itself, then up to 4 levels of parents, checking
         ``base/.claude/commands/<name>`` and any *child* of ``base``
         whose name matches a known update-package label (claw-code-pack,
         update-package, kit*, vibecodekit-update*);
      3) fall back to ``cwd``.
    """
    env = os.environ.get("VIBECODE_UPDATE_PACKAGE")
    if env:
        cand = Path(env) / ".claude" / "commands" / name
        if cand.exists():
            return cand
    KNOWN_PACKAGE_DIRS = ("claw-code-pack", "update-package")
    KNOWN_PREFIXES = ("kit", "vibecodekit-update")
    bases: List[Path] = [here]
    for level in range(0, 5):
        try:
            bases.append(here.parents[level])
        except IndexError:
            break
    for base in bases:
        cand = base / ".claude" / "commands" / name
        if cand.exists():
            return cand
        if base.is_dir():
            for sib in base.iterdir():
                if not sib.is_dir():
                    continue
                if (sib.name in KNOWN_PACKAGE_DIRS
                        or any(sib.name.startswith(p) for p in KNOWN_PREFIXES)):
                    cand = sib / ".claude" / "commands" / name
                    if cand.exists():
                        return cand
    cand = Path.cwd() / ".claude" / "commands" / name
    if cand.exists():
        return cand
    return None
