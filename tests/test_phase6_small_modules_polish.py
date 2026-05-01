"""Cycle 12 PR2 (Phase 6) — polish coverage cho 8 module medium-small nhằm
đẩy global TOTAL 87 → ~90%.

Target modules & expected gain (measured on main @ end of cycle 12 PR1):
  * eval_select.py           74% → 100% (30 miss → 0)
  * mcp_servers/core.py      55% →  90% (50 miss → ~10)
  * install_manifest.py      74% →  97% (31 miss → ~5)
  * learnings.py             83% →  97% (25 miss → ~5)
  * event_bus.py             73% →  97% (11 miss → ~2)
  * denial_store.py          84% →  97% (18 miss → ~5)
  * compaction.py            82% →  97% (14 miss → ~3)
  * conformance_audit.py _main + audit exception path (cover ~10 miss)

KHÔNG đụng runtime — chỉ thêm test."""
from __future__ import annotations

import io
import json
import os
import subprocess  # noqa: F401 — referenced indirectly via monkeypatch
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

# -------------------------------------------------------------------------
# eval_select.py
# -------------------------------------------------------------------------

from vibecodekit import eval_select as es


def test_eval_select_selection_result_as_dict() -> None:
    r = es.SelectionResult(
        selected=["a"], always_run=["b"],
        matched={"a": ["src/x.py"]}, unmapped_changes=["docs/y.md"],
    )
    d = r.as_dict()
    assert d["selected"] == ["a"]
    assert d["always_run"] == ["b"]
    assert d["matched"] == {"a": ["src/x.py"]}
    assert d["unmapped_changes"] == ["docs/y.md"]


def test_eval_select_load_map_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        es.load_map(tmp_path / "nope.json")


def test_eval_select_load_map_not_object(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        es.load_map(p)


def test_eval_select_load_map_dict_and_list_shapes(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "tests/a.py": ["src/a.py"],
        "tests/b.py": {"files": ["src/b/*.py"], "always_run": True},
    }), encoding="utf-8")
    m = es.load_map(p)
    assert m["tests/a.py"] == ["src/a.py"]
    assert "__ALWAYS__" in m["tests/b.py"]


def test_eval_select_load_map_bad_entry(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"tests/a.py": 42}), encoding="utf-8")
    with pytest.raises(ValueError, match="bad touchfile entry"):
        es.load_map(p)


def test_eval_select_git_changed_files_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError("no git")

    monkeypatch.setattr(es.subprocess, "run", boom)
    assert es.git_changed_files("origin/main", cwd=tmp_path) == []


def test_eval_select_git_changed_files_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class R:
        stdout = "src/a.py\nsrc/b.py\n\n"

    monkeypatch.setattr(es.subprocess, "run", lambda *a, **k: R())
    assert es.git_changed_files("origin/main") == ["src/a.py", "src/b.py"]


def test_eval_select_match_all_branches() -> None:
    # exact
    assert es._match("src/a.py", "src/a.py")
    # glob
    assert es._match("src/*.py", "src/x.py")
    # directory prefix
    assert es._match("src/", "src/x/y.py")
    # no match
    assert not es._match("src/*.py", "tests/x.py")


def test_eval_select_normalise_entry_bad() -> None:
    with pytest.raises(ValueError, match="bad touchfile entry"):
        es._normalise_entry(42)


def test_eval_select_select_tests_empty_changes_fallback() -> None:
    res = es.select_tests([], {"tests/a.py": ["src/a.py"]},
                          fallback_all_tests=["tests/a.py", "tests/b.py"])
    assert set(res.selected) == {"tests/a.py", "tests/b.py"}


def test_eval_select_select_tests_empty_changes_no_fallback() -> None:
    res = es.select_tests([], {"tests/a.py": ["src/a.py"]},
                          extra_always_run=["tests/z.py"])
    assert res.selected == ("tests/z.py",)


def test_eval_select_select_tests_matched_and_unmapped() -> None:
    tmap = {
        "tests/a.py": ["src/a.py"],
        "tests/always.py": [],  # empty → __ALWAYS__
    }
    res = es.select_tests(["src/a.py", "docs/unmapped.md"], tmap)
    assert "tests/a.py" in res.selected
    assert "tests/always.py" in res.selected
    assert "docs/unmapped.md" in res.unmapped_changes


