"""CI guard: 5 core module phải pass ``mypy --strict``.

Cycle 6 PR2: bật strict gate cho ``permission_engine``, ``scaffold_engine``,
``verb_router``, ``denial_store``, ``_audit_log``.  Các module còn lại
(``tool_executor``, ``team_mode``, ``task_runtime``, ``subagent_runtime``)
relax strict trong ``mypy.ini`` — sẽ siết cycle sau.

Test này chạy mypy as subprocess.  Skip nếu mypy không cài (CI luôn cài,
dev local có thể không).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")

CORE_MODULES = [
    "scripts/vibecodekit/permission_engine.py",
    "scripts/vibecodekit/scaffold_engine.py",
    "scripts/vibecodekit/verb_router.py",
    "scripts/vibecodekit/denial_store.py",
    "scripts/vibecodekit/_audit_log.py",
]


def _mypy_available() -> bool:
    return importlib.util.find_spec("mypy") is not None


@pytest.mark.skipif(
    not _mypy_available(),
    reason="mypy không cài — skip strict gate test (CI luôn cài).",
)
def test_mypy_strict_passes_on_core_modules() -> None:
    """``mypy --strict`` phải xanh cho 5 core module.

    Cache vào ``.mypy_cache`` (gitignored) để re-run local nhanh hơn.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = SCRIPTS_DIR
    cmd = [sys.executable, "-m", "mypy", "--strict", *CORE_MODULES]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"mypy --strict failed (exit {proc.returncode}) trên 5 core module.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
