"""Behaviour-based conformance audit (replaces v0.6's tautological file-exists check).

Each of the 95 patterns in the methodology maps to a *probe* — a small
runtime experiment exercised against a temp directory.  A probe is
``pass`` iff it observes the documented behaviour.  File existence is
never sufficient.

Run::

    python -m vibecodekit.conformance_audit --root /path/to/project

Exit code is 0 iff the parity score ≥ ``--threshold`` (default 0.85).

Layout (post-cycle 14 PR β-6)
=============================

The audit machinery lives in the ``vibecodekit.conformance`` package
(see its ``__init__.py``):

  ``conformance/_runner.py``        – ``audit()`` + CLI ``main()``
  ``conformance/_registry.py``      – ``@probe`` decorator + registry
  ``conformance/_helpers.py``       – ``find_slash_command``
  ``conformance/probes_runtime.py``     – probes #01-30 (runtime / hooks / MCP)
  ``conformance/probes_methodology.py`` – probes #31-50 (RRI / scaffolds / assets)
  ``conformance/probes_assets.py``      – probes #51-70 (browser / vck / classifier)
  ``conformance/probes_governance.py``  – probes #71-95 (security / case-studies / design-tokens)

This module is a **back-compat shim**.  Existing callers that do
``from vibecodekit.conformance_audit import PROBES`` or
``from vibecodekit.conformance_audit import _probe_<name>`` keep
working unchanged.  The manual ``PROBES`` list (manually maintained
across v0.6 → v0.22) is now a snapshot of the decorator-based registry,
sorted by canonical probe-id (``"01_…"`` through ``"92_…"``) so external
orderings are preserved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Tuple

# Warm-load only: the 3 modules below have no direct call-site here, but
# probe #85 (`_probe_no_orphan_module`) verifies that every public-ish
# ``vibecodekit/*.py`` module is referenced from somewhere.  Importing
# them here gives the sibling-import scan something to find.  Do NOT
# remove — keep the F401 noqa marker so ruff does not strip them.
from . import dashboard          # noqa: F401  (warm-load for probe #85)
from . import memory_retriever   # noqa: F401  (warm-load for probe #85)
from . import tool_use_parser    # noqa: F401  (warm-load for probe #85)


# `_find_slash_command` (canonical helper for `.claude/commands/<name>`)
# was moved to `vibecodekit.conformance._helpers` in PR β-1.  After PR β-4
# all in-tree probe consumers import it directly from the package, but the
# back-compat contract test pins ``conformance_audit._find_slash_command``,
# so we keep the re-export here.  F401 noqa is intentional.
from .conformance._helpers import find_slash_command as _find_slash_command  # noqa: E402,F401

# Importing the probe modules executes each ``@probe(...)`` decorator,
# populating the global registry.  The explicit re-imports below pin
# every probe under its leading-underscore name on this module so
# external callers keep working unchanged.
from .conformance.probes_runtime import (  # noqa: E402, F401
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
from .conformance.probes_methodology import (  # noqa: E402, F401
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
from .conformance.probes_assets import (  # noqa: E402, F401
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
from .conformance.probes_governance import (  # noqa: E402, F401
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
    _probe_tailwind_prewire_design_tokens,
    _probe_design_tokens_files_shipped,
    _probe_shadcn_samples_ship,
)

# Build the canonical ``PROBES`` list lazily from the registry, sorted
# by probe-id so the row-by-row output of ``python -m vibecodekit
# .conformance_audit`` matches v0.22.x exactly (``"01_…"`` first,
# ``"95_…"`` last).  Any future probe added with
# ``@probe(id, group=...)`` automatically lands in this list — no manual
# edit required.  This replaces the ~110-line manual ``PROBES`` block
# that lived here through v0.22.x.
from .conformance._registry import collect_registered  # noqa: E402

PROBES: List[Tuple[str, Callable[[Path], Tuple[bool, str]]]] = sorted(
    collect_registered(),
    key=lambda row: row[0],
)


# `audit()` and `_main()` continue to live in `conformance._runner`.
# The runner pulls from the same registry by default — the ``PROBES``
# list above is exposed only for back-compat with external callers (we
# no longer pass it explicitly).
from .conformance._runner import audit, main as _main  # noqa: E402, F401


if __name__ == "__main__":
    _main()