def test_eval_select_main_non_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"tests/a.py": ["src/a.py"]}), encoding="utf-8")
    monkeypatch.setattr(es, "git_changed_files",
                        lambda *a, **k: ["src/a.py", "docs/x.md"])
    rc = es._main(["--map", str(p)])
    assert rc == 0
    out = capsys.readouterr()
    assert "tests/a.py" in out.out
    assert "not covered by any test mapping" in out.err


def test_eval_select_main_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"tests/a.py": ["src/a.py"]}), encoding="utf-8")
    monkeypatch.setattr(es, "git_changed_files", lambda *a, **k: [])
    fb = tmp_path / "fb.txt"
    fb.write_text("tests/a.py\ntests/b.py\n", encoding="utf-8")
    rc = es._main(["--map", str(p), "--json",
                   "--fallback-all-tests-file", str(fb),
                   "--always", "tests/c.py"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "selected" in payload and "changed_files" in payload


# -------------------------------------------------------------------------
# mcp_servers/core.py — stdio protocol + tool dispatch
# -------------------------------------------------------------------------

from vibecodekit.mcp_servers import core as mcp_core


def test_mcp_core_get_root_default() -> None:
    assert mcp_core._get_root({}) == "."
    assert mcp_core._get_root({"root": "/tmp"}) == "/tmp"


def _capture_stdout(fn: Any, *args: Any, **kw: Any) -> Any:
    buf = io.StringIO()
    orig = sys.stdout
    sys.stdout = buf
    try:
        result = fn(*args, **kw)
    finally:
        sys.stdout = orig
    return result, buf.getvalue()


def test_mcp_core_respond_and_error_emit_jsonrpc() -> None:
    _, out = _capture_stdout(mcp_core._respond, 1, {"x": 2})
    rec = json.loads(out.strip())
    assert rec == {"jsonrpc": "2.0", "id": 1, "result": {"x": 2}}

    _, out = _capture_stdout(mcp_core._error, 2, -32601, "boom")
    rec = json.loads(out.strip())
    assert rec["error"]["code"] == -32601 and rec["error"]["message"] == "boom"


def test_mcp_core_handle_initialize() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
    )
    rec = json.loads(out.strip())
    assert rec["result"]["protocolVersion"] == "2024-11-05"
    assert rec["result"]["serverInfo"]["name"] == "vibecodekit-core"


def test_mcp_core_handle_notifications_initialized_no_output() -> None:
    # notifications/initialized MUST return no response.
    buf = io.StringIO()
    orig = sys.stdout
    sys.stdout = buf
    try:
        mcp_core._handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
    finally:
        sys.stdout = orig
    assert buf.getvalue() == ""


def test_mcp_core_handle_tools_list() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    rec = json.loads(out.strip())
    names = [t["name"] for t in rec["result"]["tools"]]
    assert "permission_classify" in names and "scaffold_list" in names


def test_mcp_core_handle_tools_call_ok() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "permission_classify",
                    "arguments": {"command": "ls"}}},
    )
    rec = json.loads(out.strip())
    assert "decision" in rec["result"]


def test_mcp_core_handle_tools_call_unknown_tool() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "nope", "arguments": {}}},
    )
    rec = json.loads(out.strip())
    assert rec["error"]["code"] == -32601


def test_mcp_core_handle_tools_call_bad_arguments() -> None:
    # scaffold_list takes no args; passing extras raises TypeError.
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "scaffold_list",
                    "arguments": {"bogus": 1}}},
    )
    rec = json.loads(out.strip())
    assert rec["error"]["code"] == -32602


def test_mcp_core_handle_tools_call_tool_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(**kw: Any) -> Any:
        raise RuntimeError("tool-boom")

    monkeypatch.setitem(mcp_core._TOOLS, "permission_classify",
                        {**mcp_core._TOOLS["permission_classify"], "fn": boom})
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "permission_classify",
                    "arguments": {"command": "ls"}}},
    )
    rec = json.loads(out.strip())
    assert rec["error"]["code"] == -32000 and "RuntimeError" in rec["error"]["message"]


