"""Coverage-focused tests cho ``vibecodekit.tool_executor``.

Mục tiêu (cycle 6 PR3): nâng coverage của ``tool_executor.py`` từ ~39%
lên ≥80%.  Hot-path subprocess execute là module nguy hiểm nhất; mỗi
path (allow/deny/timeout/error/forward) phải có test cover.

Test mocks ``subprocess.Popen`` để KHÔNG chạy real shell trong CI —
chỉ verify control-flow của permission/dispatch/timeout layer.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vibecodekit import tool_executor as te  # noqa: E402
from vibecodekit.event_bus import EventBus  # noqa: E402


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

class TestResolveUnderRoot:
    def test_empty_rel_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty path"):
            te._resolve_under_root(tmp_path, "")

    def test_relative_inside_root_ok(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("x")
        result = te._resolve_under_root(tmp_path, "a.txt")
        assert result == (tmp_path / "a.txt").resolve()

    def test_dotdot_escape_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes project root"):
            te._resolve_under_root(tmp_path, "../../etc/passwd")

    def test_absolute_outside_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes project root"):
            te._resolve_under_root(tmp_path, "/etc/passwd")

    def test_absolute_inside_ok(self, tmp_path: Path) -> None:
        target = tmp_path / "inner" / "f.txt"
        target.parent.mkdir()
        target.write_text("x")
        result = te._resolve_under_root(tmp_path, str(target))
        assert result == target.resolve()


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:
    def test_missing_target(self, tmp_path: Path) -> None:
        out = te._tool_list_files(tmp_path, {"path": "no-such-dir"})
        assert "missing" in out

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("x")
        out = te._tool_list_files(tmp_path, {"path": "f.txt"})
        assert out["files"] == ["f.txt"]

    def test_directory_listing(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        out = te._tool_list_files(tmp_path, {"path": ".", "depth": 1})
        assert "a.txt" in out["files"] and "b.txt" in out["files"]
        assert out["truncated"] is False

    def test_depth_limits(self, tmp_path: Path) -> None:
        (tmp_path / "deep" / "deeper").mkdir(parents=True)
        (tmp_path / "deep" / "shallow.txt").write_text("s")
        (tmp_path / "deep" / "deeper" / "x.txt").write_text("x")
        out = te._tool_list_files(tmp_path, {"path": "deep", "depth": 1})
        # depth=1 includes shallow.txt + deeper/, excludes deeper/x.txt.
        files = out["files"]
        assert any(f.endswith("shallow.txt") for f in files)
        assert not any(f.endswith("x.txt") for f in files)

    def test_max_files_truncation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text("x")
        monkeypatch.setattr(te, "MAX_FILES_LISTED", 3)
        out = te._tool_list_files(tmp_path, {"path": ".", "depth": 1})
        assert out["truncated"] is True
        assert out["limit"] == 3


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_read_basic(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("hello")
        out = te._tool_read_file(tmp_path, {"path": "a.txt"})
        assert out["content"] == "hello"
        assert out["bytes"] == 5
        assert out["eof"] is True
        assert out["truncated"] is False

    def test_read_with_offset_and_length(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("0123456789")
        out = te._tool_read_file(tmp_path, {"path": "a.txt", "offset": 2, "length": 3})
        assert out["content"] == "234"
        assert out["offset"] == 2
        assert out["next_offset"] == 5
        assert out["eof"] is False

    def test_read_truncation_signal(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("0123456789")
        out = te._tool_read_file(tmp_path, {"path": "a.txt", "length": 4})
        assert out["truncated"] is True
        assert out["content"] == "0123"

    def test_read_invalid_path(self, tmp_path: Path) -> None:
        out = te._tool_read_file(tmp_path, {"path": "../escape"})
        assert "error" in out

    def test_read_missing_required(self, tmp_path: Path) -> None:
        out = te._tool_read_file(tmp_path, {"path": "missing.txt"})
        assert "error" in out

    def test_read_missing_optional(self, tmp_path: Path) -> None:
        out = te._tool_read_file(tmp_path, {"path": "missing.txt", "optional": True})
        assert "missing" in out

    def test_read_invalid_utf8_replaced(self, tmp_path: Path) -> None:
        (tmp_path / "a.bin").write_bytes(b"\xff\xfe abc")
        out = te._tool_read_file(tmp_path, {"path": "a.bin"})
        assert "content" in out
        assert "abc" in out["content"]


# ---------------------------------------------------------------------------
# grep
# ---------------------------------------------------------------------------

class TestGrep:
    def test_match(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("import os\nimport sys\n")
        out = te._tool_grep(tmp_path, {"pattern": r"^import", "glob": "*.py"})
        assert len(out["matches"]) == 2
        assert out["truncated"] is False

    def test_invalid_regex(self, tmp_path: Path) -> None:
        out = te._tool_grep(tmp_path, {"pattern": "([", "glob": "*.py"})
        assert "error" in out

    def test_ignore_case(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("Hello\nWORLD\n")
        out = te._tool_grep(tmp_path, {"pattern": "hello",
                                        "glob": "*.txt", "ignore_case": True})
        assert len(out["matches"]) == 1

    def test_max_results_truncation(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("\n".join("x" for _ in range(10)))
        out = te._tool_grep(tmp_path, {"pattern": "x", "glob": "*.txt", "max_results": 3})
        assert out["truncated"] is True
        assert len(out["matches"]) == 3

    def test_skip_unreadable_file(self, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
        # Tạo file rồi mock read_text raise OSError.
        f = tmp_path / "a.txt"
        f.write_text("x")
        original = Path.read_text

        def fake_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
            if self == f:
                raise OSError("no read perm")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fake_read_text)
        out = te._tool_grep(tmp_path, {"pattern": "x", "glob": "*.txt"})
        assert out["matches"] == []


# ---------------------------------------------------------------------------
# write_file / append_file / delete_file
# ---------------------------------------------------------------------------

class TestWriteAppendDelete:
    def test_write_creates_dirs(self, tmp_path: Path) -> None:
        out = te._tool_write_file(tmp_path,
                                  {"path": "deep/dir/f.txt", "content": "hello"})
        assert (tmp_path / "deep" / "dir" / "f.txt").read_text() == "hello"
        assert out["bytes"] == 5
        assert out["modifier"]["kind"] == "file_changed"

    def test_append(self, tmp_path: Path) -> None:
        (tmp_path / "log.txt").write_text("a")
        out = te._tool_append_file(tmp_path, {"path": "log.txt", "content": "bc"})
        assert (tmp_path / "log.txt").read_text() == "abc"
        assert out["appended"] == 2

    def test_delete_always_blocked(self, tmp_path: Path) -> None:
        out = te._tool_delete_file(tmp_path, {"path": "ignored"})
        assert out["permission"]["decision"] == "deny"


# ---------------------------------------------------------------------------
# glob
# ---------------------------------------------------------------------------

class TestGlob:
    def test_basic(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.py").write_text("b")
        out = te._tool_glob(tmp_path, {"pattern": "*.txt"})
        assert "a.txt" in out["matches"]
        assert all(not m.endswith(".py") for m in out["matches"])

    def test_truncation(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text("x")
        out = te._tool_glob(tmp_path, {"pattern": "*.txt", "max_results": 2})
        assert out["truncated"] is True
        assert out["limit"] == 2


# ---------------------------------------------------------------------------
# run_command — permission flow + subprocess mock
# ---------------------------------------------------------------------------

class TestRunCommand:
    def test_deny_permission_skips_execute(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        out = te._tool_run_command(tmp_path, {"cmd": "rm -rf /"}, bus, mode="default")
        assert out["executed"] is False
        assert out["permission"]["decision"] == "deny"

    def test_allow_then_subprocess(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("ok-out", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            out = te._tool_run_command(tmp_path, {"cmd": "git status"},
                                        bus, mode="default")
        assert out["executed"] is True
        assert out["returncode"] == 0
        assert out["stdout"] == "ok-out"
        # subprocess.Popen được gọi với cwd = str(root) + shell=True
        kwargs = mock_popen.call_args.kwargs
        assert kwargs["cwd"] == str(tmp_path)
        assert kwargs["shell"] is True

    def test_timeout_kills_pgroup(self, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
        bus = EventBus(tmp_path)
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.pid = 999
            # 1st communicate raises Timeout, 2nd returns leftover.
            proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="git status", timeout=1),
                ("stdout-after-kill", "stderr-after-kill"),
            ]
            mock_popen.return_value = proc
            killpg_calls: List[Any] = []
            monkeypatch.setattr(
                te.os, "killpg",
                lambda pid, sig: killpg_calls.append((pid, sig)),
            )
            out = te._tool_run_command(
                tmp_path, {"cmd": "git status", "timeout": 1},
                bus, mode="default",
            )
        assert out["executed"] is True
        assert out["returncode"] == -1
        assert "killed after 1s timeout" in out["stderr"]
        if os.name == "posix":
            assert killpg_calls and killpg_calls[0][0] == 999

    def test_subprocess_exception(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            mock_popen.side_effect = OSError("fork failed")
            out = te._tool_run_command(tmp_path, {"cmd": "git status"},
                                        bus, mode="default")
        assert out["executed"] is False
        assert "fork failed" in out["error"]

    def test_double_timeout_sigkill(self, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
        """Nếu SIGTERM không kill được, fall back SIGKILL."""
        if os.name != "posix":
            pytest.skip("posix-only path")
        bus = EventBus(tmp_path)
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.pid = 1234
            # 1st = initial timeout; 2nd = wait-after-SIGTERM also timeouts;
            # 3rd = final communicate after SIGKILL.
            proc.communicate.side_effect = [
                subprocess.TimeoutExpired(cmd="x", timeout=1),
                subprocess.TimeoutExpired(cmd="x", timeout=5),
                ("kill-out", "kill-err"),
            ]
            mock_popen.return_value = proc
            killpg_calls: List[Any] = []
            monkeypatch.setattr(
                te.os, "killpg",
                lambda pid, sig: killpg_calls.append((pid, sig)),
            )
            out = te._tool_run_command(
                tmp_path, {"cmd": "git status", "timeout": 1},
                bus, mode="default",
            )
        assert out["returncode"] == -1
        assert len(killpg_calls) >= 2  # SIGTERM + SIGKILL


# ---------------------------------------------------------------------------
# execute_one — ACL / hooks / dispatch
# ---------------------------------------------------------------------------

class TestExecuteOne:
    def test_unknown_tool(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        out = te.execute_one(tmp_path, {"tool": "no-such-tool", "input": {}},
                             bus, mode="default")
        assert out["status"] == "error"
        assert "unknown tool" in out["result"]["error"]

    def test_acl_deny(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        out = te.execute_one(
            tmp_path,
            {"tool": "list_files", "input": {"path": "."}},
            bus, mode="default",
            profile={"tools": ["read_file"]},
        )
        assert out["status"] == "deny"
        assert "not in agent profile" in out["result"]["error"]

    def test_acl_wildcard(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        out = te.execute_one(
            tmp_path,
            {"tool": "list_files", "input": {"path": "."}},
            bus, mode="default",
            profile={"tools": ["*"]},
        )
        assert out["status"] == "ok"

    def test_pre_hook_blocks(self, tmp_path: Path,
                             monkeypatch: pytest.MonkeyPatch) -> None:
        bus = EventBus(tmp_path)
        monkeypatch.setattr(te, "run_hooks",
                            lambda *a, **kw: [{"decision": "deny"}])
        monkeypatch.setattr(te, "is_blocked", lambda hooks: True)
        out = te.execute_one(
            tmp_path,
            {"tool": "list_files", "input": {"path": "."}},
            bus, mode="default",
        )
        assert out["status"] == "blocked"

    def test_post_hook_blocks(self, tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
        bus = EventBus(tmp_path)
        # 1st run_hooks (pre) → empty; 2nd (post) → block-signal.
        calls = {"n": 0}

        def fake_hooks(*a: Any, **kw: Any) -> List[Dict[str, Any]]:
            calls["n"] += 1
            return [] if calls["n"] == 1 else [{"decision": "deny"}]

        def fake_blocked(hooks: List[Dict[str, Any]]) -> bool:
            return bool(hooks)

        monkeypatch.setattr(te, "run_hooks", fake_hooks)
        monkeypatch.setattr(te, "is_blocked", fake_blocked)
        out = te.execute_one(
            tmp_path,
            {"tool": "list_files", "input": {"path": "."}},
            bus, mode="default",
        )
        assert out["status"] == "blocked_post"

    def test_run_command_permission_deny(self, tmp_path: Path) -> None:
        bus = EventBus(tmp_path)
        out = te.execute_one(
            tmp_path,
            {"tool": "run_command", "input": {"cmd": "rm -rf /"}},
            bus, mode="default",
        )
        assert out["status"] == "deny"
        assert out["result"]["permission"]["decision"] == "deny"

    def test_run_command_allow_dispatch(self, tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch
                                         ) -> None:
        """Cycle 7 PR1 regression — `run_command` đi qua execute_one phải
        dispatch sang ``_tool_run_command`` (TRƯỚC fix bug, sẽ trả
        ``unknown tool`` vì impl is None)."""
        bus = EventBus(tmp_path)
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("ok-out", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            out = te.execute_one(
                tmp_path,
                {"tool": "run_command", "input": {"cmd": "git status"}},
                bus, mode="default",
            )
        assert out["status"] == "ok", out
        assert out["result"]["returncode"] == 0
        assert "stdout" in out["result"]
        assert mock_popen.called

    def test_run_command_dispatch_via_execute_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cycle 7 PR1 regression — execute_blocks route run_command
        sang _tool_run_command thay vì 'unknown tool'."""
        with patch("vibecodekit.tool_executor.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("hello\n", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            out = te.execute_blocks(
                tmp_path,
                blocks=[{"tool": "run_command",
                          "input": {"cmd": "echo hello"}}],
                mode="default",
            )
        assert len(out["results"]) == 1
        r = out["results"][0]
        assert r["status"] == "ok", r
        assert r["result"]["returncode"] == 0
        assert "unknown tool" not in str(r["result"])


