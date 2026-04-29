"""Tests for the production MCP core server (``mcp_servers.core``).

Covers:
- In-process tool callables return valid dicts
- MCP stdio protocol (initialize + tools/list + tools/call)
- All 12 tools are registered with JSON Schema
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_PKG = str(Path(__file__).resolve().parent.parent / "scripts")
_REPO = str(Path(__file__).resolve().parent.parent)


# ---------------------------------------------------------------------------
# In-process callable tests
# ---------------------------------------------------------------------------

class TestInProcessTools:
    """Verify each tool callable works when imported directly."""

    def test_permission_classify_safe(self):
        from vibecodekit.mcp_servers.core import permission_classify
        r = permission_classify("git status")
        assert r["class"] == "read_only"
        assert r["decision"] == "allow"

    def test_permission_classify_dangerous(self):
        from vibecodekit.mcp_servers.core import permission_classify
        r = permission_classify("rm -rf /")
        assert r["decision"] == "deny"

    def test_permission_decide(self):
        from vibecodekit.mcp_servers.core import permission_decide
        with tempfile.TemporaryDirectory() as tmp:
            r = permission_decide("ls -la", root=tmp)
        assert "decision" in r

    def test_doctor_check(self):
        from vibecodekit.mcp_servers.core import doctor_check
        r = doctor_check(root=_REPO)
        assert "skill_repo" in r

    def test_audit_run(self):
        from vibecodekit.mcp_servers.core import audit_run
        r = audit_run(threshold=0.5)
        assert r["passed"] > 0
        assert r["met"] is True

    def test_scaffold_list(self):
        from vibecodekit.mcp_servers.core import scaffold_list
        r = scaffold_list()
        assert len(r["presets"]) >= 10
        names = [p["name"] for p in r["presets"]]
        assert "api-todo" in names

    def test_scaffold_preview(self):
        from vibecodekit.mcp_servers.core import scaffold_preview
        r = scaffold_preview(preset="api-todo", stack="fastapi")
        assert r["preset"] == "api-todo"
        assert r["stack"] == "fastapi"
        assert len(r["files"]) > 0

    def test_intent_classify(self):
        from vibecodekit.mcp_servers.core import intent_classify
        r = intent_classify("build a REST API")
        assert "intents" in r
        assert "commands" in r

    def test_memory_stats(self):
        from vibecodekit.mcp_servers.core import memory_stats
        with tempfile.TemporaryDirectory() as tmp:
            r = memory_stats(root=tmp)
        assert "user" in r
        assert "project" in r
        assert "team" in r

    def test_memory_add_and_retrieve(self):
        from vibecodekit.mcp_servers.core import memory_add, memory_retrieve
        with tempfile.TemporaryDirectory() as tmp:
            add_r = memory_add("test entry from MCP", root=tmp, scope="project")
            assert "tier" in add_r
            ret_r = memory_retrieve("test entry", root=tmp, scope="project")
            assert "results" in ret_r

    def test_dashboard_summarise(self):
        from vibecodekit.mcp_servers.core import dashboard_summarise
        with tempfile.TemporaryDirectory() as tmp:
            r = dashboard_summarise(root=tmp)
        assert isinstance(r, dict)

    def test_compact_run(self):
        from vibecodekit.mcp_servers.core import compact_run
        with tempfile.TemporaryDirectory() as tmp:
            r = compact_run(root=tmp)
        assert isinstance(r, dict)


# ---------------------------------------------------------------------------
# MCP stdio protocol tests
# ---------------------------------------------------------------------------

class TestMCPStdioProtocol:
    """Full MCP JSON-RPC handshake via subprocess."""

    def _call(self, *requests):
        """Send JSON-RPC requests and return parsed responses."""
        stdin = "\n".join(json.dumps(r) for r in requests) + "\n"
        proc = subprocess.run(
            [sys.executable, "-m", "vibecodekit.mcp_servers.core"],
            input=stdin, capture_output=True, text=True,
            cwd=_REPO, env={"PYTHONPATH": _PKG, "PATH": "/usr/bin:/bin"},
            timeout=30,
        )
        lines = [l for l in proc.stdout.strip().split("\n") if l.strip()]
        return [json.loads(l) for l in lines]

    def test_initialize_handshake(self):
        responses = self._call(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert len(responses) == 1
        r = responses[0]
        assert r["result"]["serverInfo"]["name"] == "vibecodekit-core"
        assert r["result"]["protocolVersion"] == "2024-11-05"

    def test_tools_list_returns_12_tools(self):
        responses = self._call(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools_resp = responses[1]
        tools = tools_resp["result"]["tools"]
        assert len(tools) == 12
        names = {t["name"] for t in tools}
        assert "permission_classify" in names
        assert "scaffold_list" in names
        assert "intent_classify" in names
        assert "memory_retrieve" in names
        assert "audit_run" in names

    def test_tools_call_permission_classify(self):
        responses = self._call(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "permission_classify",
                        "arguments": {"command": "git status"}}},
        )
        r = responses[1]["result"]
        assert r["decision"] == "allow"

    def test_tools_call_unknown_tool(self):
        responses = self._call(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "nonexistent_tool", "arguments": {}}},
        )
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_all_tools_have_input_schema(self):
        responses = self._call(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools = responses[1]["result"]["tools"]
        for tool in tools:
            assert "inputSchema" in tool, f"Missing inputSchema for {tool['name']}"
            assert tool["inputSchema"]["type"] == "object"