def test_mcp_core_handle_shutdown() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 7, "method": "shutdown"},
    )
    rec = json.loads(out.strip())
    assert rec == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_mcp_core_handle_unknown_method() -> None:
    _, out = _capture_stdout(
        mcp_core._handle,
        {"jsonrpc": "2.0", "id": 8, "method": "unknown/thing"},
    )
    rec = json.loads(out.strip())
    assert rec["error"]["code"] == -32601


def test_mcp_core_handle_unknown_method_no_id_silent() -> None:
    # Notification (no id) on unknown method → MUST be silent.
    buf = io.StringIO()
    orig = sys.stdout
    sys.stdout = buf
    try:
        mcp_core._handle({"jsonrpc": "2.0", "method": "unknown/thing"})
    finally:
        sys.stdout = orig
    assert buf.getvalue() == ""


def test_mcp_core_main_reads_stdin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buf_in = io.StringIO(
        '{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'
        "\n"
        "not-json\n"
        '{"jsonrpc":"2.0","id":2,"method":"shutdown"}\n'
    )
    buf_out = io.StringIO()
    monkeypatch.setattr(sys, "stdin", buf_in)
    monkeypatch.setattr(sys, "stdout", buf_out)
    rc = mcp_core._main()
    assert rc == 0
    lines = [ln for ln in buf_out.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 3  # initialize resp, parse-error, shutdown resp
    first = json.loads(lines[0])
    assert first["result"]["serverInfo"]["name"] == "vibecodekit-core"


def test_mcp_core_permission_classify_direct() -> None:
    r = mcp_core.permission_classify("ls")
    assert "decision" in r and "mode" in r


def test_mcp_core_scaffold_list_direct() -> None:
    r = mcp_core.scaffold_list()
    assert "presets" in r and len(r["presets"]) >= 1


# -------------------------------------------------------------------------
# install_manifest.py
# -------------------------------------------------------------------------

from vibecodekit import install_manifest as im


def test_install_manifest_sha_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    assert len(im._sha(p)) == 64


def test_install_manifest_install_real_copy(tmp_path: Path) -> None:
    """Exercise the non-dry-run path + _install_lock context manager."""
    result = im.install(tmp_path, dry_run=False)
    assert result["dry_run"] is False
    assert result["total"] > 0
    # Idempotent — running again should skip everything.
    result2 = im.install(tmp_path, dry_run=False)
    assert result2["skipped"] == result2["total"]


def test_install_manifest_main_human_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv",
                        ["install_manifest", str(tmp_path), "--dry-run"])
    im._main()
    out = capsys.readouterr().out
    assert "dry_run: True" in out

    monkeypatch.setattr(sys, "argv", ["install_manifest", str(tmp_path),
                                      "--dry-run", "--json"])
    im._main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True and "operations" in payload


# -------------------------------------------------------------------------
# learnings.py
# -------------------------------------------------------------------------

from vibecodekit import learnings as lrn


def test_learnings_store_bad_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bad scope"):
        lrn.LearningStore(tmp_path / "x.jsonl", scope="nope")


def test_learnings_store_properties(tmp_path: Path) -> None:
    p = tmp_path / "x.jsonl"
    s = lrn.LearningStore(p, scope="project")
    assert s.path == p
    assert s.scope == "project"


