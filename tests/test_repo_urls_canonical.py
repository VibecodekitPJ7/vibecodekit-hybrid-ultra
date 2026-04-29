"""CI guard: every github.com/<org>/ URL in the repo must reference an
allowed organisation.  Prevents stale fork / personal-account URLs from
leaking into releases.
"""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Orgs that are legitimate references in this codebase.
ALLOWED_ORGS = {"VibecodekitPJ3", "VagabondKingsman", "garrytan"}

# Placeholder orgs used in examples (e.g. "github.com/.../pull/42").
_PLACEHOLDER_ORGS = {"...", "OWNER", "owner", "example", "your-org"}

_ORG_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/")

# Only scan text-ish files; skip binary and vendored content.
_SCAN_SUFFIXES = {".md", ".toml", ".json", ".py", ".yml", ".yaml", ".cfg", ".txt"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}


def _scan_files():
    bad: list[str] = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in _SCAN_SUFFIXES:
            continue
        if any(skip in p.parts for skip in _SKIP_DIRS):
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for m in _ORG_RE.finditer(text):
            org = m.group(1)
            if org in _PLACEHOLDER_ORGS:
                continue
            if org not in ALLOWED_ORGS:
                rel = p.relative_to(REPO_ROOT)
                bad.append(f"{rel}: found org {org!r} in {m.group(0)!r}")
    return bad


def test_no_stale_org_in_repo():
    bad = _scan_files()
    assert not bad, (
        "Stale / non-canonical GitHub org references found:\n"
        + "\n".join(f"  - {b}" for b in bad)
    )
