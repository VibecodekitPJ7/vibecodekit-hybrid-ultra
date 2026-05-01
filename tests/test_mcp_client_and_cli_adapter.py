"""Cycle 11 PR1 — coverage suite for ``mcp_client`` + ``browser/cli_adapter``.

Mục tiêu:
* ``scripts/vibecodekit/mcp_client.py``   62% → ≥85%
* ``scripts/vibecodekit/browser/cli_adapter.py`` 33% → ≥85%

Strategy:
* Manifest helpers (load / save / register / list / disable) đều run
  trên ``tmp_path`` — không touch real ``.vibecode/runtime/``.
* ``_call_inproc`` test bằng module có sẵn (``json``, ``builtins``)
  thay vì spawn subprocess.
* ``StdioSession`` test bằng fake ``Popen`` shape (BytesIO stdin/stdout)
  qua ``monkeypatch.setattr(subprocess, "Popen", _FakePopen)`` — không
  spawn process thật trong CI.
* ``DaemonClient`` HTTP test bằng monkeypatch ``urllib.request.urlopen``
  — không bind socket trong CI.

KHÔNG đụng runtime code.  Test code only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from vibecodekit import mcp_client as mc
from vibecodekit.browser import cli_adapter as ca
from vibecodekit.browser import state as state_mod


# ---------------------------------------------------------------------------
# 1. mcp_client: manifest helpers
# ---------------------------------------------------------------------------

def test_load_manifest_missing_file_returns_empty(tmp_path: Path) -> None:
    out = mc.load_manifest(tmp_path)
    assert out == {"servers": []}


def test_load_manifest_valid_json(tmp_path: Path) -> None:
    p = tmp_path / mc.MANIFEST_REL
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"servers": [{"name": "x"}]}), encoding="utf-8")
    out = mc.load_manifest(tmp_path)
    assert out["servers"][0]["name"] == "x"


def test_load_manifest_malformed_json_falls_back(tmp_path: Path) -> None:
    p = tmp_path / mc.MANIFEST_REL
    p.parent.mkdir(parents=True)
    p.write_text("not-json{", encoding="utf-8")
    out = mc.load_manifest(tmp_path)
    assert out == {"servers": []}


def test_save_manifest_creates_parent(tmp_path: Path) -> None:
    mc.save_manifest(tmp_path, {"servers": [{"name": "y"}]})
    p = tmp_path / mc.MANIFEST_REL
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8"))["servers"][0]["name"] == "y"


def test_register_server_unsupported_transport_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported transport"):
        mc.register_server(tmp_path, "bad", transport="websocket")


def test_register_server_replaces_existing(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "a", transport="inproc", module="m1")
    mc.register_server(tmp_path, "a", transport="inproc", module="m2")
    servers = mc.list_servers(tmp_path)
    assert len(servers) == 1
    assert servers[0]["module"] == "m2"


def test_register_server_with_command_env_handshake(tmp_path: Path) -> None:
    s = mc.register_server(
        tmp_path, "stdio-x", transport="stdio",
        command=["python3", "-m", "x.y"], env={"K": "V"},
        description="my server", handshake=True,
    )
    assert s["transport"] == "stdio"
    assert s["command"] == ["python3", "-m", "x.y"]
    assert s["env"] == {"K": "V"}
    assert s["handshake"] is True
    assert s["description"] == "my server"
    assert s["enabled"] is True


def test_disable_server_existing_and_missing(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "alpha", transport="inproc", module="m")
    assert mc.disable_server(tmp_path, "alpha") is True
    assert mc.list_servers(tmp_path)[0]["enabled"] is False
    # second disable: already disabled, no change.
    assert mc.disable_server(tmp_path, "alpha") is False
    assert mc.disable_server(tmp_path, "missing") is False


# ---------------------------------------------------------------------------
# 2. mcp_client: _call_inproc
# ---------------------------------------------------------------------------

def test_call_inproc_missing_module() -> None:
    out = mc._call_inproc({}, "anything", {})
    assert "error" in out and "module" in out["error"]


def test_call_inproc_import_error() -> None:
    out = mc._call_inproc({"module": "definitely_not_a_real_module_xyz"},
                         "x", {})
    assert "cannot import" in out["error"]


def test_call_inproc_not_callable() -> None:
    # ``json.__doc__`` is a string, not callable.
    out = mc._call_inproc({"module": "json"}, "__doc__", {})
    assert "not callable" in out["error"]


def test_call_inproc_success() -> None:
    # ``json.dumps`` is callable.
    out = mc._call_inproc({"module": "json"}, "dumps", {"obj": {"a": 1}})
    assert out == {"ok": True, "result": '{"a": 1}'}


def test_call_inproc_callable_raises() -> None:
    out = mc._call_inproc({"module": "json"}, "loads", {"s": "not-json"})
    assert out["error"].startswith("JSONDecodeError")


# ---------------------------------------------------------------------------
# 3. mcp_client: _call_stdio_oneshot (subprocess mock)
# ---------------------------------------------------------------------------


class _FakeProc:
    """Minimal Popen double for ``_call_stdio_oneshot`` tests."""

    def __init__(self, stdout: str = "", stderr: str = "",
                 returncode: int = 0,
                 raise_on_communicate: Optional[Exception] = None) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._raise = raise_on_communicate
        self.killed = False

    def communicate(self, _input: str = "", timeout: float = 10.0):
        if self._raise is not None:
            raise self._raise
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True


def test_call_stdio_oneshot_missing_command() -> None:
    out = mc._call_stdio_oneshot({}, "ping", {})
    assert "command" in out["error"]


def test_call_stdio_oneshot_filenotfound(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> None:
        raise FileNotFoundError("no such binary")

    monkeypatch.setattr(mc.subprocess, "Popen", boom)
    out = mc._call_stdio_oneshot({"command": ["nope"]}, "ping", {})
    assert "cannot start" in out["error"]


def test_call_stdio_oneshot_success(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = _FakeProc(stdout=json.dumps({"jsonrpc": "2.0", "id": 1,
                                         "result": "pong"}) + "\n")
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: proc)
    out = mc._call_stdio_oneshot({"command": ["x"]}, "ping", {})
    assert out["result"] == "pong"


def test_call_stdio_oneshot_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = _FakeProc(raise_on_communicate=subprocess.TimeoutExpired(cmd=["x"],
                                                                    timeout=1.0))
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: proc)
    out = mc._call_stdio_oneshot({"command": ["x"]}, "ping", {}, timeout=1.0)
    assert "timeout" in out["error"]
    assert proc.killed is True


def test_call_stdio_oneshot_nonzero_returncode(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = _FakeProc(stdout="", stderr="boom", returncode=42)
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: proc)
    out = mc._call_stdio_oneshot({"command": ["x"]}, "ping", {})
    assert "exit 42" in out["error"]


def test_call_stdio_oneshot_no_json(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = _FakeProc(stdout="hello\nworld\n")
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: proc)
    out = mc._call_stdio_oneshot({"command": ["x"]}, "ping", {})
    assert "no JSON" in out["error"]


def test_call_stdio_oneshot_skips_non_json_then_returns_first(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two lines: the first is log noise, the second is the real reply.
    body = "log line\n" + json.dumps({"id": 1, "result": "ok"}) + "\n"
    proc = _FakeProc(stdout=body)
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: proc)
    out = mc._call_stdio_oneshot({"command": ["x"]}, "ping", {})
    assert out == {"id": 1, "result": "ok"}


# ---------------------------------------------------------------------------
# 4. mcp_client: _call_stdio_handshake / dispatcher
# ---------------------------------------------------------------------------


def test_call_stdio_handshake_missing_command() -> None:
    out = mc._call_stdio_handshake({}, "ping", {})
    assert "command" in out["error"]


def test_call_stdio_handshake_filenotfound(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(self) -> None:
        raise FileNotFoundError("no binary")

    monkeypatch.setattr(mc.StdioSession, "open", boom)
    out = mc._call_stdio_handshake({"command": ["x"]}, "ping", {})
    assert "cannot start" in out["error"]


def test_call_stdio_handshake_session_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(self) -> None:
        raise mc.StdioSessionError("session blew up")

    monkeypatch.setattr(mc.StdioSession, "open", boom)
    out = mc._call_stdio_handshake({"command": ["x"]}, "ping", {})
    assert out["error"] == "session blew up"


def test_call_stdio_dispatches_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    flag = {"called": False}

    def fake_handshake(server: Dict[str, Any], tool: str,
                       args: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        flag["called"] = True
        return {"ok": True}

    monkeypatch.setattr(mc, "_call_stdio_handshake", fake_handshake)
    out = mc._call_stdio({"handshake": True, "command": ["x"]}, "ping", {})
    assert out == {"ok": True}
    assert flag["called"] is True


def test_call_stdio_dispatches_oneshot(monkeypatch: pytest.MonkeyPatch) -> None:
    flag = {"called": False}

    def fake_oneshot(server: Dict[str, Any], tool: str,
                     args: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        flag["called"] = True
        return {"ok": True}

    monkeypatch.setattr(mc, "_call_stdio_oneshot", fake_oneshot)
    out = mc._call_stdio({"command": ["x"]}, "ping", {})
    assert out == {"ok": True}
    assert flag["called"] is True


# ---------------------------------------------------------------------------
# 5. mcp_client: _resolve / list_tools / call_tool
# ---------------------------------------------------------------------------

def test_resolve_missing_returns_none(tmp_path: Path) -> None:
    assert mc._resolve(tmp_path, "missing") is None


def test_resolve_disabled_returns_none(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "x", transport="inproc", module="m")
    mc.disable_server(tmp_path, "x")
    assert mc._resolve(tmp_path, "x") is None


def test_list_tools_missing_server(tmp_path: Path) -> None:
    out = mc.list_tools(tmp_path, "missing")
    assert "no enabled MCP server" in out["error"]


def test_list_tools_inproc_missing_module(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "x", transport="inproc")
    out = mc.list_tools(tmp_path, "x")
    assert "module" in out["error"]


def test_list_tools_inproc_import_error(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "x", transport="inproc",
                       module="not_a_real_module_xyz_qq")
    out = mc.list_tools(tmp_path, "x")
    assert "cannot import" in out["error"]


def test_list_tools_inproc_success(tmp_path: Path) -> None:
    # ``json`` exposes ``dumps``, ``loads``, etc. as public callables.
    mc.register_server(tmp_path, "x", transport="inproc", module="json")
    out = mc.list_tools(tmp_path, "x")
    assert out["ok"] is True
    names = {t["name"] for t in out["tools"]}
    assert {"dumps", "loads"}.issubset(names)


def test_list_tools_oneshot_stdio_rejected(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "x", transport="stdio",
                       command=["echo"], handshake=False)
    out = mc.list_tools(tmp_path, "x")
    assert "one-shot" in out["error"]


def test_list_tools_handshake_missing_command(tmp_path: Path) -> None:
    # Manually craft a manifest with handshake=True but no command.
    mc.save_manifest(tmp_path, {"servers": [{
        "name": "x", "transport": "stdio", "enabled": True,
        "handshake": True,
    }]})
    out = mc.list_tools(tmp_path, "x")
    assert "command" in out["error"]


def test_list_tools_handshake_filenotfound(tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    mc.register_server(tmp_path, "x", transport="stdio",
                       command=["nope"], handshake=True)
    monkeypatch.setattr(mc.StdioSession, "open",
                        lambda self: (_ for _ in ()).throw(FileNotFoundError("x")))
    out = mc.list_tools(tmp_path, "x")
    assert "cannot start" in out["error"]


def test_list_tools_handshake_session_error(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    mc.register_server(tmp_path, "x", transport="stdio",
                       command=["echo"], handshake=True)
    monkeypatch.setattr(
        mc.StdioSession, "open",
        lambda self: (_ for _ in ()).throw(mc.StdioSessionError("nope")),
    )
    out = mc.list_tools(tmp_path, "x")
    assert out["error"] == "nope"


def test_call_tool_missing_server(tmp_path: Path) -> None:
    out = mc.call_tool(tmp_path, "missing", "ping")
    assert "no enabled MCP server" in out["error"]


def test_call_tool_invalid_timeout_falls_back(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    mc.register_server(tmp_path, "x", transport="inproc", module="json")

    def fake_inproc(server: Dict[str, Any], tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True}

    monkeypatch.setattr(mc, "_call_inproc", fake_inproc)
    out = mc.call_tool(tmp_path, "x", "dumps", args={"obj": {}}, timeout="bad")  # type: ignore[arg-type]
    assert out == {"ok": True}


def test_call_tool_clamps_timeout(tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    mc.register_server(tmp_path, "x", transport="stdio",
                       command=["echo"])
    seen: List[float] = []

    def fake_stdio(server: Dict[str, Any], tool: str,
                   args: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        seen.append(timeout)
        return {"ok": True}

    monkeypatch.setattr(mc, "_call_stdio", fake_stdio)
    mc.call_tool(tmp_path, "x", "ping", timeout=10**6)
    assert seen[0] == mc.MAX_TIMEOUT
    mc.call_tool(tmp_path, "x", "ping", timeout=0.0)
    assert seen[1] == mc.MIN_TIMEOUT


def test_call_tool_inproc(tmp_path: Path) -> None:
    mc.register_server(tmp_path, "x", transport="inproc", module="json")
    out = mc.call_tool(tmp_path, "x", "dumps", args={"obj": {"a": 1}})
    assert out["ok"] is True


# ---------------------------------------------------------------------------
# 6. mcp_client: StdioSession (with fake Popen)
# ---------------------------------------------------------------------------


class _RealPipeStream:
    """Wrap an os.pipe() endpoint so it has a real fd for selectors."""

    def __init__(self, fd: int, mode: str) -> None:
        self._fd = fd
        self._mode = mode
        self.written = bytearray()
        self.closed = False

    # write side
    def write(self, b: bytes) -> int:
        self.written.extend(b)
        return len(b)

    def flush(self) -> None:
        pass

    # read side: feed bytes via a backing buffer.
    def feed(self, b: bytes) -> None:
        self._buf.extend(b)

    def read1(self, n: int) -> bytes:
        if not self._buf:
            return b""
        chunk = bytes(self._buf[:n])
        del self._buf[:n]
        return chunk

    def read(self, n: int = -1) -> bytes:
        if n == -1 or n >= len(self._buf):
            out = bytes(self._buf)
            self._buf.clear()
            return out
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                os.close(self._fd)
            except OSError:
                pass

    def fileno(self) -> int:
        return self._fd


class _RealReadStream(_RealPipeStream):
    def __init__(self, data: bytes) -> None:
        # We need a real read-end fd to register on the selector.  Use a
        # pipe and write the canned data into the write end, then close
        # the write end so EOF is observed naturally if the test reads
        # past the buffer.
        r, w = os.pipe()
        # Pre-feed bytes via the write fd so ``select`` actually sees the
        # fd as readable in real-fd land too.
        if data:
            os.write(w, data)
        os.close(w)
        super().__init__(r, "rb")
        # Backing software buffer (StdioSession uses ``read1`` on this
        # object which we override to read from ``self._buf``).
        self._buf = bytearray(data)


class _RealWriteStream(_RealPipeStream):
    def __init__(self) -> None:
        r, w = os.pipe()
        os.close(r)
        super().__init__(w, "wb")
        self._buf = bytearray()


class _FakeStdioPopen:
    """Drop-in for ``subprocess.Popen`` used by ``StdioSession`` tests."""

    def __init__(self, stdout_bytes: bytes = b"", returncode: Optional[int] = None) -> None:
        self.stdin = _RealWriteStream()
        self.stdout = _RealReadStream(stdout_bytes)
        self.stderr = _RealReadStream(b"")
        self.returncode = returncode

    def poll(self) -> Optional[int]:
        return self.returncode

    def wait(self, timeout: float = 0) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.returncode = -9


@pytest.fixture
def fake_select(monkeypatch: pytest.MonkeyPatch):
    """Make ``DefaultSelector.select`` always claim the fd is ready."""
    import selectors as _sel

    def _select(self, timeout: float = 0):
        if not self.get_map():
            return []
        key = next(iter(self.get_map().values()))
        return [(key, _sel.EVENT_READ)]

    monkeypatch.setattr(_sel.DefaultSelector, "select", _select)


def _spawn_session(monkeypatch: pytest.MonkeyPatch,
                    stdout_bytes: bytes,
                    returncode: Optional[int] = None) -> mc.StdioSession:
    fake = _FakeStdioPopen(stdout_bytes=stdout_bytes, returncode=returncode)
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: fake)
    sess = mc.StdioSession(["x"], env={"K": "V"}, timeout=0.5)
    sess.open()
    return sess


def test_stdio_session_open_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _spawn_session(monkeypatch, b"")
    proc = sess._proc
    sess.open()  # second open is a no-op.
    assert sess._proc is proc
    sess.close()


def test_stdio_session_send_recv_request(monkeypatch: pytest.MonkeyPatch,
                                          fake_select: None) -> None:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": "pong"}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    resp = sess._request("ping", {})
    assert resp["result"] == "pong"
    sess.close()


def test_stdio_session_recv_skips_log_noise(monkeypatch: pytest.MonkeyPatch,
                                             fake_select: None) -> None:
    body = (
        "stderr-like log noise\n"
        + json.dumps({"id": 1, "result": "ok"}) + "\n"
    )
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    resp = sess._request("ping", {})
    assert resp == {"id": 1, "result": "ok"}
    sess.close()


def test_stdio_session_recv_timeout(monkeypatch: pytest.MonkeyPatch,
                                     fake_select: None) -> None:
    sess = _spawn_session(monkeypatch, b"")
    sess._timeout = 0.1
    with pytest.raises(mc.StdioSessionError, match="timeout"):
        sess._request("ping", {})
    sess.close()


def test_stdio_session_recv_server_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStdioPopen(stdout_bytes=b"", returncode=7)
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: fake)
    sess = mc.StdioSession(["x"], timeout=0.5)
    sess.open()
    with pytest.raises(mc.StdioSessionError, match="server exited"):
        sess._request("ping", {})
    sess.close()


def test_stdio_session_send_after_close_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _spawn_session(monkeypatch, b"")
    sess.close()
    with pytest.raises(mc.StdioSessionError):
        sess._send({"jsonrpc": "2.0"})


def test_stdio_session_send_broken_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _spawn_session(monkeypatch, b"")

    def boom(_b: bytes) -> int:
        raise BrokenPipeError("pipe died")

    sess._proc.stdin.write = boom  # type: ignore[assignment]
    with pytest.raises(mc.StdioSessionError, match="send failed"):
        sess._send({"jsonrpc": "2.0"})
    sess.close()


def test_stdio_session_initialize_success(monkeypatch: pytest.MonkeyPatch,
                                           fake_select: None) -> None:
    body = json.dumps({"id": 1, "result": {
        "serverInfo": {"name": "srv"},
        "capabilities": {"tools": {}},
    }}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    out = sess.initialize()
    assert sess.server_info == {"name": "srv"}
    assert sess.server_capabilities == {"tools": {}}
    assert out["serverInfo"]["name"] == "srv"
    sess.close()


def test_stdio_session_initialize_error(monkeypatch: pytest.MonkeyPatch,
                                         fake_select: None) -> None:
    body = json.dumps({"id": 1, "error": {"code": 1, "message": "no"}}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    with pytest.raises(mc.StdioSessionError, match="initialize error"):
        sess.initialize()
    sess.close()


def test_stdio_session_list_tools_success(monkeypatch: pytest.MonkeyPatch,
                                           fake_select: None) -> None:
    body = json.dumps({"id": 1, "result": {"tools": [{"name": "ping"}]}}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    tools = sess.list_tools()
    assert tools == [{"name": "ping"}]
    sess.close()


def test_stdio_session_list_tools_error(monkeypatch: pytest.MonkeyPatch,
                                         fake_select: None) -> None:
    body = json.dumps({"id": 1, "error": {"code": 2}}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    with pytest.raises(mc.StdioSessionError, match="tools/list error"):
        sess.list_tools()
    sess.close()


def test_stdio_session_call_tool(monkeypatch: pytest.MonkeyPatch,
                                  fake_select: None) -> None:
    body = json.dumps({"id": 1, "result": "pong"}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    out = sess.call_tool("ping", {})
    assert out["result"] == "pong"
    sess.close()


def test_stdio_session_public_request_notify(monkeypatch: pytest.MonkeyPatch,
                                              fake_select: None) -> None:
    body = json.dumps({"id": 1, "result": "ok"}) + "\n"
    sess = _spawn_session(monkeypatch, body.encode("utf-8"))
    out = sess.request("ping/extension", {"k": "v"})
    assert out["result"] == "ok"
    sess.notify("logging/setLevel", {"level": "info"})
    # Notification should have written without expecting a response.
    written = bytes(sess._proc.stdin.written).decode("utf-8")
    assert '"method": "logging/setLevel"' in written
    sess.close()


def test_stdio_session_context_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStdioPopen(stdout_bytes=b"")
    monkeypatch.setattr(mc.subprocess, "Popen", lambda *a, **k: fake)
    with mc.StdioSession(["x"], timeout=0.5) as sess:
        assert sess._proc is fake
    assert sess._proc is None


def test_stdio_session_stderr_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    sess = _spawn_session(monkeypatch, b"")
    # Manually feed bytes to the deque (drain thread reads from real
    # stderr in production; in tests we sidestep it).
    sess._stderr_buf.extend(b"hello stderr")
    assert sess.stderr_tail() == b"hello stderr"
    sess.close()


# ---------------------------------------------------------------------------
# 7. browser/cli_adapter: DaemonClient
# ---------------------------------------------------------------------------


def _state(port: int = 7777, pid: int = 1) -> state_mod.BrowserState:
    return state_mod.BrowserState(pid=pid, port=port, started_ts=0.0)


def test_daemon_not_running_when_state_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: None)
    client = ca.DaemonClient()
    with pytest.raises(ca.DaemonNotRunning):
        client._state()


def test_daemon_not_running_when_pid_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: _state())
    monkeypatch.setattr(state_mod, "is_pid_alive", lambda _pid: False)
    with pytest.raises(ca.DaemonNotRunning):
        ca.DaemonClient()._state()


def test_daemon_state_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: _state(port=8080))
    monkeypatch.setattr(state_mod, "is_pid_alive", lambda _pid: True)
    s = ca.DaemonClient()._state()
    assert s.port == 8080


def test_is_daemon_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: None)
    assert ca.is_daemon_alive() is False
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: _state(port=8080))
    monkeypatch.setattr(state_mod, "is_pid_alive", lambda _pid: True)
    assert ca.is_daemon_alive() is True


class _FakeUrlopen:
    """Drop-in for ``urllib.request.urlopen`` returning canned bytes."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeUrlopen":
        return self

    def __exit__(self, *a: Any) -> None:
        pass

    def read(self) -> bytes:
        return self._body


