#!/usr/bin/env python3
"""Example: parse 3 ad-hoc tool-use formats produced by upstream LLMs.

Run from the repo root:
    PYTHONPATH=./scripts python examples/07_tool_use_parser.py

Demonstrates ``vibecodekit.tool_use_parser.parse_tool_uses``: tolerant
parser for ad-hoc tool-call payloads when the orchestrator does not
go through the standard ``query_loop`` path.

Three input shapes:
  1. Raw JSON array of ``{tool, input}`` blocks.
  2. Embedded ``<tool name="...">{ ... }</tool>`` tag (regex form).
  3. Mixed prose with multiple tag occurrences.
"""
from vibecodekit.tool_use_parser import parse_tool_uses


CASES = [
    (
        "JSON array",
        '[{"tool": "read", "input": {"path": "README.md"}}, '
        ' {"tool": "grep", "input": {"pattern": "TODO"}}]',
    ),
    (
        "Single <tool> tag",
        'Tôi sẽ kiểm tra file: <tool name="read">{"path": "config.yaml"}</tool>',
    ),
    (
        "Multiple <tool> tags + prose",
        'Step 1: <tool name="grep">{"pattern": "FIXME", "path": "src/"}</tool>\n'
        'Step 2: <tool name="bash">{"cmd": "pytest -q"}</tool>\n'
        'Báo cáo lỗi nếu có.',
    ),
]


if __name__ == "__main__":
    for label, payload in CASES:
        print(f"--- {label} ---")
        blocks = parse_tool_uses(payload)
        if not blocks:
            print("  (không tìm thấy tool-call nào)")
        for i, block in enumerate(blocks, 1):
            print(f"  [{i}] tool={block['tool']!r}  input={block['input']!r}")
        print()

    # Sanity check: each example produced ≥ 1 block.
    assert all(parse_tool_uses(p) for _, p in CASES)
    # Empty input → empty list.
    assert parse_tool_uses("") == []
    assert parse_tool_uses("just prose, no tool tags") == []

    print("OK")
