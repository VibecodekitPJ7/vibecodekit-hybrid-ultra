# Examples

Standalone scripts demonstrating core VibecodeKit capabilities.
**No network, no LLM, no Claude Code required.**

## Quick start

```bash
git clone https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra

# All-in-one demo (< 2 seconds):
PYTHONPATH=./scripts python -m vibecodekit.cli demo

# Or run individual examples:
PYTHONPATH=./scripts python examples/01_permission_engine.py
PYTHONPATH=./scripts python examples/02_scaffold_preview.py
PYTHONPATH=./scripts python examples/03_mcp_selfcheck.py
PYTHONPATH=./scripts python examples/04_vn_faker.py
PYTHONPATH=./scripts python examples/05_vn_error_translator.py
PYTHONPATH=./scripts python examples/06_quality_gate.py
PYTHONPATH=./scripts python examples/07_tool_use_parser.py
PYTHONPATH=./scripts python examples/08_worktree_executor.py
```

## What each example does

| Script | Description |
|--------|-------------|
| `01_permission_engine.py` | Classify 20 shell commands through the 6-layer permission pipeline |
| `02_scaffold_preview.py` | List and preview all 11 scaffold presets across available stacks |
| `03_mcp_selfcheck.py` | Call the bundled MCP selfcheck server via in-process transport |
| `04_vn_faker.py` | Generate a Vietnamese user profile + 3-SKU shop catalog (deterministic, ``seed=42``) |
| `05_vn_error_translator.py` | Translate 3 common Python errors to Vietnamese with fix suggestions |
| `06_quality_gate.py` | Run the 7-dimension × 8-axis release gate on a sample scorecard (PASS + FAIL scenario) |
| `07_tool_use_parser.py` | Parse 3 ad-hoc tool-use formats (JSON array, single ``<tool>`` tag, mixed prose) |
| `08_worktree_executor.py` | Spawn an isolated git worktree (Pattern #8) on a temp repo, then clean up |

## All-in-one demo

`vibe demo` runs 6 steps in sequence:

1. **Doctor** — health-check the project layout
2. **Permission Engine** — classify 5 commands (allow/deny)
3. **Conformance Audit** — run 87 internal regression probes
4. **Scaffold Preview** — preview the `api-todo` preset
5. **Intent Router** — classify 3 free-form phrases to slash commands
6. **MCP Selfcheck** — ping the bundled MCP server