@pytest.fixture
def alive_daemon(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(state_mod, "read_state", lambda path=None: _state(port=8080))
    monkeypatch.setattr(state_mod, "is_pid_alive", lambda _pid: True)


def test_daemon_health(monkeypatch: pytest.MonkeyPatch, alive_daemon: None) -> None:
    body = json.dumps({"status": "ok"}).encode()
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout: _FakeUrlopen(body))
    out = ca.DaemonClient().health()
    assert out == {"status": "ok"}


def test_daemon_command(monkeypatch: pytest.MonkeyPatch, alive_daemon: None) -> None:
    body = json.dumps({"ok": True, "verb": "goto"}).encode()
    captured: Dict[str, Any] = {}

    def fake_open(req: urllib.request.Request, timeout: float):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["data"] = req.data
        return _FakeUrlopen(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    out = ca.DaemonClient().command("goto", target="https://x",
                                    extras={"wait_until": "load"})
    assert out["ok"] is True
    assert captured["method"] == "POST"
    assert "8080/command" in captured["url"]
    payload = json.loads(captured["data"].decode())
    assert payload == {"verb": "goto", "target": "https://x",
                        "extras": {"wait_until": "load"}}


def test_daemon_command_default_extras(monkeypatch: pytest.MonkeyPatch,
                                        alive_daemon: None) -> None:
    body = json.dumps({"ok": True}).encode()
    captured: Dict[str, Any] = {}

    def fake_open(req: urllib.request.Request, timeout: float):
        captured["data"] = req.data
        return _FakeUrlopen(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    ca.DaemonClient().command("text")
    payload = json.loads(captured["data"].decode())
    assert payload == {"verb": "text", "target": None, "extras": {}}


def test_daemon_shutdown_success(monkeypatch: pytest.MonkeyPatch,
                                  alive_daemon: None) -> None:
    body = json.dumps({"shutdown": True}).encode()
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout: _FakeUrlopen(body))
    out = ca.DaemonClient().shutdown()
    assert out["shutdown"] is True


def test_daemon_shutdown_already_dead(monkeypatch: pytest.MonkeyPatch,
                                       alive_daemon: None) -> None:
    def boom(req: urllib.request.Request, timeout: float):
        raise urllib.error.URLError("connection refused")

    cleared = {"called": False}

    def fake_clear(path: Optional[Path] = None) -> None:
        cleared["called"] = True

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(state_mod, "clear_state", fake_clear)
    out = ca.DaemonClient().shutdown()
    assert out == {"status": "already_stopped"}
    assert cleared["called"] is True


def test_daemon_send_url_error(monkeypatch: pytest.MonkeyPatch,
                                alive_daemon: None) -> None:
    def boom(req: urllib.request.Request, timeout: float):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(ca.DaemonHttpError, match="HTTP error"):
        ca.DaemonClient().health()


def test_daemon_send_empty_body(monkeypatch: pytest.MonkeyPatch,
                                 alive_daemon: None) -> None:
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout: _FakeUrlopen(b""))
    assert ca.DaemonClient().health() == {}


