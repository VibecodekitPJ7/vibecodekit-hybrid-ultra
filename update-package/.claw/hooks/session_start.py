#!/usr/bin/env python3
"""session_start hook — emits a banner so the operator knows the overlay
is live, opportunistically refreshes auto-maintained CLAUDE.md
sections (rate-limited so this never spams disk I/O), and injects up
to 10 most-recent learnings so prior project context is visible to
the host LLM at session start (v0.15.0-alpha; opt-out via
``VIBECODE_LEARNINGS_INJECT=0``).
"""
import json
import os
import sys

banner = "VibecodeKit v0.11.2 engaged"
auto_writeback = {"ran": False, "reason": "skipped"}
learnings_inject = {"injected": 0, "reason": "skipped", "items": []}

# Resolve the vibecodekit Python package across known install layouts.
# Order: explicit env override → ai-rules overlay → skill bundle dev → none.
repo = os.environ.get("CLAW_PROJECT_ROOT") or os.getcwd()
here = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    os.environ.get("VIBECODEKIT_SKILL_PATH"),
    os.path.join(repo, "ai-rules", "vibecodekit", "scripts"),
    os.path.join(here, "..", "..", "..", "skill",
                  "vibecodekit-hybrid-ultra", "scripts"),
    os.path.join(here, "..", "..", "ai-rules",
                  "vibecodekit", "scripts"),
]
for _cand in _candidates:
    if _cand and os.path.isdir(os.path.join(_cand, "vibecodekit")):
        sys.path.insert(0, os.path.abspath(_cand))
        break

# Best-effort: never let writeback errors block session start.
try:
    from vibecodekit.auto_writeback import try_refresh  # type: ignore
    decision = try_refresh(repo)
    auto_writeback = {
        "ran": decision.ran,
        "reason": decision.reason,
        "elapsed_s": round(decision.elapsed_s, 3),
        "sections_updated": list(decision.sections_updated),
    }
except Exception as exc:  # noqa: BLE001
    auto_writeback = {"ran": False, "reason": f"hook_error: {type(exc).__name__}"}

# v0.15.0-alpha (PR-B / T3) — auto-inject most-recent learnings into
# the session-start payload so the host LLM can surface prior project
# context.  Opt-out with ``VIBECODE_LEARNINGS_INJECT=0``.  Limit
# overridable via ``VIBECODE_LEARNINGS_INJECT_LIMIT`` (default 10).
# Failures are silent — never break session start.
if os.environ.get("VIBECODE_LEARNINGS_INJECT", "1") != "0":
    try:
        from vibecodekit.learnings import load_recent  # type: ignore
        _limit_raw = os.environ.get("VIBECODE_LEARNINGS_INJECT_LIMIT", "10")
        try:
            _limit = max(0, int(_limit_raw))
        except ValueError:
            _limit = 10
        _recent = load_recent(limit=_limit, root=repo)
        learnings_inject = {
            "injected": len(_recent),
            "reason": "ok",
            "items": [
                {
                    "text": l.text,
                    "scope": l.scope,
                    "tags": list(l.tags),
                    "captured_ts": l.captured_ts,
                }
                for l in _recent
            ],
        }
    except Exception as exc:  # noqa: BLE001
        learnings_inject = {
            "injected": 0,
            "reason": f"hook_error: {type(exc).__name__}",
            "items": [],
        }
else:
    learnings_inject = {"injected": 0, "reason": "opt_out", "items": []}

sys.stdout.write(json.dumps({
    "decision": "allow",
    "banner": banner,
    "auto_writeback": auto_writeback,
    "learnings_inject": learnings_inject,
}))
