"""Audit runner — orchestrates probes, collects results, prints/JSON output.

Extracted from ``conformance_audit.py`` in cycle 14 PR β-1.  This module
is the engine that:

  1) Iterates over a list of probes (manual or registry-collected).
  2) Hands each probe a fresh ``tmp/<probe-id>`` working directory.
  3) Records ``pass / fail`` plus the probe's free-text detail string.
  4) Computes parity = passed / total and compares to threshold.
  5) Returns a JSON-serialisable report and (in CLI mode) prints it.

The runner is **agnostic** to where probes come from.  Callers may pass
their own ``probes`` list (used by the back-compat shim in
``conformance_audit.py``) or omit it, in which case the runner pulls
from ``vibecodekit.conformance_audit.PROBES`` for full back-compat.
Once PR β-6 lands, callers can also pass ``probes=collect_registered()``
to use the decorator-based registry.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

ProbeFn = Callable[[Path], Tuple[bool, str]]
ProbeEntry = Tuple[str, ProbeFn]


def audit(threshold: float = 0.85, *,
          probes: Optional[Sequence[ProbeEntry]] = None) -> Dict[str, Any]:
    """Run all probes against fresh temp dirs, return parity report.

    Parameters
    ----------
    threshold:
        Minimum parity (passed / total) for the audit to be considered
        "met".  Default ``0.85``.
    probes:
        Optional list of ``(id, fn)`` pairs.  If ``None`` (default)
        the runner pulls ``PROBES`` from ``vibecodekit.conformance_audit``
        — preserving v0.22.x behaviour exactly.

    Returns
    -------
    Dict with keys ``threshold``, ``passed``, ``total``, ``parity``,
    ``met``, and ``probes`` (a list of per-probe rows).
    """
    if probes is None:
        # PR β-6: source of truth is the ``@probe`` decorator-based
        # registry, but we read it via ``vibecodekit.conformance_audit
        # .PROBES`` so test code that monkey-patches that attribute
        # (e.g. ``monkeypatch.setattr(ca, "PROBES", custom)``) still
        # influences the runner.  Importing the audit shim is what
        # populates the registry as a side effect — each ``@probe``
        # decorator runs at module-load time.
        from vibecodekit.conformance_audit import PROBES as _DEFAULT_PROBES
        probes = _DEFAULT_PROBES

    rows: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as td:
        for name, probe in probes:
            sub = Path(td) / name
            sub.mkdir(parents=True, exist_ok=True)
            try:
                ok, detail = probe(sub)
                rows.append({"pattern": name, "pass": bool(ok), "detail": detail})
            except Exception as e:  # pragma: no cover - exception path
                rows.append({
                    "pattern": name,
                    "pass": False,
                    "detail": f"exception: {type(e).__name__}: {e}",
                })
    passed = sum(1 for r in rows if r["pass"])
    total = len(rows)
    parity = (passed / total) if total else 0.0
    return {
        "threshold": threshold,
        "passed": passed,
        "total": total,
        "parity": round(parity, 4),
        "met": parity >= threshold,
        "probes": rows,
    }


def main() -> None:
    """CLI entry — prints parity report and exits 0 iff met."""
    ap = argparse.ArgumentParser(
        description="Run behaviour-based conformance audit.",
    )
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = audit(args.threshold)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(
            f"parity: {out['parity']:.2%}   "
            f"({out['passed']}/{out['total']}, "
            f"threshold {out['threshold']:.0%})"
        )
        for r in out["probes"]:
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"  [{mark}] {r['pattern']:<36} {r['detail']}")
    sys.exit(0 if out["met"] else 1)
