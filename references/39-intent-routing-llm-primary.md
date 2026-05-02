# 39 — Intent routing: LLM-primary with Python keyword fallback

> **Status:** active (since v0.23.0)
> **Supersedes:** §16.1 of `USAGE_GUIDE.md` keyword-only description
> **Related:** `references/00-overview.md`, `.claude/commands/vibe.md`, `scripts/vibecodekit/intent_router.py`
> **Audit probe:** `92_intent_routing_llm_primary_doc`

This reference is the canonical design log for how the `/vibe <prose>` master command resolves free-form prose to one or more `/vibe-*` slash commands.

It is also the formal write-up of the architectural change introduced by Plan A (PR α-1, α-2, α-3) of cycle 14, in response to user feedback that the prior keyword-only router was "reinventing the wheel kém hơn" than letting the host LLM (Claude Code, Cursor, Codex) do the classification natively.

---

## 1 · Problem

Pre-v0.23.0 the routing pipeline for `/vibe <prose>` was:

```
User prose                                          (interactive)
   │
   ▼
Claude Code reads .claude/commands/vibe.md
   │  (the slash command body says: run the bash invocation)
   ▼
python -m vibecodekit.cli intent route "<prose>"
   │  (Python keyword router does the classification)
   ▼
List of /vibe-* commands
   │
   ▼
Claude Code dispatches them one by one
```

The Python keyword router (`scripts/vibecodekit/intent_router.py`) is a 642-line module that:

- Holds 14 intents × 5–25 hand-curated trigger phrases each (~140 phrases total).
- Normalises prose by lowercasing + stripping Vietnamese diacritics.
- Counts substring matches per intent and applies the score formula `min(1.0, 0.4 + 0.05·#matched + 0.01·longest)`.
- Picks intents above a `HIGH_CONF` threshold (default 0.55), or asks a Clarification when below `LOW_CONF` (0.30).

