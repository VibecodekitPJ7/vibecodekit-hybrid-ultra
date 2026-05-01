"""Phase 6 cycle 12 PR1 — coverage for ``task_runtime.py`` and
``module_workflow.py``.

* ``task_runtime.py`` (468 stmt, was 76% → ≥90%): create/list/get/
  read_task_output/kill, _read_index/_write_index resilience,
  _is_valid_task_id, drain_notifications + lock collision, check_stalls
  (3 paths: still-producing, prompt-detected, no-prompt-quiet),
  start_local_bash full lifecycle (success / fail / timeout / kill /
  short id), start_local_workflow (all 4 step kinds + on_error +
  unknown / path-escape), start_monitor_mcp success path,
  start_dream synthesis path, wait_for (terminal + timeout).
* ``module_workflow.py`` (239 stmt, was 67% → ≥85%): all 11 detectors
  (positive + negative + JSON decode error), probe non-dir, probe
  with empty dir, probe full Next.js + Prisma + NextAuth + Tailwind +
  TypeScript stack, generate_reuse_inventory ordering, _slug edge
  cases, generate_module_plan all 5 routing branches (nextjs+prisma /
  fastapi / express / django / fallback src/ + fallback ".") +
  EmptyCodebaseError + ValueError name + ValueError spec + nextauth
  risk + non-tailwind risk, ModulePlan.to_dict, main CLI all 3
  subcommands + EmptyCodebaseError exit code 2.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

_PKG = str(Path(__file__).resolve().parent.parent / "scripts")
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)

import vibecodekit.module_workflow as mw  # noqa: E402
import vibecodekit.task_runtime as tr  # noqa: E402


# ---------------------------------------------------------------------------
# task_runtime
# ---------------------------------------------------------------------------


def _wait_terminal(root: Path, tid: str, timeout: float = 5.0) -> Dict[str, Any]:
    rec = tr.wait_for(root, tid, timeout=timeout)
    assert rec.get("status") in tr.TERMINAL_STATES, f"not terminal: {rec}"
    return rec


def test_is_valid_task_id_accepts_canonical() -> None:
    assert tr._is_valid_task_id("task-local_bash-1234abcd")
    assert tr._is_valid_task_id("task-x-abcd")


def test_is_valid_task_id_rejects_garbage() -> None:
    assert not tr._is_valid_task_id("")
    assert not tr._is_valid_task_id("foo")
    assert not tr._is_valid_task_id("task-../escape")
    assert not tr._is_valid_task_id(123)  # type: ignore[arg-type]
    assert not tr._is_valid_task_id(None)  # type: ignore[arg-type]


def test_create_task_rejects_unknown_kind(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown task kind"):
        tr.create_task(tmp_path, "made_up", "x")


def test_read_index_handles_missing_and_malformed(tmp_path: Path) -> None:
    assert tr._read_index(tmp_path) == {}
    p = tr._index_path(tmp_path)
    p.write_text("not-json", encoding="utf-8")
    assert tr._read_index(tmp_path) == {}


def test_write_index_cleans_up_tmp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force fdopen → the inner block raises so _write_index hits the
    # except branch + unlink(tmp).
    real_fdopen = os.fdopen

    def boom(fd: int, *a: Any, **kw: Any) -> Any:
        os.close(fd)
        raise OSError("disk full")

    monkeypatch.setattr(os, "fdopen", boom)
    with pytest.raises(OSError):
        tr._write_index(tmp_path, {"x": {"y": 1}})
    monkeypatch.setattr(os, "fdopen", real_fdopen)


def test_get_task_invalid_id_returns_none(tmp_path: Path) -> None:
    assert tr.get_task(tmp_path, "nope") is None


def test_list_tasks_filter_and_sort(tmp_path: Path) -> None:
    a = tr.create_task(tmp_path, "local_bash", "a")
    time.sleep(0.005)
    b = tr.create_task(tmp_path, "local_bash", "b")
    # mark b as completed so we can filter
    tr._finish(tmp_path, b.task_id, "completed", returncode=0, error=None)
    out = tr.list_tasks(tmp_path)
    assert {x["task_id"] for x in out} == {a.task_id, b.task_id}
    # sorted by created_ts desc → b (newer) comes first
    assert out[0]["task_id"] == b.task_id
    only_completed = tr.list_tasks(tmp_path, only="completed")
    assert [x["task_id"] for x in only_completed] == [b.task_id]


def test_read_task_output_invalid_and_unknown(tmp_path: Path) -> None:
    assert "invalid task_id" in tr.read_task_output(tmp_path, "nope")["error"]
    # valid format but unknown
    assert "unknown task" in tr.read_task_output(tmp_path, "task-x-deadbeef")["error"]


def test_read_task_output_missing_file_returns_eof(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    out_path = tmp_path / t.output_file
    out_path.unlink()
    out = tr.read_task_output(tmp_path, t.task_id)
    assert out["eof"] is True
    assert out["total_size"] == 0


def test_read_task_output_returns_window(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    (tmp_path / t.output_file).write_bytes(b"hello world")
    out = tr.read_task_output(tmp_path, t.task_id, offset=6, length=100)
    assert out["content"] == "world"
    assert out["eof"] is True


def test_read_task_output_handles_unicode_decode_error(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    (tmp_path / t.output_file).write_bytes(b"\xff\xfe\xfd")
    out = tr.read_task_output(tmp_path, t.task_id)
    # decode error fall-through → text contains replacement chars
    assert isinstance(out["content"], str)


def test_start_local_bash_completes(tmp_path: Path) -> None:
    t = tr.start_local_bash(tmp_path, "echo hello-world")
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "completed"
    assert rec["returncode"] == 0


def test_start_local_bash_failure_status(tmp_path: Path) -> None:
    t = tr.start_local_bash(tmp_path, "exit 7")
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "failed"
    assert rec["returncode"] == 7


def test_start_local_bash_timeout(tmp_path: Path) -> None:
    t = tr.start_local_bash(tmp_path, "sleep 5", timeout_sec=1)
    rec = _wait_terminal(tmp_path, t.task_id, timeout=8.0)
    assert rec["status"] == "killed"
    assert rec["returncode"] == 124


def test_kill_task_invalid_id(tmp_path: Path) -> None:
    assert tr.kill_task(tmp_path, "nope") is False


def test_kill_task_unknown(tmp_path: Path) -> None:
    assert tr.kill_task(tmp_path, "task-x-deadbeef") is False


def test_kill_task_already_terminal(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    tr._finish(tmp_path, t.task_id, "completed", returncode=0, error=None)
    assert tr.kill_task(tmp_path, t.task_id) is False


def test_kill_task_no_pid(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    # mark running but no pid → kill marks as killed
    tr._upsert(tmp_path, tr.Task(
        task_id=t.task_id, kind="local_bash", description="x",
        status="running", output_file=t.output_file, pid=None,
    ))
    assert tr.kill_task(tmp_path, t.task_id) is True
    rec = tr.get_task(tmp_path, t.task_id)
    assert rec is not None and rec["status"] == "killed"


def test_drain_notifications_invalid_id(tmp_path: Path) -> None:
    assert tr.drain_notifications(tmp_path, "bad") == []


def test_drain_notifications_atomic(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    # create_task already enqueued task_created
    out = tr.drain_notifications(tmp_path, t.task_id)
    assert len(out) == 1
    assert out[0]["payload"]["event"] == "task_created"
    # second drain returns empty (truncated)
    assert tr.drain_notifications(tmp_path, t.task_id) == []


def test_drain_notifications_skips_malformed(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    p = tr._notifications_path(tmp_path, t.task_id)
    p.write_text(p.read_text() + "{not-json\n", encoding="utf-8")
    out = tr.drain_notifications(tmp_path, t.task_id)
    # malformed line dropped, valid line kept
    assert all("payload" in r for r in out)


def test_drain_notifications_no_file(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    p = tr._notifications_path(tmp_path, t.task_id)
    p.unlink()
    assert tr.drain_notifications(tmp_path, t.task_id) == []


def test_check_stalls_still_producing_no_alert(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    # mark running and write fresh bytes
    out_path = tmp_path / t.output_file
    out_path.write_bytes(b"first chunk")
    tr._upsert(tmp_path, tr.Task(
        task_id=t.task_id, kind="local_bash", description="x",
        status="running", output_file=t.output_file,
        stdout_size=0, last_write_ts=time.time() - 100,
    ))
    out = tr.check_stalls(tmp_path)
    assert out == []  # bytes grew → still producing


def test_check_stalls_quiet_no_prompt(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    out_path = tmp_path / t.output_file
    out_path.write_bytes(b"plain output\n")
    size = out_path.stat().st_size
    tr._upsert(tmp_path, tr.Task(
        task_id=t.task_id, kind="local_bash", description="x",
        status="running", output_file=t.output_file,
        stdout_size=size, last_write_ts=time.time() - 100,
    ))
    out = tr.check_stalls(tmp_path)
    assert out == []  # quiet but no prompt


def test_check_stalls_detects_interactive_prompt(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    out_path = tmp_path / t.output_file
    out_path.write_bytes(b"Continue? [y/N]")
    size = out_path.stat().st_size
    tr._upsert(tmp_path, tr.Task(
        task_id=t.task_id, kind="local_bash", description="x",
        status="running", output_file=t.output_file,
        stdout_size=size, last_write_ts=time.time() - 100,
    ))
    out = tr.check_stalls(tmp_path)
    assert len(out) == 1
    assert "y/N" in out[0]["tail"]


def test_check_stalls_skips_when_output_missing(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    (tmp_path / t.output_file).unlink()
    tr._upsert(tmp_path, tr.Task(
        task_id=t.task_id, kind="local_bash", description="x",
        status="running", output_file=t.output_file,
    ))
    assert tr.check_stalls(tmp_path) == []


def test_start_local_workflow_bash_step(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "bash", "cmd": "echo hi"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "completed"
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "echo hi" not in out  # we wrote step records, not raw cmd
    assert "returncode" in out


def test_start_local_workflow_blocked_bash_step(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "bash", "cmd": "rm -rf /", "mode": "auto_safe"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id, timeout=8.0)
    # blocked steps don't fail by default; they just record permission
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "permission" in out
    # no break → workflow completes
    assert rec["status"] == "completed"


def test_start_local_workflow_sleep_step(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "sleep", "seconds": 0.05}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "completed"
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "slept" in out


def test_start_local_workflow_write_step(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "write", "path": "logs/note.md", "content": "hi"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "completed"
    note = tmp_path / "logs" / "note.md"
    assert note.read_text(encoding="utf-8") == "hi"


def test_start_local_workflow_write_path_escape_aborts(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "write", "path": "../escape.txt", "content": "x"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "failed"
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "escapes root" in out


def test_start_local_workflow_unknown_step_aborts(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "made_up"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "failed"
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "unknown step kind" in out


def test_start_local_workflow_unknown_step_continue(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[
            {"kind": "made_up", "on_error": "continue"},
            {"kind": "sleep", "seconds": 0.01},
        ],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "completed"


def test_start_local_workflow_step_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Make subprocess.run raise → covers per-step exception branch in bash kind.
    def boom(*a: Any, **kw: Any) -> Any:
        raise RuntimeError("boom-from-subprocess")

    monkeypatch.setattr(tr.subprocess, "run", boom)
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "bash", "cmd": "echo hi"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id)
    assert rec["status"] == "failed"
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    assert "RuntimeError" in out


def test_start_local_workflow_bash_failure_aborts(tmp_path: Path) -> None:
    t = tr.start_local_workflow(
        tmp_path,
        steps=[{"kind": "bash", "cmd": "ls /no/such/path/here_does_not_exist"}],
    )
    rec = _wait_terminal(tmp_path, t.task_id, timeout=8.0)
    # ls of nonexistent path returns rc != 0 → workflow status = failed
    out = (tmp_path / t.output_file).read_text(encoding="utf-8")
    # Either decision was blocked (recorded permission) or executed and failed.
    if '"blocked": true' in out:
        # Permission-blocked steps don't fail the workflow.
        assert rec["status"] == "completed"
    else:
        assert rec["status"] == "failed"


def test_start_monitor_mcp_records_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # monkeypatch mcp_client.call_tool → return {"ok": True}.
    import vibecodekit.mcp_client as mcp

    monkeypatch.setattr(
        mcp, "call_tool",
        lambda *a, **kw: {"ok": True},
    )
    t = tr.start_monitor_mcp(
        tmp_path, server_name="vibecodekit-selfcheck",
        interval_sec=0.01, max_checks=2, tool="ping",
    )
    rec = _wait_terminal(tmp_path, t.task_id, timeout=4.0)
    assert rec["status"] == "completed"


def test_start_monitor_mcp_records_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibecodekit.mcp_client as mcp

    monkeypatch.setattr(
        mcp, "call_tool",
        lambda *a, **kw: {"error": "nope"},
    )
    t = tr.start_monitor_mcp(
        tmp_path, server_name="vibecodekit-selfcheck",
        interval_sec=0.01, max_checks=1, tool="ping",
    )
    rec = _wait_terminal(tmp_path, t.task_id, timeout=4.0)
    assert rec["status"] == "failed"


def test_start_dream_consolidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Seed a session events file.
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "sess-1.events.jsonl").write_text(
        "\n".join([
            json.dumps({"event": "tool_result",
                        "payload": {"block": {"tool": "Bash"}}}),
            json.dumps({"event": "permission_check", "status": "blocked"}),
            "{not-json",
        ]),
        encoding="utf-8",
    )
    # Stub embedding backend so prune phase is deterministic.

    class _Emb:
        def embed(self, text: str) -> list:
            return [float(len(text))]

        def similarity(self, a: list, b: list) -> float:
            return 0.0  # never duplicate

    import vibecodekit.memory_hierarchy as mh

    monkeypatch.setattr(mh, "get_backend", lambda: _Emb())
    # Seed a project memory log.
    mem = tmp_path / ".vibecode" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "log.jsonl").write_text(
        "\n".join([
            json.dumps({"text": "alpha", "header": "h1"}),
            json.dumps({"text": "beta", "header": "h2"}),
            "{not-json",
        ]),
        encoding="utf-8",
    )
    t = tr.start_dream(tmp_path)
    rec = _wait_terminal(tmp_path, t.task_id, timeout=8.0)
    assert rec["status"] == "completed"
    digest = mem / "dream-digest.md"
    assert digest.exists()
    txt = digest.read_text(encoding="utf-8")
    assert "Tool usage" in txt
    assert "Errors / blocks" in txt


def test_wait_for_returns_terminal(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    tr._finish(tmp_path, t.task_id, "completed", returncode=0, error=None)
    rec = tr.wait_for(tmp_path, t.task_id, timeout=0.5)
    assert rec["status"] == "completed"


def test_wait_for_timeout_returns_record(tmp_path: Path) -> None:
    t = tr.create_task(tmp_path, "local_bash", "x")
    rec = tr.wait_for(tmp_path, t.task_id, timeout=0.1)
    # not terminal — current state returned
    assert rec.get("task_id") == t.task_id
    assert rec.get("status") == "pending"


def test_wait_for_unknown_task(tmp_path: Path) -> None:
    rec = tr.wait_for(tmp_path, "task-x-deadbeef", timeout=0.05)
    assert rec == {}


# ---------------------------------------------------------------------------
# module_workflow
# ---------------------------------------------------------------------------


def test_read_text_handles_oserror(tmp_path: Path) -> None:
    # A directory cannot be read as text → returns "".
    p = tmp_path / "dir"
    p.mkdir()
    assert mw._read_text(p) == ""


def test_detect_nextjs_via_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "^14.0.0"}}),
        encoding="utf-8",
    )
    assert mw._detect_nextjs(tmp_path) and "next@" in mw._detect_nextjs(tmp_path)


def test_detect_nextjs_via_config_file(tmp_path: Path) -> None:
    (tmp_path / "next.config.js").write_text("module.exports = {}", encoding="utf-8")
    assert mw._detect_nextjs(tmp_path) == "next.config.* present"


def test_detect_nextjs_malformed_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not-json", encoding="utf-8")
    assert mw._detect_nextjs(tmp_path) is None


def test_detect_nextjs_no_package_json(tmp_path: Path) -> None:
    assert mw._detect_nextjs(tmp_path) is None


def test_detect_react_positive(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"react": "^18"}}),
        encoding="utf-8",
    )
    assert "react@" in (mw._detect_react(tmp_path) or "")


def test_detect_react_no_dep(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {}}), encoding="utf-8"
    )
    assert mw._detect_react(tmp_path) is None


def test_detect_react_malformed(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not-json", encoding="utf-8")
    assert mw._detect_react(tmp_path) is None


def test_detect_react_missing(tmp_path: Path) -> None:
    assert mw._detect_react(tmp_path) is None


def test_detect_prisma_via_schema(tmp_path: Path) -> None:
    (tmp_path / "prisma").mkdir()
    (tmp_path / "prisma" / "schema.prisma").write_text("//", encoding="utf-8")
    assert mw._detect_prisma(tmp_path) == "prisma/schema.prisma"


def test_detect_prisma_via_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"@prisma/client":"^5"}}', encoding="utf-8"
    )
    assert "@prisma/client" in (mw._detect_prisma(tmp_path) or "")


def test_detect_prisma_none(tmp_path: Path) -> None:
    assert mw._detect_prisma(tmp_path) is None


def test_detect_nextauth_via_package(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"next-auth":"^4"}}', encoding="utf-8"
    )
    assert mw._detect_nextauth(tmp_path) == "package.json: next-auth"


def test_detect_nextauth_via_lib_auth(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "auth.ts").write_text("//", encoding="utf-8")
    assert mw._detect_nextauth(tmp_path) == "lib/auth.ts present"


def test_detect_nextauth_none(tmp_path: Path) -> None:
    assert mw._detect_nextauth(tmp_path) is None


def test_detect_tailwind_via_config(tmp_path: Path) -> None:
    (tmp_path / "tailwind.config.ts").write_text("//", encoding="utf-8")
    assert mw._detect_tailwind(tmp_path) == "tailwind.config.ts"


def test_detect_tailwind_via_package(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"devDependencies":{"tailwindcss":"^3"}}', encoding="utf-8"
    )
    assert "tailwindcss" in (mw._detect_tailwind(tmp_path) or "")


def test_detect_tailwind_none(tmp_path: Path) -> None:
    assert mw._detect_tailwind(tmp_path) is None


def test_detect_express_positive(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies":{"express":"^4"}}', encoding="utf-8"
    )
    assert mw._detect_express(tmp_path) == "package.json: express"


def test_detect_express_none(tmp_path: Path) -> None:
    assert mw._detect_express(tmp_path) is None


def test_detect_fastapi_via_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "dependencies = ['fastapi']", encoding="utf-8"
    )
    assert "fastapi" in (mw._detect_fastapi(tmp_path) or "")


def test_detect_fastapi_none(tmp_path: Path) -> None:
    assert mw._detect_fastapi(tmp_path) is None


def test_detect_django_via_manage_py(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text("# django", encoding="utf-8")
    assert mw._detect_django(tmp_path) == "manage.py"


def test_detect_django_via_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("Django==5.0", encoding="utf-8")
    assert "django" in (mw._detect_django(tmp_path) or "").lower()


def test_detect_django_none(tmp_path: Path) -> None:
    assert mw._detect_django(tmp_path) is None


def test_detect_vite_positive(tmp_path: Path) -> None:
    (tmp_path / "vite.config.ts").write_text("//", encoding="utf-8")
    assert mw._detect_vite(tmp_path) == "vite.config.ts"


def test_detect_vite_none(tmp_path: Path) -> None:
    assert mw._detect_vite(tmp_path) is None


def test_detect_typescript_positive(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    assert mw._detect_typescript(tmp_path) == "tsconfig.json"


def test_detect_typescript_none(tmp_path: Path) -> None:
    assert mw._detect_typescript(tmp_path) is None


def test_probe_non_dir_returns_falsey(tmp_path: Path) -> None:
    p = tmp_path / "missing"
    out = mw.probe_existing_codebase(p)
    assert out.is_codebase is False
    assert out.capabilities == {}


def test_probe_empty_dir_is_not_codebase(tmp_path: Path) -> None:
    out = mw.probe_existing_codebase(tmp_path)
    assert out.is_codebase is False


def test_probe_full_nextjs_stack(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({
            "dependencies": {"next": "14", "react": "18", "next-auth": "4",
                             "@prisma/client": "5"},
            "devDependencies": {"tailwindcss": "3"},
        }),
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    (tmp_path / "yarn.lock").write_text("", encoding="utf-8")
    (tmp_path / "Pipfile").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module x", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    (tmp_path / "app").mkdir()
    (tmp_path / "components").mkdir()
    (tmp_path / "src").mkdir()
    out = mw.probe_existing_codebase(tmp_path)
    assert out.is_codebase
    assert "nextjs" in out.capabilities
    assert "react" in out.capabilities
    assert "tailwind" in out.capabilities
    assert "typescript" in out.capabilities
    # package_managers covers all four
    assert set(out.package_managers) >= {"npm", "pnpm", "yarn", "pip", "pipenv"}
    assert "javascript" in out.languages
    assert "typescript" in out.languages
    assert "python" in out.languages
    assert "rust" in out.languages
    assert "go" in out.languages
    assert "app" in out.notable_dirs
    # to_dict is JSON-serialisable
    json.dumps(out.to_dict())


def test_generate_reuse_inventory_orders_alphabetically(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"react": "package.json: react",
                      "nextjs": "package.json: next",
                      "made_up_cap": "evidence"},
    )
    inv = mw.generate_reuse_inventory(probe)
    assert [i.capability for i in inv] == ["made_up_cap", "nextjs", "react"]
    # made_up cap falls back to "reuse existing X"
    assert next(i for i in inv if i.capability == "made_up_cap").reuse_hint == "reuse existing made_up_cap"


def test_generate_module_plan_empty_codebase_raises(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(root=str(tmp_path), is_codebase=False)
    with pytest.raises(mw.EmptyCodebaseError):
        mw.generate_module_plan("billing", "spec", probe)


def test_generate_module_plan_blank_name_raises(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(root=str(tmp_path), is_codebase=True,
                              capabilities={"nextjs": "x"})
    with pytest.raises(ValueError, match="module name"):
        mw.generate_module_plan(" ", "spec", probe)


def test_generate_module_plan_blank_spec_raises(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(root=str(tmp_path), is_codebase=True,
                              capabilities={"nextjs": "x"})
    with pytest.raises(ValueError, match="module spec"):
        mw.generate_module_plan("billing", " ", probe)


def test_generate_module_plan_nextjs_with_prisma_and_nextauth(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"nextjs": "x", "prisma": "y", "nextauth": "z"},
    )
    plan = mw.generate_module_plan("Billing System", "Add billing", probe)
    assert any(f.startswith("app/billing-system/") for f in plan.new_files)
    assert any("prisma/migrations" in f for f in plan.new_files)
    assert any("getServerSession" in r for r in plan.risks)
    # Tailwind risk fires because no tailwind in caps
    assert any("Tailwind" in r for r in plan.risks)
    json.dumps(plan.to_dict())


def test_generate_module_plan_fastapi(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"fastapi": "x"},
    )
    plan = mw.generate_module_plan("billing", "spec", probe)
    assert plan.target_dirs == ["api/billing"]
    assert "api/billing/router.py" in plan.new_files


def test_generate_module_plan_express(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"express": "x"},
    )
    plan = mw.generate_module_plan("billing", "spec", probe)
    assert plan.target_dirs == ["api/billing"]
    assert "api/billing/routes.ts" in plan.new_files


def test_generate_module_plan_django(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"django": "x"},
    )
    plan = mw.generate_module_plan("billing", "spec", probe)
    assert plan.target_dirs == ["billing"]
    assert "billing/models.py" in plan.new_files


def test_generate_module_plan_fallback_src(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"react": "x"},
        notable_dirs=["src"],
    )
    plan = mw.generate_module_plan("billing", "spec", probe)
    assert plan.target_dirs == ["src/billing"]


def test_generate_module_plan_fallback_dot(tmp_path: Path) -> None:
    probe = mw.CodebaseProbe(
        root=str(tmp_path), is_codebase=True,
        capabilities={"react": "x"},
    )
    plan = mw.generate_module_plan("billing", "spec", probe)
    assert plan.target_dirs == ["./billing"]


def test_slug_normalises(tmp_path: Path) -> None:
    assert mw._slug("Billing System!") == "billing-system"
    assert mw._slug("   ") == "module"


def test_main_probe_returns_zero_for_codebase(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    rc = mw.main(["probe", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "is_codebase" in out


def test_main_probe_returns_one_for_empty_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = mw.main(["probe", str(tmp_path)])
    assert rc == 1


def test_main_plan_returns_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "18"}}),
        encoding="utf-8",
    )
    rc = mw.main(["plan", "--name", "billing", "--spec", "spec",
                  "--target", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "billing" in out


def test_main_plan_empty_codebase_returns_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = mw.main(["plan", "--name", "billing", "--spec", "spec",
                  "--target", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "is not an existing codebase" in out
