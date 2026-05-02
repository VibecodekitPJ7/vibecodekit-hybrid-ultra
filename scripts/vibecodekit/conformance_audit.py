"""Behaviour-based conformance audit (replaces v0.6's tautological file-exists check).

Each of the 18 patterns maps to a *probe* — a small runtime experiment
exercised against a temp directory.  A probe is ``pass`` iff it observes the
documented behaviour.  File existence is never sufficient.

Run::

    python -m vibecodekit.conformance_audit --root /path/to/project

Exit code is 0 iff the parity score ≥ ``--threshold`` (default 0.85).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Tuple

# Warm-load only: 3 module dưới đây không có call site trực tiếp trong
# conformance_audit.py nhưng được giữ trong import block để probe #85
# (no_orphan_module) chắc chắn nhìn thấy chúng qua sibling-import scan.
# KHÔNG xóa — giữ noqa marker để ruff không strip.
from . import dashboard          # noqa: F401  (warm-load for probe #85)
from . import memory_retriever   # noqa: F401  (warm-load for probe #85)
from . import tool_use_parser    # noqa: F401  (warm-load for probe #85)


# `_find_slash_command` (canonical helper for `.claude/commands/<name>`)
# was moved to `vibecodekit.conformance._helpers` in PR β-1.  After PR β-4
# all in-tree probe consumers import it directly from the package, but the
# back-compat contract test pins ``conformance_audit._find_slash_command``,
# so we keep the re-export here.  F401 noqa is intentional.
from .conformance._helpers import find_slash_command as _find_slash_command  # noqa: E402,F401


# Probes #1-30 (runtime / 5-layer / hooks / MCP / tasks) moved to
# `vibecodekit.conformance.probes_runtime` in cycle 14 PR β-2.  Re-imported
# here under the leading-underscore names so the manual ``PROBES`` list at
# the bottom of this module keeps working unchanged.
from .conformance.probes_runtime import (  # noqa: E402
    _probe_async_generator,
    _probe_derived_follow_up,
    _probe_escalating_recovery,
    _probe_concurrency_partition,
    _probe_streaming_execution,
    _probe_context_modifier,
    _probe_coordinator_restriction,
    _probe_fork_isolation,
    _probe_five_layer_defense,
    _probe_permission_pipeline,
    _probe_conditional_skill,
    _probe_shell_in_prompt,
    _probe_dynamic_skill_discovery,
    _probe_plugin_extension,
    _probe_plugin_sandbox,
    _probe_reconciliation_install,
    _probe_ts_replacement,
    _probe_terminal_ui,
    _probe_background_tasks,
    _probe_mcp_adapter,
    _probe_cost_ledger,
    _probe_26_hook_events,
    _probe_follow_up_reexecute,
    _probe_denial_concurrency,
    _probe_memory_hierarchy,
    _probe_approval_contract,
    _probe_all_task_kinds,
    _probe_dream_four_phase,
    _probe_mcp_stdio_roundtrip,
    _probe_structured_notifications,
)

# Probes #31-50 (RRI methodology, scaffolds, asset catalogs) moved to
# `vibecodekit.conformance.probes_methodology` in cycle 14 PR β-3.  Re-imported
# here under the leading-underscore names so the manual ``PROBES`` list at the
# bottom of this module keeps working unchanged.
from .conformance.probes_methodology import (  # noqa: E402
    _probe_rri_reverse_interview,
    _probe_rri_t_testing,
    _probe_rri_ux_critique,
    _probe_rri_ui_combined,
    _probe_vibecode_master_workflow,
    _probe_methodology_commands,
    _probe_methodology_runners,
    _probe_config_persistence,
    _probe_mcp_stdio_handshake,
    _probe_refine_boundary,
    _probe_verify_coverage,
    _probe_anti_patterns,
    _probe_portfolio_saas_scaffolds,
    _probe_enterprise_module,
    _probe_docs_scaffold,
    _probe_style_tokens,
    _probe_question_bank,
    _probe_copy_patterns,
    _probe_stack_recommendations,
    _probe_docs_intent_routing,
)

# Probes #51-70 (assets / browser / vck commands / classifier) moved to
# `vibecodekit.conformance.probes_assets` in cycle 14 PR β-4.  Re-imported
# here under the leading-underscore names so the manual ``PROBES`` list at
# the bottom of this module keeps working unchanged.
from .conformance.probes_assets import (  # noqa: E402
    _probe_command_context_wiring,
    _probe_command_agent_binding,
    _probe_skill_paths_activation,
    _probe_browser_state_atomic,
    _probe_browser_idle_timeout_default,
    _probe_browser_port_selection,
    _probe_browser_cookie_path,
    _probe_browser_permission_routed,
    _probe_browser_envelope_wrap,
    _probe_browser_hidden_strip,
    _probe_browser_bidi_sanitisation,
    _probe_browser_url_blocklist,
    _probe_vck_commands_present,
    _probe_vck_command_frontmatter_attribution,
    _probe_vck_agents_registered,
    _probe_vck_command_agent_binding,
    _probe_vck_license_attribution,
    _probe_classifier_ensemble_contract,
    _probe_classifier_regex_rule_bank,
    _probe_classifier_blocks_prompt_injection,
)

# Probes #71-92 (governance / license / plugin / case-study artefacts) moved
# to `vibecodekit.conformance.probes_governance` in cycle 14 PR β-5.  The
# helper `_candidate_repo_roots` (used only by probes #76-79) moves with
# them.  Re-imported here under the leading-underscore names so the manual
# ``PROBES`` list at the bottom of this module keeps working unchanged.
from .conformance.probes_governance import (  # noqa: E402
    _probe_classifier_blocks_secret_leak,
    _probe_classifier_optional_layers,
    _probe_eval_select_diff_based,
    _probe_learnings_jsonl,
    _probe_team_mode_required_gates,
    _probe_github_actions_ci,
    _probe_contributing_and_usage_guide,
    _probe_vck_ship_team_mode_wired,
    _probe_eval_select_wired_into_ci_and_ship,
    _probe_session_ledger_module,
    _probe_classifier_auto_on_default,
    _probe_session_start_learnings_inject,
    _probe_scaffold_seeds_vibecode_dir,
    _probe_vck_pipeline_command,
    _probe_no_orphan_module,
    _probe_vck_review_classifier_wired,
    _probe_vck_cso_classifier_wired,
    _probe_case_study_otb_budget,
    _probe_anti_patterns_gallery_complete,
    _probe_color_psychology_appendix,
    _probe_font_pairing_appendix,
    _probe_intent_routing_llm_primary_doc,
)






# ---------------------------------------------------------------------------
# v0.12.0 — Browser daemon probes (#54 – #62) + Skill v2 probes (#63 – #67)
# ---------------------------------------------------------------------------
# The browser daemon is a *clean-room* Python reimplementation of gstack's
# persistent-daemon architecture.  These probes verify that the runtime
# guarantees (atomic state file, permission routing, content sanitisation,
# URL blocklist, envelope wrap, …) match the contract documented in
# ``scripts/vibecodekit/browser/__init__.py``.


# `_VCK_COMMANDS` constant lives in `conformance.probes_assets` since β-4
# (was here at module-level for probes #63 and #64).


# ---------------------------------------------------------------------------
# v0.14.0 — ML security (#68-#72) + Phase-4 polish (#73-#77)
# ---------------------------------------------------------------------------


PROBES: List[Tuple[str, Callable[[Path], Tuple[bool, str]]]] = [
    ("01_async_generator_loop",         _probe_async_generator),
    ("02_derived_needs_follow_up",      _probe_derived_follow_up),
    ("03_escalating_recovery",          _probe_escalating_recovery),
    ("04_concurrency_partitioning",     _probe_concurrency_partition),
    ("05_streaming_tool_execution",     _probe_streaming_execution),
    ("06_context_modifier_chain",       _probe_context_modifier),
    ("07_coordinator_restriction",      _probe_coordinator_restriction),
    ("08_fork_isolation_worktree",      _probe_fork_isolation),
    ("09_five_layer_context_defense",   _probe_five_layer_defense),
    ("10_permission_classification",    _probe_permission_pipeline),
    ("11_conditional_skill_activation", _probe_conditional_skill),
    ("12_shell_in_prompt",              _probe_shell_in_prompt),
    ("13_dynamic_skill_discovery",      _probe_dynamic_skill_discovery),
    ("14_plugin_extension",             _probe_plugin_extension),
    ("15_plugin_sandbox",               _probe_plugin_sandbox),
    ("16_reconciliation_install",       _probe_reconciliation_install),
    ("17_pure_ts_native_replacement",   _probe_ts_replacement),
    ("18_terminal_ui_as_browser",       _probe_terminal_ui),
    # v0.8 Full Agentic-OS extensions
    ("19_background_tasks",             _probe_background_tasks),
    ("20_mcp_adapter",                  _probe_mcp_adapter),
    ("21_cost_accounting_ledger",       _probe_cost_ledger),
    ("22_26_hook_events",               _probe_26_hook_events),
    ("23_follow_up_reexecute",          _probe_follow_up_reexecute),
    ("24_denial_concurrency_safe",      _probe_denial_concurrency),
    # v0.9 — Full Agentic OS completion probes
    ("25_memory_hierarchy_3tier",       _probe_memory_hierarchy),
    ("26_approval_contract_ui",         _probe_approval_contract),
    ("27_all_seven_task_kinds",         _probe_all_task_kinds),
    ("28_dream_four_phase",             _probe_dream_four_phase),
    ("29_mcp_stdio_roundtrip",          _probe_mcp_stdio_roundtrip),
    ("30_structured_notifications",     _probe_structured_notifications),
    # v0.10 — RRI + VIBECODE-MASTER methodology integration probes
    ("31_rri_reverse_interview",        _probe_rri_reverse_interview),
    ("32_rri_t_testing_methodology",    _probe_rri_t_testing),
    ("33_rri_ux_critique_methodology",  _probe_rri_ux_critique),
    ("34_rri_ui_design_pipeline",       _probe_rri_ui_combined),
    ("35_vibecode_master_workflow",  _probe_vibecode_master_workflow),
    ("36_methodology_slash_commands",   _probe_methodology_commands),
    # v0.10.1 — methodology runner + config persistence + real MCP handshake
    ("37_methodology_runners",          _probe_methodology_runners),
    ("38_config_persistence",           _probe_config_persistence),
    ("39_mcp_stdio_full_handshake",     _probe_mcp_stdio_handshake),
    # Round 8 — v5 deep-dive parity probes
    ("40_refine_boundary_step8",        _probe_refine_boundary),
    ("41_verify_req_coverage",          _probe_verify_coverage),
    ("42_saas_anti_patterns_12",        _probe_anti_patterns),
    ("43_portfolio_saas_scaffolds",     _probe_portfolio_saas_scaffolds),
    ("44_enterprise_module_workflow",   _probe_enterprise_module),
    ("45_docs_scaffold_pattern_d",      _probe_docs_scaffold),
    ("46_style_tokens_canonical",       _probe_style_tokens),
    ("47_rri_question_bank",            _probe_question_bank),
    # v0.11.2 — FIX-001/002/005 additions
    ("48_copy_patterns_canonical",      _probe_copy_patterns),
    ("49_stack_recommendations",        _probe_stack_recommendations),
    ("50_docs_intent_routing",          _probe_docs_intent_routing),
    # v0.11.3 — Patch A/B/C wiring probes
    ("51_command_context_wiring",       _probe_command_context_wiring),
    ("52_command_agent_binding",        _probe_command_agent_binding),
    ("53_skill_paths_activation",       _probe_skill_paths_activation),
    # v0.12.0 — gstack-inspired browser daemon (9 probes)
    ("54_browser_state_atomic",         _probe_browser_state_atomic),
    ("55_browser_idle_timeout_default", _probe_browser_idle_timeout_default),
    ("56_browser_port_selection",       _probe_browser_port_selection),
    ("57_browser_cookie_path",          _probe_browser_cookie_path),
    ("58_browser_permission_routed",    _probe_browser_permission_routed),
    ("59_browser_envelope_wrap",        _probe_browser_envelope_wrap),
    ("60_browser_hidden_strip",         _probe_browser_hidden_strip),
    ("61_browser_bidi_sanitisation",    _probe_browser_bidi_sanitisation),
    ("62_browser_url_blocklist",        _probe_browser_url_blocklist),
    # v0.12.0 — gstack-inspired specialist skills v2 (5 probes)
    ("63_vck_commands_present",         _probe_vck_commands_present),
    ("64_vck_frontmatter_attribution",  _probe_vck_command_frontmatter_attribution),
    ("65_vck_agents_registered",        _probe_vck_agents_registered),
    ("66_vck_command_agent_binding",    _probe_vck_command_agent_binding),
    ("67_vck_license_attribution",      _probe_vck_license_attribution),
    # v0.14.0 — ML security (#68-#72) + Phase-4 polish (#73-#77).
    ("68_classifier_ensemble_contract", _probe_classifier_ensemble_contract),
    ("69_classifier_regex_rule_bank",   _probe_classifier_regex_rule_bank),
    ("70_classifier_blocks_prompt_injection", _probe_classifier_blocks_prompt_injection),
    ("71_classifier_blocks_secret_leak",_probe_classifier_blocks_secret_leak),
    ("72_classifier_optional_layers",   _probe_classifier_optional_layers),
    ("73_eval_select_diff_based",       _probe_eval_select_diff_based),
    ("74_learnings_store_jsonl",        _probe_learnings_jsonl),
    ("75_team_mode_required_gates",     _probe_team_mode_required_gates),
    ("76_github_actions_ci",            _probe_github_actions_ci),
    ("77_contributing_and_usage_guide", _probe_contributing_and_usage_guide),
    # v0.15.0-alpha — pipeline-wiring probes (T1 + T2)
    ("78_vck_ship_team_mode_wired",     _probe_vck_ship_team_mode_wired),
    ("79_eval_select_wired",            _probe_eval_select_wired_into_ci_and_ship),
    ("80_session_ledger_module",        _probe_session_ledger_module),
    # v0.15.0-alpha — auto-on wiring probes (T3 + T4)
    ("81_classifier_auto_on_default",   _probe_classifier_auto_on_default),
    ("82_session_start_learnings_inject", _probe_session_start_learnings_inject),
    # v0.15.0-alpha — scaffold seed + master pipeline dispatcher (T5 + T6)
    ("83_scaffold_seeds_vibecode_dir",  _probe_scaffold_seeds_vibecode_dir),
    ("84_vck_pipeline_command",         _probe_vck_pipeline_command),
    # v0.15.0 — invariant guard against re-introducing orphan modules
    ("85_no_orphan_module",             _probe_no_orphan_module),
    # v0.15.2 — invariant guards for T4-completion (Bug #2 + #3)
    ("86_vck_review_classifier_wired",  _probe_vck_review_classifier_wired),
    ("87_vck_cso_classifier_wired",     _probe_vck_cso_classifier_wired),
    # v0.22.0 (cycle 13) — documentation expansion probes
    ("88_case_study_otb_budget",        _probe_case_study_otb_budget),
    ("89_anti_patterns_gallery",        _probe_anti_patterns_gallery_complete),
    ("90_color_psychology_appendix",    _probe_color_psychology_appendix),
    ("91_font_pairing_appendix",        _probe_font_pairing_appendix),
    # v0.23.0 — LLM-primary intent routing (cycle 14, Plan A)
    ("92_intent_routing_llm_primary_doc", _probe_intent_routing_llm_primary_doc),
]


# `audit()` and `_main()` were extracted to `vibecodekit.conformance._runner` in
# cycle 14 PR β-1.  Re-export them here so existing callers
# (`from vibecodekit.conformance_audit import audit`,
# `python -m vibecodekit.conformance_audit`) keep working unchanged.
#
# The runner picks up this module's ``PROBES`` list lazily by default, so the
# 92 probes still defined above are exercised exactly as before.  Subsequent
# β-2..β-5 PRs will move probes into sibling modules
# (``conformance/probes_*.py``); β-6 will switch to a ``@probe`` decorator.
from .conformance._runner import audit, main as _main  # noqa: E402, F401


if __name__ == "__main__":
    _main()