def test_daemon_send_invalid_json(monkeypatch: pytest.MonkeyPatch,
                                   alive_daemon: None) -> None:
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout: _FakeUrlopen(b"not-json"))
    with pytest.raises(ca.DaemonHttpError, match="non-JSON"):
        ca.DaemonClient().health()


# ---------------------------------------------------------------------------
# 8. browser/cli_adapter: main()
# ---------------------------------------------------------------------------


def test_main_no_args_prints_usage(capsys: pytest.CaptureFixture) -> None:
    rc = ca.main([])
    assert rc == 2
    err = capsys.readouterr().err
    assert "usage:" in err


def test_main_health(monkeypatch: pytest.MonkeyPatch,
                      capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(ca.DaemonClient, "health",
                        lambda self: {"status": "ok"})
    rc = ca.main(["health"])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"status": "ok"}


def test_main_shutdown(monkeypatch: pytest.MonkeyPatch,
                        capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(ca.DaemonClient, "shutdown",
                        lambda self: {"shutdown": True})
    rc = ca.main(["shutdown"])
    assert rc == 0


def test_main_command_with_extras(monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture) -> None:
    captured: Dict[str, Any] = {}

    def fake_command(self: Any, verb: str, target: Optional[str] = None,
                     extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        captured["verb"] = verb
        captured["target"] = target
        captured["extras"] = extras
        return {"ok": True}

    monkeypatch.setattr(ca.DaemonClient, "command", fake_command)
    rc = ca.main(["fill", "input#name", "value=Alice", "scope=outer"])
    assert rc == 0
    assert captured["verb"] == "fill"
    assert captured["target"] == "input#name"
    assert captured["extras"] == {"value": "Alice", "scope": "outer"}


def test_main_daemon_not_running(monkeypatch: pytest.MonkeyPatch,
                                  capsys: pytest.CaptureFixture) -> None:
    def boom(self) -> None:
        raise ca.DaemonNotRunning("nope")

    monkeypatch.setattr(ca.DaemonClient, "health", boom)
    rc = ca.main(["health"])
    assert rc == 3
    assert "nope" in capsys.readouterr().err


def test_main_daemon_http_error(monkeypatch: pytest.MonkeyPatch,
                                  capsys: pytest.CaptureFixture) -> None:
    def boom(self) -> None:
        raise ca.DaemonHttpError("boom")

    monkeypatch.setattr(ca.DaemonClient, "health", boom)
    rc = ca.main(["health"])
    assert rc == 4


def test_main_uses_argv_when_none(monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(sys, "argv", ["prog"])
    rc = ca.main()
    assert rc == 2