**This worked, but it was strictly worse than letting Claude do the classification.** Claude has been trained on millions of intent-classification examples, speaks Vietnamese natively, understands conversational context (recent messages, user's open files, the active repo), and can handle unbounded synonym variants. The Python router, by contrast:

- Is **brittle** — every new VN phrasing requires a source-code patch.
- Is **stateless** — it does not see the recent conversation, so prose like "ship đi" loses the prior-turn context.
- Is **synonym-blind** — "đẻ ra cho tao 1 trang" (a colloquial VN way of saying "build me a page") matches none of the BUILD triggers.
- Has only ~140 enumerated phrases vs Claude's millions of training examples.

The user critique was fair: for the **interactive** use-case where the host LLM is already in the loop, delegating classification to a 142-phrase keyword table is a strict downgrade in semantic understanding.

---

## 2 · Design

The fix is **not** to delete the Python keyword router — it remains useful for several non-LLM use-cases. Instead, we **invert the priority**:

```
User prose                                          (interactive)
   │
   ▼
Claude Code reads .claude/commands/vibe.md
   │  (the slash command body now says: classify directly using the
   │   intent table; only fall back to Python if you're unsure)
   ▼
Claude classifies the prose using its native NLP
   │  (steps documented inline in vibe.md as a 14-row "When to pick" table)
   ▼
List of /vibe-* commands
   │
   ▼
Claude Code dispatches them one by one
                          ┊
                          ▼ (only when Claude is unsure)
                     python -m vibecodekit.cli intent route "<prose>"
                          │
                          ▼
                     Deterministic keyword classification (the old path)
```

### 2.1 · Where the keyword router still pulls its weight

The Python `IntentRouter` stays in the codebase as the **canonical fallback** and **programmatic API** for four use-cases that interactive Claude does not cover:

| Use-case | Why the LLM is not enough |
|:---------|:--------------------------|
| **CLI / batch jobs** | A shell script running `vibe intent route "<prose>"` has no LLM available. |
| **CI / golden tests** | Tests need deterministic output; LLMs introduce drift across versions. |
| **MCP server** | `mcp_servers/core.py` exposes the router to MCP clients that may dispatch their own way. |
| **Privacy / offline** | The keyword router never sends the prose anywhere; the LLM path may forward it to a vendor. |

The Python class also serves as a **regression-detection tool** — when the LLM's classification diverges sharply from the keyword router's output, that's a useful signal during golden-test runs.

### 2.2 · Trade-off matrix

| Tiêu chí                          | Keyword router (fallback) | Host LLM (primary)                |
|:----------------------------------|:---------------------------|:----------------------------------|
| Semantic understanding            | Brittle (phrase list)      | **Excellent** (already understands prose) |
| Determinism                       | **100 %**                  | ~95 % (needs `temperature=0`)     |
| Latency                           | **<1 ms**                  | 200–2 000 ms (LLM call)           |
| Cost per dispatch                 | **$0**                     | $0.001–0.01                       |
| Offline / no API key              | **Yes**                    | No                                |
| Privacy (prose stays local)       | **Yes**                    | Depends on host LLM               |
| Adding a new intent               | Edit Python source         | **Update prompt list**            |
| Multi-language out of the box     | Hand-enumerate VN+EN       | **Native** (LLM speaks 50+)       |
| Synonym handling                  | Brittle                    | **Excellent**                     |
| Conversation context              | None                       | **Full**                          |
| Golden-test stability             | **Stable**                 | Drifts across LLM versions        |
| MCP / non-LLM client support      | **Yes**                    | Needs a fallback chain            |

---

## 3 · The 14 intents

Both paths use the same 14-intent vocabulary (canonical pipeline order):

| #  | Intent      | Slash command       | When to pick                                                  |
|:---|:------------|:--------------------|:--------------------------------------------------------------|
| 1  | `SCAN`      | `/vibe-scan`        | repo exploration, security scan, needs-discovery              |
| 2  | `VISION`    | `/vibe-vision`      | brand, design vision, concept, định hướng                     |
| 3  | `RRI`       | `/vibe-rri`         | reverse-interview requirements, verify yêu cầu                |
| 4  | `RRI-T`     | `/vibe-rri-t`       | testing matrix, stress axes, ma trận test                     |
| 5  | `RRI-UX`    | `/vibe-rri-ux`      | UX flow, flow-physics, luồng người dùng                       |
| 6  | `RRI-UI`    | `/vibe-rri-ui`      | UI design system, design tokens, thiết kế UI                  |
| 7  | `BUILD`     | `/vibe-scaffold`    | scaffold project, build app, tạo dự án                        |
| 8  | `VERIFY`    | `/vibe-verify`      | adversarial QA gate, audit chất lượng, kiểm tra code          |
| 9  | `SHIP`      | `/vibe-ship`        | deploy, release, lên production, ra mắt                       |
| 10 | `MAINTAIN`  | `/vibe-task`        | upgrade dependency, refactor, nâng cấp, fix lỗi               |
| 11 | `ADVISOR`   | `/vibe-tip`         | architecture advice, tư vấn kiến trúc, hỏi best practice      |
| 12 | `MEMORY`    | `/vibe-memory`      | update CLAUDE.md, ghi nhớ, retrieve memory                    |
| 13 | `DOCTOR`    | `/vibe-doctor`      | health check, chẩn đoán môi trường, overlay sanity            |
| 14 | `DASHBOARD` | `/vibe-dashboard`   | runtime event summary, xem dashboard                          |

(The full set of 30+ intents — including `REFINE`, `MODULE`, `INSTALL`, the VCK-* specialist commands — lives in `_INTENT_TO_SLASH` inside `intent_router.py` for completeness.)

### 3.1 · Pipeline expansion

If the prose describes a holistic build goal — phrases like "shop online", "landing page", "ra mắt sản phẩm", "build me an MVP" — both paths expand to the canonical pipeline:

```
SCAN → VISION → RRI → BUILD → VERIFY
```

That fan-out is implemented in `_PIPELINE_TRIGGERS` (Python) and described under "Pipeline expansion" in `vibe.md` (LLM).

---

## 4 · Migration notes

### 4.1 · Back-compat guarantee

The Python `IntentRouter` class API is **frozen** for v0.23.0 → v1.0.0:

```python
from vibecodekit.intent_router import IntentRouter
r = IntentRouter()
match = r.classify("làm cho tôi shop online")  # IntentMatch | Clarification
slash_cmds = r.route(match)                     # list[str]
human_explain = r.explain(match)                # str
```

No call site needs to change. `cli.py` (`intent classify`, `intent route`), `mcp_servers/core.py`, and the four router-related test modules all continue to work without modification.

### 4.2 · What changed visibly

- **`.claude/commands/vibe.md`** — rewritten to instruct the host LLM to classify directly (PR α-1, +106 / −36).
- **`update-package/.claude/commands/vibe.md`** — same rewrite, this is the canonical copy shipped to consumers.
- **`scripts/vibecodekit/intent_router.py` docstring** — fixed the long-standing claim that the router used `HashEmbeddingBackend` cosine similarity (it never did), updated the doctest example to reflect the real `_INTENT_TO_SLASH` mapping (PR α-2).
- **`tests/test_intent_router_docstring_contract.py`** — new contract test (5 cases) that asserts the docstring matches the implementation, so the drift cannot return.
- **`references/39-intent-routing-llm-primary.md`** — this design log (PR α-3).
- **Conformance probe `92_intent_routing_llm_primary_doc`** — verifies that `vibe.md` reflects the LLM-primary design and points at this design log (PR α-3).

### 4.3 · What did *not* change

- The 642-line `IntentRouter` class — **0 functional changes**. Same scoring formula, same trigger tables, same thresholds, same Clarification fallback, same Vietnamese diacritic handling.
- The 104-line `tests/fixtures/intent_router_golden.jsonl` — same set, same expected intents, same accuracy gate (`set_inclusion_accuracy ≥ 0.75`).
- `cli.py`, `mcp_servers/core.py` — call sites untouched.
- The 14 intent definitions, the 8-verb front door, `_FULL_BUILD_PIPELINE` — all unchanged.

---

## 5 · Decision log

| Decision | Rationale |
|:---------|:----------|
| Don't delete the Python router | Still essential for CLI/CI/MCP/privacy use-cases; deletion would break four call sites and 84 router tests for ~$0 benefit. |
| Don't add LLM calls to the Python router | That would defeat the purpose (determinism, $0 cost, offline) of the fallback path. The LLM is already at the call site for interactive use; layering another LLM call on top is wasteful. |
| Move the LLM-primary instructions into `vibe.md` (not a Python prompt) | Keeps the runtime free of vendor-specific prompt formats. Different host LLMs (Claude / GPT / Codex) read the same markdown spec. |
| Keep the score formula simple (no embedding) | Embeddings would add ~50 MB of model weight + 200 ms classification latency for a marginal accuracy gain that the host LLM already delivers for free in the primary path. |
| Add a contract test for the docstring | The pre-fix docstring drift went undetected for 12 minor versions. A test prevents recurrence. |

---

## 6 · References

- `.claude/commands/vibe.md` — LLM-primary spec (the slash command body).
- `update-package/.claude/commands/vibe.md` — same, shipped to consumers.
- `scripts/vibecodekit/intent_router.py` — Python keyword router (fallback).
- `scripts/vibecodekit/cli.py` — `intent classify` / `intent route` CLI subcommands.
- `scripts/vibecodekit/mcp_servers/core.py` — MCP server that exposes the router.
- `tests/test_intent_router_golden.py` — 104-case golden eval.
- `tests/test_intent_router_docstring_contract.py` — docstring↔impl contract test.
- `tests/fixtures/intent_router_golden.jsonl` — golden fixture corpus.
- `REVIEW-2-issues-2026-05-01.md` — cycle 14 architectural review that triggered this work.