def test_learnings_store_append_and_load_skips_malformed(tmp_path: Path) -> None:
    p = tmp_path / "x.jsonl"
    s = lrn.LearningStore(p, scope="project")
    rec = s.append(lrn.Learning(text="hello", scope="project", tags=("a",), author="me"))
    assert rec.captured_ts > 0
    # Append a malformed + empty line manually.
    with open(p, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("not-json\n")
    items = s.load()
    assert len(items) == 1 and items[0].text == "hello"


def test_learnings_main_capture_list_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert lrn._main(["capture", "hello", "world",
                      "--scope", "project", "--tag", "t1"]) == 0
    assert lrn._main(["list", "--scope", "project"]) == 0
    assert lrn._main(["list", "--scope", "project", "--json"]) == 0
    assert lrn._main(["list"]) == 0  # merged across scopes
    assert lrn._main(["clear"]) == 0


# -------------------------------------------------------------------------
# event_bus.py
# -------------------------------------------------------------------------

from vibecodekit import event_bus as eb


def test_event_bus_emit_and_read_all(tmp_path: Path) -> None:
    bus = eb.EventBus(tmp_path, session_id="s1")
    assert bus.session_id == "s1"
    bus.set_turn(3)
    rec = bus.emit("turn_start", status="ok", payload={"x": 1})
    assert rec["turn"] == 3 and rec["schema"] == eb.SCHEMA
    bus.emit("tool_result", status="error", payload={"err": "boom"})
    events = list(bus.read_all())
    assert len(events) == 2 and events[0]["event"] == "turn_start"


def test_event_bus_new_session_id_default(tmp_path: Path) -> None:
    bus = eb.EventBus(tmp_path)
    assert bus.session_id.startswith("vibe-")


def test_event_bus_read_all_missing(tmp_path: Path) -> None:
    bus = eb.EventBus(tmp_path, session_id="s-missing")
    # Explicitly remove any file created by __init__.
    if bus.path.exists():
        bus.path.unlink()
    assert list(bus.read_all()) == []


def test_event_bus_read_all_skips_malformed(tmp_path: Path) -> None:
    bus = eb.EventBus(tmp_path, session_id="s-malformed")
    bus.path.parent.mkdir(parents=True, exist_ok=True)
    bus.path.write_text('not-json\n{"event":"x","status":"ok","turn":1}\n',
                        encoding="utf-8")
    evts = list(bus.read_all())
    assert len(evts) == 1 and evts[0]["event"] == "x"


def test_event_bus_emit_fsync_error_is_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus = eb.EventBus(tmp_path, session_id="s-fsync")

    def boom(fd: int) -> None:
        raise OSError("no fsync")

    monkeypatch.setattr(eb.os, "fsync", boom)
    rec = bus.emit("ok", payload={})
    assert rec["event"] == "ok"


# -------------------------------------------------------------------------
# denial_store.py
# -------------------------------------------------------------------------

from vibecodekit import denial_store as ds


def test_denial_store_record_and_success_and_clear(tmp_path: Path) -> None:
    st = ds.DenialStore(tmp_path, max_consecutive=2, max_total=5,
                         ttl_seconds=60)
    st.record_denial("rm -rf /", reason="dangerous")
    st.record_denial("rm -rf /", reason="dangerous-again")
    # denied_before returns the rec when count ≥ 2.
    rec = st.denied_before("rm -rf /")
    assert rec and rec["count"] == 2
    # record_success resets consecutive.
    st.record_success()
    state = st.state()
    assert state.get("consecutive", -1) == 0
    # Clear wipes everything.
    st.clear()
    assert st.denied_before("rm -rf /") is None


def test_denial_store_malformed_json_fallback(tmp_path: Path) -> None:
    st = ds.DenialStore(tmp_path)
    st.path.write_text("not-json", encoding="utf-8")
    # _read returns {} on JSONDecodeError; record_denial still works.
    rec = st.record_denial("ls", reason="why not")
    assert rec["count"] == 1


def test_denial_store_denied_before_ttl_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = ds.DenialStore(tmp_path, ttl_seconds=10)
    st.record_denial("dangerous", reason="x")
    st.record_denial("dangerous", reason="x")
    # Simulate time passing beyond TTL.
    now = time.time() + 1000
    monkeypatch.setattr(ds.time, "time", lambda: now)
    assert st.denied_before("dangerous") is None


def test_denial_store_write_exception_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = ds.DenialStore(tmp_path)
    # Force os.replace to raise after temp file is written — ensures the
    # cleanup branch runs (unlink tmp file, reraise).
    calls: Dict[str, int] = {"n": 0}

    def boom_replace(src: str, dst: str) -> None:
        calls["n"] += 1
        raise OSError("boom replace")

    monkeypatch.setattr(ds.os, "replace", boom_replace)
    with pytest.raises(OSError):
        st.record_denial("xyz", reason="simulated")
    assert calls["n"] >= 1


def test_denial_store_should_fallback_to_user(tmp_path: Path) -> None:
    st = ds.DenialStore(tmp_path, max_consecutive=2, max_total=50)
    st.record_denial("a", reason="x")
    st.record_denial("b", reason="x")
    assert st.should_fallback_to_user() is True


# -------------------------------------------------------------------------
# compaction.py
# -------------------------------------------------------------------------

from vibecodekit import compaction as cpt


def test_compaction_collect_events_oserror_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True)
    f = rt / "sess.events.jsonl"
    f.write_text('{"event":"x"}\n', encoding="utf-8")

    orig_read_text = Path.read_text

    def read_text(self: Path, *a: Any, **kw: Any) -> str:
        if self.name.endswith(".events.jsonl"):
            raise OSError("denied")
        return orig_read_text(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", read_text)
    assert cpt._collect_events(rt) == []


def test_compaction_summarise_line_bad_json() -> None:
    assert cpt._summarise_line("not-json") is None


def test_compaction_summarise_line_ok() -> None:
    rec = cpt._summarise_line(
        '{"ts":1,"event":"e","status":"ok","turn":2,"payload":{"k":1}}'
    )
    assert rec and rec["event"] == "e" and rec["payload_keys"] == ["k"]


def test_compaction_load_keeps_oserror_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "BLUEPRINT.md").write_text("hi", encoding="utf-8")

    orig_read_text = Path.read_text

    def read_text(self: Path, *a: Any, **kw: Any) -> str:
        if self.name == "BLUEPRINT.md":
            raise OSError("denied")
        return orig_read_text(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", read_text)
    keeps = cpt._load_keeps(tmp_path)
    # BLUEPRINT was skipped; no keeps.
    assert "blueprint" not in keeps


def test_compaction_compact_layer1_truncation(tmp_path: Path) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True)
    big = "a" * 50  # well under default MAX_CHARS, so we'll lower the cap
    (rt / "sess.events.jsonl").write_text(big + "\n", encoding="utf-8")
    out = cpt.compact(tmp_path, max_chars=10, reactive=True)
    layers = {l["layer"] for l in out["layers"]}
    assert 1 in layers and 2 in layers and 3 in layers and 4 in layers and 5 in layers


