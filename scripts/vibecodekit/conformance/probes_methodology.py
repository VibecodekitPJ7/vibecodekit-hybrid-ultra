"""Probes #31-50 — RRI methodology, scaffolds, asset catalogs.

Extracted from ``conformance_audit.py`` in cycle 14 PR β-3.  These 20
probes verify the methodology layer (RRI / RRI-T / RRI-UX / docs
scaffold) and the supporting reference assets (style tokens, question
bank, copy patterns, stack recommendations, …):

  #31  rri_reverse_interview
  #32  rri_t_testing_methodology
  #33  rri_ux_critique_methodology
  #34  rri_ui_design_pipeline
  #35  vibecode_master_workflow
  #36  methodology_slash_commands
  #37  methodology_runners
  #38  config_persistence
  #39  mcp_stdio_full_handshake
  #40  refine_boundary_step8
  #41  verify_req_coverage
  #42  saas_anti_patterns_12
  #43  portfolio_saas_scaffolds
  #44  enterprise_module_workflow
  #45  docs_scaffold_pattern_d
  #46  style_tokens_canonical
  #47  rri_question_bank
  #48  copy_patterns_canonical
  #49  stack_recommendations
  #50  docs_intent_routing

Probe functions live here under the leading-underscore name (e.g.
``_probe_rri_reverse_interview``); ``conformance_audit.py`` re-imports
them so the manual ``PROBES`` list keeps working unchanged until β-6
switches to the ``@probe`` decorator.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Tuple

from .. import memory_hierarchy, methodology
from ._helpers import find_slash_command as _find_slash_command


def _probe_rri_reverse_interview(tmp: Path) -> Tuple[bool, str]:
    """RRI (Reverse Requirements Interview) methodology assets present."""
    here = Path(__file__).resolve().parents[3]
    needed = [
        here / "references" / "29-rri-reverse-interview.md",
        here / "assets" / "templates" / "rri-matrix.md",
    ]
    missing = [p.name for p in needed if not p.exists()]
    if missing:
        return False, f"missing: {missing}"
    body = needed[0].read_text(encoding="utf-8")
    # Canonical 5 personas must be named.
    personas = ("End User", "Business Analyst", "QA", "Developer", "Operator")
    misses = [p for p in personas if p not in body]
    return (not misses, "personas ok" if not misses else f"missing personas: {misses}")


def _probe_rri_t_testing(tmp: Path) -> Tuple[bool, str]:
    """RRI-T testing methodology: 5 personas × 7 dimensions × 8 stress axes."""
    here = Path(__file__).resolve().parents[3]
    ref = here / "references" / "31-rri-t-testing.md"
    tpl = here / "assets" / "templates" / "rri-t-test-case.md"
    if not ref.exists() or not tpl.exists():
        return False, "missing ref or template"
    body = ref.read_text(encoding="utf-8")
    tbody = tpl.read_text(encoding="utf-8")
    dims = [f"D{i}" for i in range(1, 8)]
    stress = ("TIME", "DATA", "ERROR", "COLLAB", "EMERGENCY",
              "SECURITY", "INFRASTRUCTURE", "LOCALIZATION")
    dm = all(d in body for d in dims)
    sm = all(s in body for s in stress)
    fmt = all(tok in tbody for tok in ("## Q", "## A", "## R", "## P", "## T"))
    return (dm and sm and fmt,
            f"dims={dm} stress={sm} qarpt={fmt}")


def _probe_rri_ux_critique(tmp: Path) -> Tuple[bool, str]:
    """RRI-UX: 5 UX personas × 7 dims × 8 Flow Physics; S→V→P→F→I template."""
    here = Path(__file__).resolve().parents[3]
    ref = here / "references" / "32-rri-ux-critique.md"
    tpl = here / "assets" / "templates" / "rri-ux-critique.md"
    if not ref.exists() or not tpl.exists():
        return False, "missing ref or template"
    body = ref.read_text(encoding="utf-8")
    tbody = tpl.read_text(encoding="utf-8")
    personas = ("Speed Runner", "First-Timer", "Data Scanner",
                "Multi-Tasker", "Field Worker")
    axes = ("SCROLL", "CLICK DEPTH", "EYE TRAVEL", "DECISION LOAD",
            "RETURN PATH", "VIEWPORT", "VN TEXT", "FEEDBACK")
    pm = all(p in body for p in personas)
    am = all(a in body for a in axes)
    fmt = all(tok in tbody for tok in ("## S ", "## V ", "## P ", "## F ", "## I "))
    return (pm and am and fmt,
            f"personas={pm} axes={am} svpfi={fmt}")


def _probe_vibecode_master_workflow(tmp: Path) -> Tuple[bool, str]:
    """VIBECODE-MASTER 8-step workflow + 3 actors are documented."""
    here = Path(__file__).resolve().parents[3]
    ref = here / "references" / "30-vibecode-master.md"
    vision = here / "assets" / "templates" / "vision.md"
    if not ref.exists() or not vision.exists():
        return False, "missing ref or vision template"
    body = ref.read_text(encoding="utf-8")
    steps = ("SCAN", "RRI", "VISION", "BLUEPRINT",
             "TASK GRAPH", "BUILD", "VERIFY", "REFINE")
    actors = ("Homeowner", "Contractor", "Builder")
    sm = all(s in body for s in steps)
    am = all(a in body for a in actors)
    return (sm and am, f"steps={sm} actors={am}")


def _probe_rri_ui_combined(tmp: Path) -> Tuple[bool, str]:
    """RRI-UI: four-phase pipeline combining RRI-UX + RRI-T for design."""
    here = Path(__file__).resolve().parents[3]
    ref = here / "references" / "33-rri-ui-design.md"
    if not ref.exists():
        return False, "missing 33-rri-ui-design.md"
    body = ref.read_text(encoding="utf-8")
    phases = ("Phase 0", "Phase 1", "Phase 2", "Phase 3", "Phase 4")
    gates = ("≥ 70 %", "≥ 85 %", "P0")
    pm = all(p in body for p in phases)
    gm = all(g in body for g in gates)
    return (pm and gm, f"phases={pm} gate={gm}")


def _probe_methodology_runners(tmp: Path) -> Tuple[bool, str]:
    """v0.10.1: RRI-T, RRI-UX, and VN-checklist evaluators are executable."""
    import json as _json
    # RRI-T: happy path passes, injecting a P0 FAIL flips the gate.
    good = [{"id": f"t{i}", "dimension": f"D{(i%7)+1}",
             "result": "PASS", "priority": "P1"} for i in range(14)]
    bad = list(good) + [{"id": "x", "dimension": "D1",
                          "result": "FAIL", "priority": "P0"}]
    p_good = tmp / "rri_t_good.jsonl"
    p_bad = tmp / "rri_t_bad.jsonl"
    p_good.write_text("\n".join(_json.dumps(e) for e in good), encoding="utf-8")
    p_bad.write_text("\n".join(_json.dumps(e) for e in bad), encoding="utf-8")
    r_good = methodology.evaluate_rri_t(p_good)
    r_bad = methodology.evaluate_rri_t(p_bad)
    rri_t_ok = r_good["gate"] == "PASS" and r_bad["gate"] == "FAIL"
    # RRI-UX similar
    ux_good = [{"id": f"u{i}", "dimension": f"U{(i%7)+1}",
                "result": "FLOW", "priority": "P1"} for i in range(14)]
    ux_bad = list(ux_good) + [{"id": "x", "dimension": "U1",
                                 "result": "BROKEN", "priority": "P0"}]
    p_gu = tmp / "ux_good.jsonl"
    p_bu = tmp / "ux_bad.jsonl"
    p_gu.write_text("\n".join(_json.dumps(e) for e in ux_good), encoding="utf-8")
    p_bu.write_text("\n".join(_json.dumps(e) for e in ux_bad), encoding="utf-8")
    rg = methodology.evaluate_rri_ux(p_gu)
    rb = methodology.evaluate_rri_ux(p_bu)
    ux_ok = rg["gate"] == "PASS" and rb["gate"] == "FAIL"
    # VN checklist
    all_true = {k: True for k, _ in methodology.VN_CHECKLIST_ITEMS}
    vn = methodology.evaluate_vn_checklist(all_true)
    vn_ok = vn["gate"] == "PASS" and vn["summary"]["pass"] == 12
    return (rri_t_ok and ux_ok and vn_ok,
            f"rri_t={rri_t_ok} ux={ux_ok} vn={vn_ok}")


def _probe_mcp_stdio_handshake(tmp: Path) -> Tuple[bool, str]:
    """v0.10.1: real MCP initialize + tools/list + tools/call handshake
    against the bundled selfcheck server."""
    import sys
    from .. import __file__ as vk_init
    from .. import mcp_client
    pkg_dir = Path(vk_init).resolve().parent
    scripts_dir = str(pkg_dir.parent)
    env = {"PYTHONPATH": scripts_dir + os.pathsep + os.environ.get("PYTHONPATH", "")}
    cmd = [sys.executable, "-m", "vibecodekit.mcp_servers.selfcheck"]
    try:
        with mcp_client.StdioSession(cmd, env=env, timeout=5.0) as sess:
            init = sess.initialize()
            if init.get("serverInfo", {}).get("name") != "vibecodekit-selfcheck":
                return False, f"bad serverInfo: {init}"
            tools = sess.list_tools()
            names = sorted(t["name"] for t in tools)
            if names != ["echo", "now", "ping"]:
                return False, f"tools/list={names}"
            r = sess.call_tool("ping", {})
            if r.get("result", {}).get("pong") is not True:
                return False, f"ping={r}"
        return True, f"tools={names} pong=True"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _probe_config_persistence(tmp: Path) -> Tuple[bool, str]:
    """v0.10.1: embedding backend persists via ~/.vibecode/config.json.

    Note: restores any pre-existing ``VIBECODE_CONFIG_HOME`` env var so the
    probe is side-effect free when run in a user session that already had
    its own config-home configured.
    """
    prev = os.environ.get("VIBECODE_CONFIG_HOME")
    os.environ["VIBECODE_CONFIG_HOME"] = str(tmp / "cfg")
    try:
        methodology.set_embedding_backend("hash-256")
        backend = methodology.get_embedding_backend()
        mem_backend = memory_hierarchy.get_backend(None)
        ok = backend == "hash-256" and mem_backend.name == "hash-256"
        return (ok, f"persisted={backend} memory_resolves={mem_backend.name}")
    finally:
        if prev is None:
            os.environ.pop("VIBECODE_CONFIG_HOME", None)
        else:
            os.environ["VIBECODE_CONFIG_HOME"] = prev


def _probe_refine_boundary(tmp: Path) -> Tuple[bool, str]:
    """v5 BƯỚC 8/8 — `/vibe-refine` command + classifier wired together."""
    from .. import refine_boundary
    here = Path(__file__).resolve().parents[3]
    cmd = _find_slash_command(here, "vibe-refine.md")
    tpl = here / "assets" / "templates" / "refine.md"
    if cmd is None:
        return False, "missing slash command vibe-refine.md (looked in 5 paths)"
    if not tpl.exists():
        return False, f"missing template: {tpl}"
    in_scope = refine_boundary.classify_change([
        {"path": "README.md", "status": "modified",
         "added_lines": ["new copy"], "removed_lines": ["old"]}
    ])
    requires = refine_boundary.classify_change([
        {"path": "package.json", "status": "modified",
         "added_lines": ["dep"], "removed_lines": []}
    ])
    if in_scope["kind"] != "in_scope":
        return False, f"copy edit misclassified: {in_scope}"
    if requires["kind"] != "requires_vision":
        return False, f"deps edit misclassified: {requires}"
    return True, "command + template + classifier OK"


def _probe_verify_coverage(tmp: Path) -> Tuple[bool, str]:
    """v5 BƯỚC 7 — REQ-* traceability evaluator + template sections."""
    here = Path(__file__).resolve().parents[3]
    vt = (here / "assets" / "templates" / "verify-report.md").read_text(
        encoding="utf-8"
    )
    bp = (here / "assets" / "templates" / "blueprint.md").read_text(
        encoding="utf-8"
    )
    if "Requirement traceability" not in vt:
        return False, "verify-report.md missing traceability section"
    if "RRI Requirements matrix" not in bp:
        return False, "blueprint.md missing RRI Requirements matrix"
    if "Task decomposition preview" not in bp:
        return False, "blueprint.md missing Task decomposition preview"
    # Smoke evaluator on synthetic inputs.
    bp_path = tmp / "bp.md"
    rep_path = tmp / "rep.md"
    bp_path.write_text(
        "## 4a. RRI Requirements matrix\n\n"
        "| REQ-ID | Description | Section | Source | AC |\n"
        "|---|---|---|---|---|\n"
        "| REQ-001 | x | y | z | w |\n"
        "## 4b. Task decomposition preview\n",
        encoding="utf-8",
    )
    rep_path.write_text(
        "## 1. Requirement traceability matrix\n\n"
        "| REQ-ID | Description | Status | Evidence | Owner |\n"
        "|---|---|---|---|---|\n"
        "| REQ-001 | x | DONE | tests/foo.py | dev |\n",
        encoding="utf-8",
    )
    res = methodology.evaluate_verify_coverage(bp_path, rep_path)
    if res["gate"] != "PASS":
        return False, f"smoke gate FAIL: {res}"
    return True, "templates + evaluator OK"


def _probe_anti_patterns(tmp: Path) -> Tuple[bool, str]:
    """RRI-UX § 10 — 12 SaaS anti-patterns enumerated + checklist evaluator."""
    here = Path(__file__).resolve().parents[3]
    ref = (here / "references" / "32-rri-ux-critique.md").read_text(
        encoding="utf-8"
    )
    table_ids = sorted(set(re.findall(r"\|\s*(AP-\d{2})\s*\|", ref)))
    expected = [f"AP-{i:02d}" for i in range(1, 13)]
    if table_ids != expected:
        return False, f"reference list mismatch: {table_ids}"
    if len(methodology.ANTI_PATTERNS) != 12:
        return False, "ANTI_PATTERNS not 12"
    # Smoke gate
    res = methodology.evaluate_anti_patterns_checklist({"AP-01": True})
    if res["gate"] != "FAIL" or res["violations"] != 1:
        return False, f"smoke gate broken: {res}"
    res2 = methodology.evaluate_anti_patterns_checklist({})
    if res2["gate"] != "PASS":
        return False, f"empty smoke gate broken: {res2}"
    return True, "12/12 enumerated + evaluator OK"


def _probe_portfolio_saas_scaffolds(tmp: Path) -> Tuple[bool, str]:
    """v5 Pattern E + Pattern B — portfolio + saas scaffold presets."""
    from .. import scaffold_engine
    engine = scaffold_engine.ScaffoldEngine()
    names = {p.name for p in engine.list_presets()}
    if "portfolio" not in names:
        return False, "portfolio preset missing"
    if "saas" not in names:
        return False, "saas preset missing"
    # Apply both into tmp for full smoke.
    portfolio_target = tmp / "p"
    saas_target = tmp / "s"
    pr = engine.apply("portfolio", portfolio_target, "nextjs")
    sr = engine.apply("saas", saas_target, "nextjs")
    p_issues = engine.verify(pr)
    s_issues = engine.verify(sr)
    if p_issues:
        return False, f"portfolio verify fail: {p_issues}"
    if s_issues:
        return False, f"saas verify fail: {s_issues}"
    return True, f"presets={sorted(names)}"


def _probe_enterprise_module(tmp: Path) -> Tuple[bool, str]:
    """v5 Pattern F — `/vibe-module` workflow + probe + plan + refusal."""
    from .. import module_workflow
    here = Path(__file__).resolve().parents[3]
    cmd = _find_slash_command(here, "vibe-module.md")
    tpl = here / "assets" / "templates" / "module-spec.md"
    ref = here / "references" / "35-enterprise-module-pattern.md"
    if cmd is None:
        return False, "missing slash command vibe-module.md (looked in 5 paths)"
    if not tpl.exists():
        return False, f"missing template: {tpl}"
    if not ref.exists():
        return False, f"missing reference: {ref}"
    # Empty target refuses.
    empty = module_workflow.probe_existing_codebase(tmp)
    if empty.is_codebase:
        return False, "empty tmp probed as codebase"
    try:
        module_workflow.generate_module_plan("x", "y", empty)
    except module_workflow.EmptyCodebaseError:
        pass
    else:
        return False, "empty target did not raise EmptyCodebaseError"
    # Synthetic Next.js project plans correctly.
    (tmp / "package.json").write_text(
        '{"name":"x","version":"0.1.0","dependencies":{"next":"15.0.0"}}',
        encoding="utf-8",
    )
    (tmp / "tsconfig.json").write_text("{}", encoding="utf-8")
    probe = module_workflow.probe_existing_codebase(tmp)
    if "nextjs" not in probe.capabilities:
        return False, f"nextjs not detected: {probe.capabilities}"
    plan = module_workflow.generate_module_plan(
        "billing", "subscription", probe
    )
    if not any("app/billing/page.tsx" == f for f in plan.new_files):
        return False, f"plan missing nextjs route: {plan.new_files}"
    return True, "probe + plan + refusal OK"


def _probe_methodology_commands(tmp: Path) -> Tuple[bool, str]:
    """All 6 new VIBECODE-MASTER slash commands are declared in the manifest."""
    here = Path(__file__).resolve().parents[3]
    mani = here / "assets" / "plugin-manifest.json"
    if not mani.exists():
        return False, "manifest missing"
    data = json.loads(mani.read_text(encoding="utf-8"))
    names = {c["name"] for c in data.get("commands", [])}
    need = {"vibe-scan", "vibe-vision", "vibe-rri",
            "vibe-rri-t", "vibe-rri-ux", "vibe-rri-ui"}
    missing = sorted(need - names)
    return (not missing, f"missing: {missing}" if missing else f"present={sorted(need)}")


def _probe_docs_scaffold(tmp: Path) -> Tuple[bool, str]:
    """v0.11.1 / Pattern D — `docs` scaffold preset is registered + bootable."""
    from .. import scaffold_engine
    engine = scaffold_engine.ScaffoldEngine()
    names = {p.name for p in engine.list_presets()}
    if "docs" not in names:
        return False, f"docs preset missing; have={sorted(names)}"
    plan = engine.preview("docs", stack="nextjs", target_dir=str(tmp / "site"))
    needed = {"package.json", "next.config.mjs", "theme.config.tsx",
              "pages/index.mdx", "pages/intro/getting-started.mdx"}
    have = {f.rel_path for f in plan.files}
    missing = needed - have
    if missing:
        return False, f"docs preset missing files: {sorted(missing)}"
    return True, f"docs preset OK ({len(plan.files)} files)"


def _probe_style_tokens(tmp: Path) -> Tuple[bool, str]:
    """v0.11.2 / FIX-004 — references/34-style-tokens.md + FP/CP/VN sync."""
    from .. import methodology
    here = Path(__file__).resolve().parents[3]
    md = here / "references" / "34-style-tokens.md"
    if not md.exists():
        return False, f"missing reference: {md}"
    text = md.read_text(encoding="utf-8")
    # FP-01..FP-06 + CP-01..CP-06 must be enumerated.
    for prefix in ("FP-0", "CP-0"):
        for n in range(1, 7):
            tag = f"{prefix}{n}"
            if tag not in text:
                return False, f"34-style-tokens.md missing {tag}"
    # FIX-004: Vietnamese typography rules VN-01..VN-12 must appear.
    for n in range(1, 13):
        tag = f"VN-{n:02d}"
        if tag not in text:
            return False, f"34-style-tokens.md missing VN typography rule {tag}"
    if not (hasattr(methodology, "FONT_PAIRINGS")
            and hasattr(methodology, "COLOR_PSYCHOLOGY")):
        return False, "methodology missing FONT_PAIRINGS/COLOR_PSYCHOLOGY"
    if len(methodology.FONT_PAIRINGS) != 6 or len(methodology.COLOR_PSYCHOLOGY) != 6:
        return False, "expected 6 entries in FONT_PAIRINGS and COLOR_PSYCHOLOGY"
    return True, "ref-34 + methodology in sync (FP=6, CP=6, VN=12)"


def _probe_question_bank(tmp: Path) -> Tuple[bool, str]:
    """v0.11.2 / FIX-003 — bank meets thresholds × all personas × all modes."""
    from .. import methodology
    here = Path(__file__).resolve().parents[3]
    bank = here / "assets" / "rri-question-bank.json"
    if not bank.exists():
        return False, f"missing question bank: {bank}"
    data = json.loads(bank.read_text(encoding="utf-8"))
    types = data.get("project_types", {})
    thresholds = {
        "landing": 25, "saas": 50, "dashboard": 35, "blog": 25, "docs": 30,
        "portfolio": 25, "ecommerce": 40, "enterprise-module": 45, "custom": 15,
    }
    missing = set(thresholds) - set(types)
    if missing:
        return False, f"question bank missing types: {sorted(missing)}"
    valid_personas = set(methodology.VALID_RRI_PERSONAS)
    valid_modes = set(methodology.VALID_RRI_MODES)
    for project, minimum in thresholds.items():
        qs = types[project].get("questions", [])
        if len(qs) < minimum:
            return False, f"{project}: {len(qs)} q < threshold {minimum}"
        for q in qs:
            if q.get("persona") not in valid_personas:
                return False, f"{project}: invalid persona in {q.get('id')}"
            if q.get("mode") not in valid_modes:
                return False, f"{project}: invalid mode in {q.get('id')}"
    if not hasattr(methodology, "load_rri_questions"):
        return False, "methodology.load_rri_questions() not exported"
    saas_dev_guided = methodology.load_rri_questions(
        "saas", persona="developer", mode="GUIDED")
    if len(saas_dev_guided) == 0:
        return False, "saas/developer/GUIDED filter returned 0 questions"
    return True, (f"bank+loader OK (9 project types, "
                  f"saas={len(types['saas']['questions'])} q, "
                  f"dev/GUIDED={len(saas_dev_guided)} q, all personas+modes valid)")


def _probe_copy_patterns(tmp: Path) -> Tuple[bool, str]:
    """v0.11.2 / FIX-005 — references/36-copy-patterns.md + COPY_PATTERNS sync."""
    from .. import methodology
    here = Path(__file__).resolve().parents[3]
    md = here / "references" / "36-copy-patterns.md"
    if not md.exists():
        return False, f"missing reference: {md}"
    text = md.read_text(encoding="utf-8")
    for n in range(1, 10):
        tag = f"CF-{n:02d}"
        if tag not in text:
            return False, f"36-copy-patterns.md missing {tag}"
    for n in range(1, 9):
        tag = f"CF-VN-{n:02d}"
        if tag not in text:
            return False, f"36-copy-patterns.md missing {tag}"
    if not (hasattr(methodology, "COPY_PATTERNS")
            and hasattr(methodology, "COPY_PATTERNS_VN")):
        return False, "methodology missing COPY_PATTERNS / COPY_PATTERNS_VN"
    if len(methodology.COPY_PATTERNS) != 9:
        return False, f"COPY_PATTERNS count {len(methodology.COPY_PATTERNS)} != 9"
    if len(methodology.COPY_PATTERNS_VN) != 8:
        return False, f"COPY_PATTERNS_VN count {len(methodology.COPY_PATTERNS_VN)} != 8"
    return True, "ref-36 + methodology in sync (CF=9, CF-VN=8)"


def _probe_stack_recommendations(tmp: Path) -> Tuple[bool, str]:
    """v0.11.2 / FIX-002 — methodology.PROJECT_STACK_RECOMMENDATIONS coverage."""
    from .. import methodology
    if not hasattr(methodology, "PROJECT_STACK_RECOMMENDATIONS"):
        return False, "methodology.PROJECT_STACK_RECOMMENDATIONS missing"
    if not hasattr(methodology, "recommend_stack"):
        return False, "methodology.recommend_stack() missing"
    expected = {"landing", "saas", "dashboard", "blog", "docs", "portfolio",
                "ecommerce", "mobile", "api", "enterprise-module", "custom"}
    have = set(methodology.PROJECT_STACK_RECOMMENDATIONS.keys())
    missing = expected - have
    if missing:
        return False, f"stack recommendations missing: {sorted(missing)}"
    rec = methodology.recommend_stack("saas")
    for k in ("framework", "styling", "state_data", "auth", "hosting", "extras"):
        if k not in rec:
            return False, f"recommend_stack missing key {k!r}"
    fallback = methodology.recommend_stack("totally-unknown-type")
    if not fallback.get("unknown"):
        return False, "recommend_stack should mark unknown types as fallback"
    return True, f"recommend_stack OK ({len(have)} canonical types + alias + safe fallback)"


def _probe_docs_intent_routing(tmp: Path) -> Tuple[bool, str]:
    """v0.11.2 / FIX-001 — intent_router classifies docs prose to BUILD."""
    from .. import intent_router
    r = intent_router.IntentRouter()
    cases = (
        "build docs site cho team kỹ thuật",
        "tạo trang tài liệu cho sản phẩm",
        "create developer documentation",
    )
    for prose in cases:
        match = r.classify(prose)
        if "BUILD" not in match.intents:
            return False, f"docs prose {prose!r} did not route to BUILD: {match.intents}"
    return True, f"docs intent routes to BUILD ({len(cases)}/{len(cases)})"
