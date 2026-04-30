#!/usr/bin/env python3
"""Example: translate 3 common Python errors to Vietnamese with fix hints.

Run from the repo root:
    PYTHONPATH=./scripts python examples/05_vn_error_translator.py

Demonstrates ``vibecodekit.vn_error_translator.VnErrorTranslator``:
pattern-based stderr → tiếng Việt explanation + fix suggestion,
ranked by ``confidence × specificity`` (longer regex wins ties).
"""
from vibecodekit.vn_error_translator import VnErrorTranslator


SAMPLES = [
    # (label, raw stderr/traceback chunk)
    (
        "Missing dependency",
        "Traceback (most recent call last):\n"
        "  File \"app.py\", line 1, in <module>\n"
        "    import requests\n"
        "ModuleNotFoundError: No module named 'requests'",
    ),
    (
        "Wrong file path",
        "Traceback (most recent call last):\n"
        "  File \"loader.py\", line 5, in <module>\n"
        "    open('/etc/missing.conf')\n"
        "FileNotFoundError: [Errno 2] No such file or directory: '/etc/missing.conf'",
    ),
    (
        "Indentation slip",
        "  File \"app.py\", line 12\n"
        "    return x\n"
        "    ^\n"
        "IndentationError: unexpected indent",
    ),
]


if __name__ == "__main__":
    tr = VnErrorTranslator()
    print(f"Loaded {len(tr)} pattern entries (built-in + YAML if any)")
    print()

    for label, stderr in SAMPLES:
        best = tr.best(stderr)
        print(f"--- {label} ---")
        if best is None:
            print("  (không khớp pattern nào)")
            continue
        print(f"  Tóm tắt VN : {best.summary_vn}")
        print(f"  Gợi ý sửa  : {best.fix_suggestion_vn}")
        print(f"  Độ tin cậy : {best.confidence:.2f}")
        print(f"  Khớp với   : {best.matched_substring!r}")
        print()

    print("OK")