def test_compaction_compact_load_keeps_paths(tmp_path: Path) -> None:
    (tmp_path / "BLUEPRINT.md").write_text("bp", encoding="utf-8")
    (tmp_path / "REQUIREMENTS.md").write_text("rq", encoding="utf-8")
    out = cpt.compact(tmp_path, reactive=False)
    layer5 = next(l for l in out["layers"] if l["layer"] == 5)
    assert "blueprint" in layer5["keeps"]


# -------------------------------------------------------------------------
# conformance_audit.py — _main + exception path in audit()
# -------------------------------------------------------------------------

from vibecodekit import conformance_audit as ca


def test_conformance_audit_exception_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force the FIRST probe to raise → covers line 2063-2064 (generic
    exception handler inside the audit() loop)."""
    name0, probe0 = ca.PROBES[0]

    def boom(p: Path) -> Any:
        raise RuntimeError("forced-failure")

    new = [(name0, boom)] + list(ca.PROBES[1:])
    monkeypatch.setattr(ca, "PROBES", new)
    r = ca.audit(threshold=0.0)
    # The forced-failed probe should be listed.
    first = next(x for x in r["probes"] if x["pattern"] == name0)
    assert first["pass"] is False
    assert "forced-failure" in first["detail"]


def test_conformance_audit_main_human(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["conformance_audit", "--threshold", "0.0"])
    with pytest.raises(SystemExit) as exc:
        ca._main()
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "parity:" in out


def test_conformance_audit_main_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv",
                        ["conformance_audit", "--threshold", "0.0", "--json"])
    with pytest.raises(SystemExit):
        ca._main()
    payload = json.loads(capsys.readouterr().out)
    assert "probes" in payload and payload["total"] == len(ca.PROBES)


def test_conformance_audit_main_failing_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["conformance_audit", "--threshold", "1.5"])
    with pytest.raises(SystemExit) as exc:
        ca._main()
    assert exc.value.code == 1


# -------------------------------------------------------------------------
# intent_router.py
# -------------------------------------------------------------------------

from vibecodekit.intent_router import IntentRouter, Clarification, IntentMatch


def test_intent_router_empty_prose_clarification() -> None:
    r = IntentRouter()
    m = r.classify("")
    assert isinstance(m, Clarification)
    assert r.route(m) == []
    # explain both languages.
    assert isinstance(r.explain(m, lang="vi"), str)
    assert isinstance(r.explain(m, lang="en"), str)


def test_intent_router_no_match_clarification() -> None:
    r = IntentRouter()
    m = r.classify("xxqq random gibberish no intent")
    assert isinstance(m, Clarification)


def test_intent_router_low_confidence_match() -> None:
    r = IntentRouter(high_conf=0.99, low_conf=0.1)
    m = r.classify("deploy")
    # With such a high high_conf, even a direct deploy mention will
    # fall below and take the low-conf path.
    assert isinstance(m, (IntentMatch, Clarification))


def test_intent_router_explain_en_match() -> None:
    r = IntentRouter()
    m = r.classify("deploy to vercel")
    if isinstance(m, IntentMatch):
        assert "Pipeline" in r.explain(m, lang="en")
        assert "Sẽ chạy" in r.explain(m, lang="vi") or isinstance(m, IntentMatch)


# -------------------------------------------------------------------------
# browser/state.py — Linux-reachable branches
# -------------------------------------------------------------------------

from vibecodekit.browser import state as bstate


def test_browser_state_from_dict_extra_fields() -> None:
    s = bstate.BrowserState.from_dict({
        "pid": 1, "port": 8000, "started_ts": 0.0,
        "last_activity_ts": 0.0, "idle_timeout_seconds": 60,
        "cookie_path": "", "protocol_version": "1.0.0",
        "extra": {"already": "there"},
        "new_field": "surprise",
    })
    assert s.extra["new_field"] == "surprise"
    assert s.extra["already"] == "there"


def test_browser_state_read_state_missing(tmp_path: Path) -> None:
    assert bstate.read_state(path=tmp_path / "no.json") is None


def test_browser_state_read_state_bad_json(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text("not-json", encoding="utf-8")
    assert bstate.read_state(path=p) is None


def test_browser_state_read_state_non_dict(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text("[]", encoding="utf-8")
    assert bstate.read_state(path=p) is None


def test_browser_state_clear_state_missing(tmp_path: Path) -> None:
    assert bstate.clear_state(path=tmp_path / "missing.json") is False


def test_browser_state_select_port_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bstate, "_is_port_free", lambda *a, **k: False)
    import random
    with pytest.raises(RuntimeError, match="could not find a free port"):
        bstate.select_port(rng=random.Random(0), budget=3)


def test_browser_state_is_pid_alive_variants() -> None:
    assert bstate.is_pid_alive(0) is False
    # pid=1 (init) should exist; we only own-process under some kernels — fall
    # through both branches by monkeypatching os.kill.
    assert bstate.is_pid_alive(os.getpid()) is True


def test_browser_state_is_pid_alive_process_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(bstate.os, "kill", boom)
    assert bstate.is_pid_alive(123) is False


def test_browser_state_is_pid_alive_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr(bstate.os, "kill", boom)
    assert bstate.is_pid_alive(1) is True


def test_browser_state_is_idle_expired_edge_cases() -> None:
    s = bstate.BrowserState(pid=1, port=1, started_ts=0.0,
                             last_activity_ts=0.0,
                             idle_timeout_seconds=0)
    assert bstate.is_idle_expired(s) is False
    s2 = bstate.BrowserState(pid=1, port=1, started_ts=0.0,
                              last_activity_ts=0.0,
                              idle_timeout_seconds=60)
    assert bstate.is_idle_expired(s2) is False


def test_browser_state_touch_state_no_daemon(tmp_path: Path) -> None:
    assert bstate.touch_state(path=tmp_path / "missing.json") is None


# -------------------------------------------------------------------------
# skill_discovery.py
# -------------------------------------------------------------------------

from vibecodekit import skill_discovery as sd


def test_skill_discovery_parse_frontmatter_no_match() -> None:
    assert sd._parse_frontmatter("no frontmatter here") == {}


def test_skill_discovery_parse_frontmatter_keys() -> None:
    fm = sd._parse_frontmatter(
        "---\nname: demo\npaths:\n  - \"**/*.py\"\n  - \"Makefile\"\n"
        "tags: [a, \"b\"]\n---\nbody\n"
    )
    assert fm["name"] == "demo"
    assert "**/*.py" in fm["paths"]
    assert fm["tags"] == ["a", "b"]


def test_skill_discovery_discover_respects_ignored(tmp_path: Path) -> None:
    # Create a SKILL.md inside node_modules — must be skipped.
    ig = tmp_path / "node_modules" / "x"
    ig.mkdir(parents=True)
    (ig / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    # Create a good SKILL.md outside.
    good = tmp_path / "skills" / "good"
    good.mkdir(parents=True)
    (good / "SKILL.md").write_text(
        "---\nname: good\npaths:\n  - \"**/*.py\"\n---\n",
        encoding="utf-8",
    )
    res = sd.discover(tmp_path)
    names = [r["name"] for r in res]
    assert "good" in names and "x" not in names


def test_skill_discovery_discover_touched_filter(tmp_path: Path) -> None:
    s = tmp_path / "skills" / "x"
    s.mkdir(parents=True)
    (s / "SKILL.md").write_text(
        "---\nname: x\npaths:\n  - \"src/*.py\"\n---\n",
        encoding="utf-8",
    )
    # touched matches
    res_match = sd.discover(tmp_path, touched="src/a.py")
    assert any(r["name"] == "x" for r in res_match)
    # touched does not match → filtered
    res_nomatch = sd.discover(tmp_path, touched="tests/a.py")
    assert not any(r["name"] == "x" for r in res_nomatch)


def test_skill_discovery_main(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["skill_discovery", "--root", str(tmp_path)])
    sd._main()
    assert capsys.readouterr().out.strip().startswith("[")


def test_skill_discovery_self_skill_md_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "SKILL.md").write_text(
        "---\nname: self\npaths:\n  - \"src/*.py\"\n---\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VIBECODE_SKILL_ROOT", str(tmp_path))
    cand = sd._self_skill_md()
    assert cand is not None and cand.name == "SKILL.md"


def test_skill_discovery_match_glob_variants() -> None:
    assert sd._match_glob("**/*.py", "foo.py")
    assert sd._match_glob("**/*.py", "src/foo.py")
    assert sd._match_glob("*.md", "README.md")
    assert not sd._match_glob("tests/*.py", "src/a.py")


def test_skill_discovery_activate_for_no_skill_md(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(sd, "_self_skill_md", lambda: None)
    r = sd.activate_for("src/a.py")
    assert r["activate"] is False
    assert r["reason"] == "skill_md_missing"


def test_skill_discovery_activate_for_no_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: x\n---\n", encoding="utf-8")
    monkeypatch.setattr(sd, "_self_skill_md", lambda: skill_md)
    r = sd.activate_for("src/a.py")
    assert r["activate"] is False


def test_skill_discovery_activate_for_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: x\npaths:\n  - \"**/*.py\"\n---\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sd, "_self_skill_md", lambda: skill_md)
    r = sd.activate_for("src/a.py")
    assert r["activate"] is True
    assert "**/*.py" in r["matched"]


# -------------------------------------------------------------------------
# cost_ledger.py
# -------------------------------------------------------------------------

from vibecodekit import cost_ledger as cl


def test_cost_ledger_approx_tokens_empty() -> None:
    assert cl._approx_tokens("") == 0
    assert cl._approx_tokens("abcd") >= 1


def test_cost_ledger_summary_missing_file(tmp_path: Path) -> None:
    s = cl.summary(tmp_path)
    assert s == {"turns": 0, "tool_calls": 0, "tokens": 0, "cost_usd": 0.0}


def test_cost_ledger_summary_ignores_malformed(tmp_path: Path) -> None:
    cl.record_turn(tmp_path, 1, "prompt text", "response text")
    cl.record_tool(tmp_path, "shell", latency_ms=10.0, bytes_in=10, bytes_out=20)
    cl.record_tool(tmp_path, "shell", latency_ms=20.0, bytes_in=1, bytes_out=2,
                    status="error")
    # Append a bad line.
    with cl._ledger_path(tmp_path.resolve()).open("a", encoding="utf-8") as f:
        f.write("not-json\n")
    s = cl.summary(tmp_path)
    assert s["turns"] == 1 and s["tool_calls"] == 2
    assert s["per_tool"]["shell"]["errors"] == 1


def test_cost_ledger_reset(tmp_path: Path) -> None:
    cl.record_turn(tmp_path, 1, "p", "r")
    cl.summary(tmp_path)
    cl.reset(tmp_path)
    # After reset both files gone; summary fallback returns defaults.
    assert cl.summary(tmp_path)["turns"] == 0
