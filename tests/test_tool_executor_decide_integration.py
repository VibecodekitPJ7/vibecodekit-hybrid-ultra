"""Integration test: tool_executor + permission_engine + audit log.

Round-trip: gọi ``execute_blocks`` với ``rm -rf /`` qua ``run_command``,
verify (a) executor abort không invoke subprocess, (b) audit log entry
được ghi qua ``_audit_log`` khi deny.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit import tool_executor as te  # noqa: E402


def test_run_command_rm_rf_root_denied_and_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force audit log dir vào tmp để verify entry mà không đụng $HOME.
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    monkeypatch.setenv("VIBECODE_AUDIT_LOG_DIR", str(audit_dir))

    out = te.execute_blocks(
        tmp_path,
        blocks=[{"tool": "run_command", "input": {"cmd": "rm -rf /"}}],
        mode="default",
    )

    assert len(out["results"]) == 1
    res = out["results"][0]
    assert res["status"] == "deny"
    assert res["result"]["permission"]["decision"] == "deny"

    # Audit log: phải có 1 entry "deny" cho cmd này (cmd_hash, không
    # plaintext) — xem _audit_log.py format.
    log_path = audit_dir / "attempts.jsonl"
    assert log_path.exists(), (
        f"audit log không được ghi tại {log_path}; entry deny thiếu."
    )
    lines = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    deny_entries = [e for e in lines if e.get("decision") == "deny"]
    assert deny_entries, f"audit log không có entry deny; lines={lines}"
    # cmd_hash phải là sha256:<prefix>, KHÔNG plaintext (security guard).
    for e in deny_entries:
        assert e.get("cmd_hash", "").startswith("sha256:"), (
            f"cmd_hash phải dùng sha256 prefix, có thể leak plaintext: {e}"
        )
        for forbidden in ("rm -rf /", "rm-rf-/"):
            assert forbidden not in json.dumps(e), (
                f"audit entry leak plaintext command: {e}"
            )


def test_run_command_allow_path_subprocess_via_direct_call(
    tmp_path: Path
) -> None:
    """Allow path integration: gọi ``_tool_run_command`` trực tiếp với
    cmd allow → subprocess được dispatch.  Note: production
    ``execute_one`` route gọi ``_tool_run_command`` qua nhánh đặc biệt
    (xem TOOL_IMPL không chứa run_command), nên test này dùng direct
    call để verify allow + subprocess dispatch."""
    from unittest.mock import MagicMock, patch

    from vibecodekit.event_bus import EventBus

    bus = EventBus(tmp_path)
    with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
        proc = MagicMock()
        proc.communicate.return_value = ("On branch main", "")
        proc.returncode = 0
        mock_popen.return_value = proc

        out = te._tool_run_command(
            tmp_path, {"cmd": "git status"}, bus, mode="default",
        )

    assert out["executed"] is True
    assert out["returncode"] == 0
    assert out["permission"]["decision"] == "allow"
