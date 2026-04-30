"""Smoke test cho 5 example mới trong PR7 (allowlist real consumers).

5 module trong ``scripts/vibecodekit/_audit_allowlist.json`` (vn_faker,
vn_error_translator, quality_gate, tool_use_parser, worktree_executor)
trước v0.16.2 chỉ có justification "consumed only by tests + downstream
demos" mà KHÔNG có consumer thật trong repo — dẫn tới audit P2 #6
phát hiện 5 module "soft-dead".  PR7 thêm 5 example độc lập trong
``examples/`` để mỗi module có 1 call site real, sau đó remove khỏi
allowlist (probe #85 vẫn xanh nhờ corpus mở rộng tới ``examples/``).

Test này chạy từng example dưới dạng subprocess, expect exit-code 0
+ output kết thúc bằng "OK" (convention chung của thư mục
``examples/``).  Nếu 1 example fail → CI sẽ report file nào fail.

Mỗi example tự stdlib-only (không cần network / pytest / yaml), nên
chạy được trong mọi env.  Timeout 30s/example để bảo hiểm với
worktree_executor (cần git subprocess) — các example còn lại typically
dưới 1s.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

# Liên kết example -> module nó tiêu thụ (để failure message trỏ thẳng
# tới module nếu example crash, giúp triage nhanh).
EXAMPLES = [
    ("04_vn_faker.py", "vn_faker"),
    ("05_vn_error_translator.py", "vn_error_translator"),
    ("06_quality_gate.py", "quality_gate"),
    ("07_tool_use_parser.py", "tool_use_parser"),
    ("08_worktree_executor.py", "worktree_executor"),
]


@pytest.mark.parametrize(("filename", "module"), EXAMPLES)
def test_example_runs_and_prints_ok(filename: str, module: str) -> None:
    path = EXAMPLES_DIR / filename
    assert path.is_file(), f"{filename} not found in examples/"

    env = {
        "PYTHONPATH": str(REPO_ROOT / "scripts"),
        "PATH": _safe_path(),
        "HOME": _safe_home(),
    }
    completed = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=30.0,
        env=env,
        cwd=str(REPO_ROOT),
    )

    assert completed.returncode == 0, (
        f"{filename} (consumes {module!r}) exited "
        f"{completed.returncode}\nSTDOUT:\n{completed.stdout}\n"
        f"STDERR:\n{completed.stderr}"
    )
    last_line = (completed.stdout.strip().splitlines() or [""])[-1]
    assert last_line.strip() == "OK", (
        f"{filename} did not end with 'OK' (got {last_line!r}); "
        f"convention broken — every example phải kết thúc print('OK')."
    )


def _safe_path() -> str:
    """Subset PATH cho subprocess (cần git cho 08, python cho tất cả)."""
    import os

    return os.environ.get("PATH", "/usr/bin:/bin")


def _safe_home() -> str:
    import os

    return os.environ.get("HOME", "/tmp")