# ---------------------------------------------------------------------------
# execute_blocks — partition + parallel + abort
# ---------------------------------------------------------------------------

class TestExecuteBlocks:
    def test_empty_blocks(self, tmp_path: Path) -> None:
        out = te.execute_blocks(tmp_path, blocks=[])
        assert out["results"] == []
        assert "session_id" in out

    def test_safe_batch_runs(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("x")
        out = te.execute_blocks(
            tmp_path,
            blocks=[
                {"tool": "list_files", "input": {"path": "."}},
                {"tool": "read_file", "input": {"path": "a.txt"}},
            ],
        )
        assert len(out["results"]) == 2

    def test_exclusive_abort_on_failure(self, tmp_path: Path) -> None:
        """Run a denied run_command (deny → status='deny') in exclusive batch
        — không abort vì returncode None.  Nhưng nếu execute_one trả status
        != ok và returncode != 0 / None thì abort.
        """
        # Tạo 2 block exclusive; cả 2 sẽ deny vì "rm -rf /".  abort logic
        # check returncode -- deny không có returncode nên không abort.
        out = te.execute_blocks(
            tmp_path,
            blocks=[
                {"tool": "run_command", "input": {"cmd": "rm -rf /"}},
                {"tool": "run_command", "input": {"cmd": "rm -rf /"}},
            ],
            mode="default",
        )
        # Cả hai deny đều có result, không abort.
        assert len(out["results"]) == 2

    def test_modifier_emitted(self, tmp_path: Path) -> None:
        out = te.execute_blocks(
            tmp_path,
            blocks=[
                {"tool": "write_file",
                 "input": {"path": "out.txt", "content": "x"}},
            ],
        )
        assert len(out["results"]) == 1
        assert (tmp_path / "out.txt").read_text() == "x"

    def test_pathlike_root(self, tmp_path: Path) -> None:
        # Test PathLike conversion.
        out = te.execute_blocks(
            str(tmp_path),
            blocks=[{"tool": "list_files", "input": {"path": "."}}],
        )
        assert "session_id" in out

    def test_exclusive_abort_on_run_command_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exclusive batch chứa run_command fail (returncode != 0) → abort
        phần còn lại của batch.  Vì partition_tool_blocks bình thường
        tách mỗi block exclusive thành batch riêng, ta force partition
        return 1 batch chứa cả 2 block để test abort path."""
        block1 = {"tool": "run_command", "input": {"cmd": "false"}}
        block2 = {"tool": "run_command", "input": {"cmd": "echo never"}}
        monkeypatch.setattr(
            te, "partition_tool_blocks",
            lambda blocks: [{"safe": False, "blocks": list(blocks)}],
        )
        calls: List[Dict[str, Any]] = []

        def fake_execute_one(root: Path, block: Dict[str, Any], *args: Any,
                             **kwargs: Any) -> Dict[str, Any]:
            calls.append(block)
            return {
                "block": block, "status": "error",
                "result": {"returncode": 1, "stdout": "", "stderr": "boom"},
                "hooks": {"pre": [], "post": []},
            }

        monkeypatch.setattr(te, "execute_one", fake_execute_one)
        out = te.execute_blocks(tmp_path, blocks=[block1, block2])
        assert len(out["results"]) == 1
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# Lazy-imported tool dispatchers (task_runtime / mcp / memory / approval)
# ---------------------------------------------------------------------------

class TestLazyImportedTools:
    def test_task_start_local_bash_deny(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path, {"kind": "local_bash", "cmd": "rm -rf /"})
        assert out["executed"] is False
        assert out["permission"]["decision"] == "deny"

    def test_task_start_local_bash_missing_cmd(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path, {"kind": "local_bash"})
        assert "error" in out

    def test_task_start_unknown_kind(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path, {"kind": "no-such-kind"})
        assert "error" in out
        assert "unsupported task kind" in out["error"]

    def test_task_start_dream(self, tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
        from vibecodekit import task_runtime
        fake_task = MagicMock(task_id="t1", kind="dream",
                              status="running", output_file="x")
        monkeypatch.setattr(task_runtime, "start_dream",
                            lambda root: fake_task)
        out = te._tool_task_start(tmp_path, {"kind": "dream"})
        assert out["task_id"] == "t1"

    def test_task_start_local_agent_missing_args(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path, {"kind": "local_agent"})
        assert "error" in out

    def test_task_start_local_agent_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        fake_task = MagicMock(task_id="t2", kind="local_agent",
                              status="running", output_file="x")
        monkeypatch.setattr(task_runtime, "start_local_agent",
                            lambda *a, **kw: fake_task)
        out = te._tool_task_start(
            tmp_path,
            {"kind": "local_agent", "role": "qa", "objective": "test"},
        )
        assert out["task_id"] == "t2"

    def test_task_start_local_workflow_empty(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path,
                                   {"kind": "local_workflow", "steps": []})
        assert "error" in out

    def test_task_start_local_workflow_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        fake = MagicMock(task_id="t3", kind="local_workflow",
                         status="running", output_file="x")
        monkeypatch.setattr(task_runtime, "start_local_workflow",
                            lambda *a, **kw: fake)
        out = te._tool_task_start(tmp_path,
                                   {"kind": "local_workflow", "steps": ["echo"]})
        assert out["task_id"] == "t3"

    def test_task_start_monitor_mcp_missing_server(self, tmp_path: Path) -> None:
        out = te._tool_task_start(tmp_path, {"kind": "monitor_mcp"})
        assert "error" in out

    def test_task_start_monitor_mcp_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        fake = MagicMock(task_id="t4", kind="monitor_mcp",
                         status="running", output_file="x")
        monkeypatch.setattr(task_runtime, "start_monitor_mcp",
                            lambda *a, **kw: fake)
        out = te._tool_task_start(tmp_path,
                                   {"kind": "monitor_mcp", "server": "s1"})
        assert out["task_id"] == "t4"

    def test_task_status_specific(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "get_task",
                            lambda root, tid: {"task_id": tid})
        out = te._tool_task_status(tmp_path, {"task_id": "abc"})
        assert out["task"]["task_id"] == "abc"

    def test_task_status_unknown(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "get_task", lambda root, tid: None)
        out = te._tool_task_status(tmp_path, {"task_id": "missing"})
        assert "error" in out

    def test_task_status_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "list_tasks",
                            lambda root, only=None: [{"id": "x"}])
        out = te._tool_task_status(tmp_path, {})
        assert out["tasks"] == [{"id": "x"}]

    def test_task_read_missing_id(self, tmp_path: Path) -> None:
        out = te._tool_task_read(tmp_path, {})
        assert "error" in out

    def test_task_read_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "read_task_output",
                            lambda *a, **kw: {"content": "hi"})
        out = te._tool_task_read(tmp_path, {"task_id": "t"})
        assert out == {"content": "hi"}

    def test_task_kill_missing_id(self, tmp_path: Path) -> None:
        out = te._tool_task_kill(tmp_path, {})
        assert "error" in out

    def test_task_kill_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "kill_task",
                            lambda root, tid: True)
        out = te._tool_task_kill(tmp_path, {"task_id": "t"})
        assert out == {"killed": True}

    def test_task_notifications_missing_id(self, tmp_path: Path) -> None:
        out = te._tool_task_notifications(tmp_path, {})
        assert "error" in out

    def test_task_notifications_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import task_runtime
        monkeypatch.setattr(task_runtime, "drain_notifications",
                            lambda root, tid: ["n1"])
        out = te._tool_task_notifications(tmp_path, {"task_id": "t"})
        assert out == {"notifications": ["n1"]}

    def test_mcp_list(self, tmp_path: Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
        from vibecodekit import mcp_client
        monkeypatch.setattr(mcp_client, "list_servers",
                            lambda root: [{"name": "s1"}])
        out = te._tool_mcp_list(tmp_path, {})
        assert out == {"servers": [{"name": "s1"}]}

    def test_mcp_call_missing_args(self, tmp_path: Path) -> None:
        out = te._tool_mcp_call(tmp_path, {"server": "s1"})
        assert "error" in out
        out2 = te._tool_mcp_call(tmp_path, {"tool": "t"})
        assert "error" in out2

    def test_mcp_call_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import mcp_client
        monkeypatch.setattr(mcp_client, "call_tool",
                            lambda *a, **kw: {"result": "ok"})
        out = te._tool_mcp_call(tmp_path,
                                 {"server": "s1", "tool": "ping"})
        assert out == {"result": "ok"}

    def test_memory_retrieve_missing_query(self, tmp_path: Path) -> None:
        out = te._tool_memory_retrieve(tmp_path, {})
        assert "error" in out

    def test_memory_retrieve_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import memory_hierarchy
        monkeypatch.setattr(memory_hierarchy, "retrieve",
                            lambda *a, **kw: ["entry"])
        out = te._tool_memory_retrieve(tmp_path, {"query": "x"})
        assert out == {"results": ["entry"]}

    def test_memory_add_missing_text(self, tmp_path: Path) -> None:
        out = te._tool_memory_add(tmp_path, {})
        assert "error" in out

    def test_memory_add_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import memory_hierarchy
        monkeypatch.setattr(memory_hierarchy, "add_entry",
                            lambda *a, **kw: {"added": True})
        out = te._tool_memory_add(tmp_path, {"text": "hello"})
        assert out == {"added": True}

    def test_memory_stats(self, tmp_path: Path,
                          monkeypatch: pytest.MonkeyPatch) -> None:
        from vibecodekit import memory_hierarchy
        monkeypatch.setattr(memory_hierarchy, "tier_stats",
                            lambda root: {"project": 5})
        out = te._tool_memory_stats(tmp_path, {})
        assert out == {"stats": {"project": 5}}

    def test_approval_create(self, tmp_path: Path,
                             monkeypatch: pytest.MonkeyPatch) -> None:
        from vibecodekit import approval_contract
        monkeypatch.setattr(approval_contract, "create",
                            lambda root, **kw: {"id": "a1"})
        out = te._tool_approval_create(tmp_path, {})
        assert out == {"id": "a1"}

    def test_approval_list(self, tmp_path: Path,
                           monkeypatch: pytest.MonkeyPatch) -> None:
        from vibecodekit import approval_contract
        monkeypatch.setattr(approval_contract, "list_pending",
                            lambda root: [{"id": "a1"}])
        out = te._tool_approval_list(tmp_path, {})
        assert out == {"pending": [{"id": "a1"}]}

    def test_approval_respond_missing_args(self, tmp_path: Path) -> None:
        out = te._tool_approval_respond(tmp_path, {})
        assert "error" in out

    def test_approval_respond_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from vibecodekit import approval_contract
        monkeypatch.setattr(approval_contract, "respond",
                            lambda *a, **kw: {"ok": True})
        out = te._tool_approval_respond(
            tmp_path, {"approval_id": "a1", "choice": "approve"},
        )
        assert out == {"ok": True}


# ---------------------------------------------------------------------------
# CLI _main
# ---------------------------------------------------------------------------

class TestCli:
    def test_main_executes_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        plan = tmp_path / "plan.json"
        plan.write_text('{"steps": [{"tool":"list_files","input":{"path":"."}}]}')
        monkeypatch.setattr(
            sys, "argv",
            ["tool_executor", str(plan), "--root", str(tmp_path)],
        )
        te._main()
        out = capsys.readouterr().out
        assert "session_id" in out
        assert "result_count" in out
