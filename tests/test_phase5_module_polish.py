"""Cycle 11 PR2 — Phase 5 polish suite for 6 module gap.

Mục tiêu (đẩy TOTAL từ 82% → ≥85%):
* ``approval_contract.py``       66% → ≥90%
* ``memory_retriever.py``        33% → ≥90%
* ``recovery_engine.py``         58% → ≥95%
* ``dashboard.py``               50% → ≥90%
* ``mcp_servers/selfcheck.py``   23% → ≥90%
* ``doctor.py``                  68% → ≥95%

KHÔNG đụng runtime code (chỉ thêm test).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from vibecodekit import (
    approval_contract as ac,
    dashboard as db,
    doctor,
    memory_retriever as mr,
    recovery_engine as re_eng,
)
from vibecodekit.mcp_servers import selfcheck


# ---------------------------------------------------------------------------
# 1. approval_contract — full lifecycle
# ---------------------------------------------------------------------------


def test_validate_appr_id_rejects_path_traversal() -> None:
    with pytest.raises(ac.InvalidApprovalID):
        ac._validate_appr_id("appr-../escape")
    with pytest.raises(ac.InvalidApprovalID):
        ac._validate_appr_id("../etc/passwd")
    with pytest.raises(ac.InvalidApprovalID):
        ac._validate_appr_id("appr-")  # too short
    with pytest.raises(ac.InvalidApprovalID):
        ac._validate_appr_id("not-an-id")


def test_validate_appr_id_rejects_non_string() -> None:
    with pytest.raises(ac.InvalidApprovalID):
        ac._validate_appr_id(42)  # type: ignore[arg-type]


def test_validate_appr_id_accepts_canonical() -> None:
    ac._validate_appr_id("appr-abcd1234")
    ac._validate_appr_id("appr-AB12-cd34_EF")


def test_create_unknown_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown approval kind"):
        ac.create(tmp_path, kind="bogus", title="t", summary="s")


def test_create_unknown_risk_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown risk level"):
        ac.create(tmp_path, kind="permission", title="t", summary="s",
                  risk="ultra")


def test_create_persists_with_default_options(tmp_path: Path) -> None:
    out = ac.create(tmp_path, kind="permission", title="run rm -rf",
                    summary="dangerous")
    assert out["kind"] == "permission"
    assert out["risk"] == "medium"
    assert out["suggested"] in {"allow", "deny"}
    assert out["id"].startswith("appr-")
    p = tmp_path / ".vibecode" / "runtime" / "approvals" / f"{out['id']}.json"
    assert p.exists()
    saved = json.loads(p.read_text(encoding="utf-8"))
    assert saved == out


def test_create_with_custom_options_and_preview(tmp_path: Path) -> None:
    out = ac.create(
        tmp_path, kind="diff", title="apply patch", summary="risky",
        risk="high", reason="touches prod",
        context={"file": "/etc/passwd"},
        options=[
            {"id": "yes", "label": "Yes", "default": False},
            {"id": "no", "label": "No", "default": True},
        ],
        preview={"type": "diff", "content": "+a\n-b"},
        deadline_sec=30.0,
    )
    assert out["preview"]["type"] == "diff"
    assert out["suggested"] == "no"  # picked because default=True
    assert "deadline_ts" in out
    assert out["context"]["file"] == "/etc/passwd"


def test_create_with_no_default_picks_last(tmp_path: Path) -> None:
    out = ac.create(
        tmp_path, kind="elicitation", title="t", summary="s",
        options=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
    )
    assert out["suggested"] == "b"  # last id wins when no default flagged


def test_list_pending_filters_resolved(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    b = ac.create(tmp_path, kind="permission", title="B", summary="y")
    ac.respond(tmp_path, a["id"], choice="allow")
    pending = ac.list_pending(tmp_path)
    assert [r["id"] for r in pending] == [b["id"]]


def test_list_pending_skips_malformed_files(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="notification", title="N", summary="x")
    bad = (tmp_path / ".vibecode" / "runtime" / "approvals"
           / "appr-deadbeef.json")
    bad.write_text("{not-json", encoding="utf-8")
    pending = ac.list_pending(tmp_path)
    # Only the well-formed one survives.
    assert [r["id"] for r in pending] == [a["id"]]


def test_get_returns_none_for_invalid_id(tmp_path: Path) -> None:
    assert ac.get(tmp_path, "appr-../bad") is None


def test_get_returns_none_for_missing(tmp_path: Path) -> None:
    assert ac.get(tmp_path, "appr-deadbeef") is None


def test_get_merges_response(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    ac.respond(tmp_path, a["id"], choice="allow", note="ok")
    full = ac.get(tmp_path, a["id"])
    assert full is not None
    assert full["response"]["choice"] == "allow"
    assert full["response"]["note"] == "ok"


def test_get_skips_malformed_response(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    rp = (tmp_path / ".vibecode" / "runtime" / "approvals"
          / f"{a['id']}.response.json")
    rp.write_text("{bad", encoding="utf-8")
    full = ac.get(tmp_path, a["id"])
    assert full is not None
    # Malformed response is silently skipped — no "response" key attached.
    assert "response" not in full


def test_respond_invalid_id_returns_error(tmp_path: Path) -> None:
    out = ac.respond(tmp_path, "../escape", choice="allow")
    assert "error" in out


def test_respond_unknown_id_returns_error(tmp_path: Path) -> None:
    out = ac.respond(tmp_path, "appr-deadbeef", choice="allow")
    assert "unknown approval id" in out["error"]


def test_respond_invalid_choice_rejected(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x",
                  options=[{"id": "yes", "label": "Y"},
                           {"id": "no", "label": "N"}])
    out = ac.respond(tmp_path, a["id"], choice="maybe")
    assert "not in" in out["error"]


def test_respond_persists_response(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    out = ac.respond(tmp_path, a["id"], choice="deny", note="n")
    assert out["choice"] == "deny"
    rp = (tmp_path / ".vibecode" / "runtime" / "approvals"
          / f"{a['id']}.response.json")
    assert json.loads(rp.read_text(encoding="utf-8")) == out


def test_wait_invalid_id_returns_error(tmp_path: Path) -> None:
    out = ac.wait(tmp_path, "../bad")
    assert "error" in out


def test_wait_returns_existing_response(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    ac.respond(tmp_path, a["id"], choice="allow")
    out = ac.wait(tmp_path, a["id"], timeout=0.1, poll_sec=0.01)
    assert out["choice"] == "allow"


def test_wait_timeout_auto_denies(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    out = ac.wait(tmp_path, a["id"], timeout=0.05, poll_sec=0.01)
    assert out["choice"] == "deny"
    assert out["note"] == "timeout"


def test_wait_skips_malformed_response_then_times_out(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    rp = (tmp_path / ".vibecode" / "runtime" / "approvals"
          / f"{a['id']}.response.json")
    rp.write_text("{bad", encoding="utf-8")
    out = ac.wait(tmp_path, a["id"], timeout=0.05, poll_sec=0.01)
    assert out["choice"] == "deny"


def test_wait_deadline_exceeded(tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x",
                  deadline_sec=0.0)  # already expired
    # Make the very first iteration see deadline_ts < time.time().
    out = ac.wait(tmp_path, a["id"], timeout=10.0, poll_sec=0.01)
    assert out["choice"] == "deny"
    assert out["note"] == "deadline_exceeded"


def test_clear_resolved(tmp_path: Path) -> None:
    a = ac.create(tmp_path, kind="permission", title="A", summary="x")
    b = ac.create(tmp_path, kind="permission", title="B", summary="y")
    ac.respond(tmp_path, a["id"], choice="allow")
    n = ac.clear_resolved(tmp_path)
    assert n == 1
    pending = ac.list_pending(tmp_path)
    assert [r["id"] for r in pending] == [b["id"]]


# ---------------------------------------------------------------------------
# 2. memory_retriever — load + retrieve
# ---------------------------------------------------------------------------


def test_strip_diacritics_basic() -> None:
    assert mr._strip_diacritics("café") == "cafe"
    assert mr._strip_diacritics("Tiếng Việt") == "Tieng Viet"
    assert mr._strip_diacritics("ASCII") == "ASCII"


def test_tokenize_normalises_and_casefolds() -> None:
    out = mr.tokenize("Tiếng VIỆT — Hello, World!")
    assert "tieng" in out
    assert "viet" in out
    assert "hello" in out
    assert "world" in out


def test_tokenize_empty_string() -> None:
    assert mr.tokenize("") == set()


def test_load_memories_skips_missing_files(tmp_path: Path) -> None:
    chunks = mr.load_memories(tmp_path)
    assert chunks == []


def test_load_memories_splits_by_header(tmp_path: Path) -> None:
    p = tmp_path / "PROJECT_MEMORY.md"
    p.write_text(
        "intro line\n"
        "# Section A\n"
        "alpha line\n"
        "## Sub A.1\n"
        "alpha sub\n"
        "# Section B\n"
        "beta\n",
        encoding="utf-8",
    )
    chunks = mr.load_memories(tmp_path)
    headers = [c["header"] for c in chunks]
    assert "(top)" in headers
    assert "# Section A" in headers
    assert "## Sub A.1" in headers
    assert "# Section B" in headers


def test_load_memories_handles_oserror(tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "PROJECT_MEMORY.md"
    p.write_text("dummy", encoding="utf-8")

    real_read_text = Path.read_text

    def boom(self: Path, *a: Any, **k: Any) -> str:
        if self == p:
            raise OSError("permission denied")
        return real_read_text(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", boom)
    # No crash; the file is silently skipped.
    chunks = mr.load_memories(tmp_path)
    assert chunks == []


def test_retrieve_ranks_by_overlap(tmp_path: Path) -> None:
    p = tmp_path / "CLAUDE.md"
    p.write_text(
        "# Tiếng Việt notes\n"
        "Tài liệu hướng dẫn cài đặt vibecode hybrid ultra.\n"
        "# English notes\n"
        "Quick install guide for vibecode.\n",
        encoding="utf-8",
    )
    out = mr.retrieve(tmp_path, "tieng viet vibecode")
    assert len(out) >= 1
    # The Vietnamese chunk should rank first because both Vietnamese
    # tokens overlap (after diacritic stripping).
    assert "Vi" in out[0]["header"] or "Tiếng" in out[0]["header"]
    assert out[0]["overlap"] >= 1


def test_retrieve_zero_overlap_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "CLAUDE.md"
    p.write_text("# Notes\nfoo bar baz\n", encoding="utf-8")
    out = mr.retrieve(tmp_path, "qqq xxx zzz")
    assert out == []


def test_retrieve_respects_limit(tmp_path: Path) -> None:
    chunks = "\n".join(f"# Header {i}\nfoo bar baz match {i}" for i in range(5))
    (tmp_path / "CLAUDE.md").write_text(chunks, encoding="utf-8")
    out = mr.retrieve(tmp_path, "match", limit=3)
    assert len(out) <= 3


# ---------------------------------------------------------------------------
# 3. recovery_engine — escalating ladder
# ---------------------------------------------------------------------------


def test_recovery_permission_denied_jumps_to_user() -> None:
    led = re_eng.RecoveryLedger()
    rec = led.escalate("permission_denied")
    assert rec["action"] == "surface_user_decision"
    # Idempotent: second call walks ladder normally.
    rec2 = led.escalate("permission_denied")
    assert rec2["action"] == "retry_same"


def test_recovery_context_overflow_jumps_to_compact() -> None:
    led = re_eng.RecoveryLedger()
    rec = led.escalate("context_overflow")
    assert rec["action"] == "compact_then_retry"
    # Same logic for prompt_too_large.
    led2 = re_eng.RecoveryLedger()
    assert led2.escalate("prompt_too_large")["action"] == "compact_then_retry"


def test_recovery_walks_full_ladder() -> None:
    led = re_eng.RecoveryLedger()
    actions = [led.escalate("tool_failed")["action"] for _ in re_eng.LEVELS]
    assert actions == list(re_eng.LEVELS)


def test_recovery_terminal_after_exhausted() -> None:
    led = re_eng.RecoveryLedger()
    for _ in re_eng.LEVELS:
        led.escalate("tool_failed")
    rec = led.escalate("tool_failed")
    assert rec["terminal"] == "recovery_exhausted"


def test_recovery_reset() -> None:
    led = re_eng.RecoveryLedger()
    led.escalate("tool_failed")
    assert led.history
    led.reset()
    assert not led.attempted
    assert not led.history


def test_recovery_to_dict() -> None:
    led = re_eng.RecoveryLedger()
    led.escalate("tool_failed")
    led.escalate("tool_failed")
    out = led.to_dict()
    assert sorted(out["attempted"]) == ["retry_same", "retry_with_budget"]
    assert len(out["history"]) == 2


def test_recovery_main_cli(monkeypatch: pytest.MonkeyPatch,
                             capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(sys, "argv", ["recovery_engine", "tool_failed",
                                        "context_overflow"])
    re_eng._main()
    out = capsys.readouterr().out
    assert "retry_same" in out
    assert "compact_then_retry" in out


# ---------------------------------------------------------------------------
# 4. dashboard — summarise events
# ---------------------------------------------------------------------------


def _seed_events(rt: Path) -> None:
    rt.mkdir(parents=True, exist_ok=True)
    events = [
        {"event": "turn_start", "session_id": "sess-1", "turn": 0},
        {"event": "tool_result", "session_id": "sess-1", "turn": 1,
         "status": "ok",
         "payload": {"block": {"tool": "Bash"}}},
        {"event": "tool_result", "session_id": "sess-1", "turn": 2,
         "status": "deny",
         "payload": {"block": {"tool": "Edit"}}},
        {"event": "recovery_compact", "session_id": "sess-1", "turn": 3},
        {"event": "recovery_retry", "session_id": "sess-1", "turn": 4},
    ]
    out = rt / "1.events.jsonl"
    out.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                   encoding="utf-8")


def test_dashboard_summarise_empty(tmp_path: Path) -> None:
    out = db.summarise(tmp_path)
    assert out["event_total"] == 0
    assert out["event_counts"] == {}
    assert out["session"] is None


def test_dashboard_summarise_with_events(tmp_path: Path) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    _seed_events(rt)
    out = db.summarise(tmp_path)
    assert out["session"] == "sess-1"
    assert out["event_total"] == 5
    assert out["tool_counts"] == {"Bash": 1, "Edit": 1}
    assert out["recovery_counts"] == {"recovery_compact": 1,
                                        "recovery_retry": 1}
    assert any(err["status"] == "deny" for err in out["errors"])


def test_dashboard_skips_malformed_lines(tmp_path: Path) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True, exist_ok=True)
    p = rt / "1.events.jsonl"
    p.write_text(
        "{not-json\n"
        + json.dumps({"event": "turn_start", "session_id": "s", "turn": 0})
        + "\n",
        encoding="utf-8",
    )
    out = db.summarise(tmp_path)
    assert out["event_total"] == 1


def test_dashboard_reads_denials(tmp_path: Path) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "denials.json").write_text(
        json.dumps({
            "Bash:rm -rf /": {"count": 1, "first_ts": 0, "last_ts": 0},
            "_state": {"meta": "ok"},
        }),
        encoding="utf-8",
    )
    out = db.summarise(tmp_path)
    assert out["permission"]["denied_actions"] == 1
    assert out["permission"]["denials_state"] == {"meta": "ok"}


def test_dashboard_denials_corrupted_swallowed(tmp_path: Path) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "denials.json").write_text("{bad", encoding="utf-8")
    out = db.summarise(tmp_path)
    assert out["permission"] == {}


def test_dashboard_main_runs(tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch,
                              capsys: pytest.CaptureFixture) -> None:
    rt = tmp_path / ".vibecode" / "runtime"
    _seed_events(rt)
    monkeypatch.setattr(sys, "argv",
                        ["dashboard", "--root", str(tmp_path)])
    db._main()  # smoke-test the CLI path


def test_dashboard_main_json_mode(tmp_path: Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv",
                        ["dashboard", "--root", str(tmp_path), "--json"])
    db._main()  # exercises the json branch


# ---------------------------------------------------------------------------
# 5. mcp_servers/selfcheck — tools + JSON-RPC handling
# ---------------------------------------------------------------------------


def test_selfcheck_ping_and_now() -> None:
    out = selfcheck.ping()
    assert out["pong"] is True
    assert "ts" in out
    out2 = selfcheck.now()
    assert "ts" in out2


def test_selfcheck_echo() -> None:
    assert selfcheck.echo(msg="hello")["echo"] == "hello"
    assert selfcheck.echo()["echo"] == ""


def _capture_stdout(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(selfcheck.sys, "stdout", buf)
    return buf


def test_selfcheck_handle_initialize(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 1, "method": "initialize", "params": {}})
    out = json.loads(buf.getvalue().strip())
    assert out["result"]["serverInfo"]["name"] == "vibecodekit-selfcheck"


def test_selfcheck_handle_initialized_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    # Notifications produce no output.
    selfcheck._handle({"method": "notifications/initialized"})
    assert buf.getvalue() == ""


def test_selfcheck_handle_tools_list(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 2, "method": "tools/list"})
    out = json.loads(buf.getvalue().strip())
    names = {t["name"] for t in out["result"]["tools"]}
    assert names == {"ping", "echo", "now"}


def test_selfcheck_handle_tools_call_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 3, "method": "tools/call",
                       "params": {"name": "echo", "arguments": {"msg": "hi"}}})
    out = json.loads(buf.getvalue().strip())
    assert out["result"]["echo"] == "hi"


def test_selfcheck_handle_tools_call_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 4, "method": "tools/call",
                       "params": {"name": "doesnotexist"}})
    out = json.loads(buf.getvalue().strip())
    assert "unknown tool" in out["error"]["message"]


def test_selfcheck_handle_tools_call_bad_args(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 5, "method": "tools/call",
                       "params": {"name": "ping",
                                   "arguments": {"unexpected": 1}}})
    out = json.loads(buf.getvalue().strip())
    assert "bad arguments" in out["error"]["message"]


def test_selfcheck_handle_tools_call_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)

    def boom(**_kw: Any) -> Dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setitem(selfcheck._TOOLS["ping"], "fn", boom)
    selfcheck._handle({"id": 6, "method": "tools/call",
                       "params": {"name": "ping"}})
    out = json.loads(buf.getvalue().strip())
    assert "RuntimeError" in out["error"]["message"]


def test_selfcheck_handle_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 7, "method": "shutdown"})
    out = json.loads(buf.getvalue().strip())
    assert out["result"] == {}


def test_selfcheck_handle_unknown_method(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    selfcheck._handle({"id": 8, "method": "logging/setLevel"})
    out = json.loads(buf.getvalue().strip())
    assert "method not found" in out["error"]["message"]


def test_selfcheck_handle_unknown_notification_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    # No id → notification → silent on unknown.
    selfcheck._handle({"method": "ping/extension"})
    assert buf.getvalue() == ""


def test_selfcheck_main_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = _capture_stdout(monkeypatch)
    stdin_text = (
        "\n"
        "{not-json\n"
        + json.dumps({"id": 9, "method": "initialize", "params": {}}) + "\n"
        + json.dumps({"id": 10, "method": "shutdown"}) + "\n"
    )
    monkeypatch.setattr(selfcheck.sys, "stdin", io.StringIO(stdin_text))
    rc = selfcheck._main()
    assert rc == 0
    out_lines = [json.loads(line) for line in buf.getvalue().strip().splitlines() if line]
    # Expect: parse-error envelope (rid=None) + initialize result + shutdown result.
    assert any(o.get("error", {}).get("code") == -32700 for o in out_lines)
    assert any(o.get("id") == 9 for o in out_lines)
    assert any(o.get("id") == 10 for o in out_lines)


# ---------------------------------------------------------------------------
# 6. doctor — project health check
# ---------------------------------------------------------------------------


def test_doctor_check_empty_dir(tmp_path: Path) -> None:
    out = doctor.check(tmp_path)
    assert out["skill_repo"] is False
    assert "advisory_missing" in out
    assert out["package_importable"] is True  # vibecodekit is importable
    assert out["exit_code"] == 0
    assert out["installed_only"] is False


def test_doctor_installed_only_fails_on_missing(tmp_path: Path) -> None:
    out = doctor.check(tmp_path, installed_only=True)
    assert out["exit_code"] == 1


def test_doctor_skill_repo_layout_detected(tmp_path: Path) -> None:
    (tmp_path / "update-package").mkdir()
    (tmp_path / "update-package" / "CLAUDE.md").write_text("x", encoding="utf-8")
    (tmp_path / "update-package" / ".claw.json").write_text("{}", encoding="utf-8")
    (tmp_path / "scripts" / "vibecodekit").mkdir(parents=True)
    out = doctor.check(tmp_path)
    assert out["skill_repo"] is True


def test_doctor_advisory_present_when_directly_in_root(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("x", encoding="utf-8")
    out = doctor.check(tmp_path)
    assert "CLAUDE.md" in out["advisory_present"]


def test_doctor_runtime_placeholder_warns(tmp_path: Path) -> None:
    # ai-rules/vibecodekit/ exists but has no scripts/ → placeholder.
    (tmp_path / "ai-rules" / "vibecodekit").mkdir(parents=True)
    out = doctor.check(tmp_path)
    assert out["runtime_placeholder"] is True
    assert any("placeholder" in w for w in out["warnings"])


def test_doctor_runtime_assets_missing(tmp_path: Path) -> None:
    # Realistic shape: ai-rules/vibecodekit/ contains scripts/ entry
    # (so not placeholder) but is missing the required asset list.
    runtime = tmp_path / "ai-rules" / "vibecodekit"
    runtime.mkdir(parents=True)
    (runtime / "scripts" / "vibecodekit").mkdir(parents=True)
    (runtime / "scripts" / "vibecodekit" / "cli.py").write_text("", encoding="utf-8")
    out = doctor.check(tmp_path)
    assert out["runtime_placeholder"] is False
    assert out["runtime_assets_missing"]
    assert any("missing required runtime assets" in w for w in out["warnings"])


def test_doctor_main_smoke(tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv",
                        ["doctor", "--root", str(tmp_path)])
    with pytest.raises(SystemExit) as ei:
        doctor._main()
    assert ei.value.code == 0


def test_doctor_main_installed_only_exits_nonzero(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv",
                        ["doctor", "--root", str(tmp_path),
                         "--installed-only"])
    with pytest.raises(SystemExit) as ei:
        doctor._main()
    assert ei.value.code == 1
