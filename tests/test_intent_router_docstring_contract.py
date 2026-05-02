"""Contract test: the module docstring of ``vibecodekit.intent_router``
must match the actual implementation.

Why this test exists
====================

Pre-v0.23.0 the docstring claimed a ``HashEmbeddingBackend`` cosine
similarity tie-breaker that was never implemented (a 12-version drift
discovered during the cycle 14 architectural review — see
``REVIEW-2-issues-2026-05-01.md`` §2.1).  The drift was removed in
PR α-2 (this PR).

This test prevents the drift from happening again by:

1. Asserting the docstring does NOT claim any ML / embedding /
   cosine / LLM mechanism (the impl is pure keyword scoring).
2. Asserting the docstring DOES describe the actual mechanism
   (pipeline triggers + tier-1 keyword scoring + multi-intent
   expansion + clarification fallback).
3. Asserting the doctest example reflects the real ``_INTENT_TO_SLASH``
   mapping (e.g. ``BUILD → /vibe-scaffold``, not ``/vibe-build``).
4. Asserting the source code does NOT import anything that would
   indicate a hidden ML/embedding path (``embedding``, ``cosine``,
   ``HashEmbeddingBackend``).
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

# scripts/ must be on sys.path (CI injects via PYTHONPATH; locally we
# insert here for parity with other router tests).
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vibecodekit import intent_router as ir_mod  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Docstring negative claims — must NOT mention these
# ---------------------------------------------------------------------------

# Phrases that would indicate a non-keyword classifier.  Each phrase here
# would be a docstring-vs-impl drift if it appeared as a positive claim.
_FORBIDDEN_POSITIVE_CLAIMS = (
    # The original drift — a tie-breaker that never existed.
    ("HashEmbeddingBackend", "embedding tie-breaker not implemented"),
    # General ML/embedding mechanisms that aren't in the code.
    ("sentence-transformers", "no transformer model is loaded"),
    ("openai", "router never calls an LLM"),
    ("anthropic", "router never calls an LLM"),
    ("vector store", "router has no vector store"),
)


def test_docstring_no_forbidden_positive_claims() -> None:
    """The module docstring must not advertise mechanisms that aren't in
    the source.  We allow these strings in the **note** that explicitly
    documents the historical drift, so we look for *positive* claims
    only — the negative-disclaimer paragraph is fine."""
    doc = ir_mod.__doc__ or ""
    # Strip the historical-drift note paragraph (everything between
    # ".. note::" and the next blank-line gap) so the disclaimer doesn't
    # trigger our forbidden-string check.
    doc_without_note = re.sub(
        r"\.\. note::.*?(?=\n\nPublic API::|\n\nThe router is)",
        "",
        doc,
        flags=re.DOTALL,
    )
    for phrase, reason in _FORBIDDEN_POSITIVE_CLAIMS:
        assert phrase.lower() not in doc_without_note.lower(), (
            f"docstring still mentions {phrase!r} ({reason})"
        )


# ---------------------------------------------------------------------------
# 2. Docstring positive claims — MUST mention these (the actual strategy)
# ---------------------------------------------------------------------------

_REQUIRED_DOCSTRING_TERMS = (
    "keyword",        # the actual strategy
    "Pipeline trigger",   # step 1
    "scoring",        # step 2
    "Multi-intent",   # step 3
    "Clarification",  # step 4
    "stateless",      # design property
    "diacritics",     # VN normalisation
)


def test_docstring_describes_actual_strategy() -> None:
    """The docstring must cover the four actual steps of ``classify``."""
    doc = ir_mod.__doc__ or ""
    missing = [t for t in _REQUIRED_DOCSTRING_TERMS if t.lower() not in doc.lower()]
    assert not missing, (
        f"docstring is missing required strategy terms: {missing!r}"
    )


# ---------------------------------------------------------------------------
# 3. Doctest example matches the real INTENT_TO_SLASH mapping
# ---------------------------------------------------------------------------


def test_docstring_doctest_example_matches_impl() -> None:
    """The docstring's worked example uses the prose ``"làm cho tôi shop
    online bán cà phê"``.  Run the actual classify+route on that prose
    and confirm the output matches the docstring (i.e. the example is
    not stale).
    """
    r = ir_mod.IntentRouter()
    match = r.classify("làm cho tôi shop online bán cà phê")
    intents = match.intents  # type: ignore[union-attr]
    route = r.route(match)

    # The docstring claims:
    #   intents -> ('SCAN', 'VISION', 'RRI', 'BUILD', 'VERIFY')
    #   route   -> ['/vibe-scan', '/vibe-vision', '/vibe-rri',
    #               '/vibe-scaffold', '/vibe-verify']
    assert intents == ("SCAN", "VISION", "RRI", "BUILD", "VERIFY"), (
        f"docstring intent example is stale: actual={intents!r}"
    )
    assert route == [
        "/vibe-scan",
        "/vibe-vision",
        "/vibe-rri",
        "/vibe-scaffold",
        "/vibe-verify",
    ], (
        f"docstring route example is stale: actual={route!r}"
    )


def test_build_intent_routes_to_scaffold_not_build() -> None:
    """Regression guard for a specific drift — pre-v0.23.0 the docstring
    had ``/vibe-build`` but the real mapping is ``/vibe-scaffold``."""
    assert ir_mod._INTENT_TO_SLASH["BUILD"] == "/vibe-scaffold"
    assert "/vibe-build" not in ir_mod._INTENT_TO_SLASH.values()


# ---------------------------------------------------------------------------
# 4. Source code does NOT import / use ML/embedding mechanisms
# ---------------------------------------------------------------------------


def test_source_does_not_import_ml_or_embedding() -> None:
    """If the source ever grows an ``import torch`` / embedding backend
    again, the docstring must be updated first.  This test protects
    against silent drift."""
    src = inspect.getsource(ir_mod)
    # Strip the docstring (top of file) so the historical-drift note
    # in the docstring doesn't trip the test.
    src_no_doc = re.sub(r'^""".*?"""', "", src, count=1, flags=re.DOTALL)
    forbidden_imports = (
        "import torch",
        "import sentence_transformers",
        "from sentence_transformers",
        "import openai",
        "import anthropic",
        "from openai",
        "from anthropic",
        "HashEmbeddingBackend",  # never instantiated in the router
        "cosine_similarity",
    )
    for token in forbidden_imports:
        assert token not in src_no_doc, (
            f"router source contains {token!r} but docstring does not "
            f"document an ML / embedding strategy.  Either add the "
            f"import behind a feature flag and update the docstring, "
            f"or remove the import."
        )
