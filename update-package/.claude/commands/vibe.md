---
description: Single-prompt master router — type free-form prose to dispatch to the right /vibe-* command (LLM-primary, Python fallback)
version: 0.23.0
allowed-tools: [Bash, Read]
---

# /vibe

The friendly entrypoint.  Type a free-form prose request in **Vietnamese
or English** and the host LLM (you) will resolve it to one (or more) of
the 25 flat `/vibe-*` commands.  All flat commands stay 100 %
backward-compatible — power users can keep using them directly.

## Usage

```bash
# Free-form Vietnamese
/vibe làm cho tôi shop online bán cà phê

# Free-form English
/vibe build a landing page for my coffee shop

# Pipeline expansion
/vibe ra mắt sản phẩm landing page mới

# Single-intent
/vibe audit chất lượng code
/vibe deploy lên Vercel production
/vibe fix lỗi npm peer-deps
/vibe tư vấn kiến trúc microservices
```

## How it routes — LLM-primary, Python fallback

This command runs **on the host LLM (you)** — keep that in mind.  You
have full NLP capability, so you classify the prose **directly** rather
than delegating to a brittle keyword matcher.  The Python keyword router
remains as a deterministic **fallback** for cases where you are unsure
or want a stable golden-set check.

### Step 1 — Classify the prose (you, the LLM, do this)

Map the user's prose to one or more of the **14 intents** (canonical
order = pipeline order):

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

**Pipeline expansion** — if the prose describes a holistic build goal
("shop online", "landing page", "ra mắt sản phẩm", "build me an MVP"),
expand to the canonical pipeline:

```
SCAN → VISION → RRI → BUILD → VERIFY
```

### Step 2 — Dispatch in canonical order

Output the slash commands in pipeline order (the table above), one per
line, prefixed with `/vibe-` or `/vibe-rri-*` etc.

### Step 3 — Fallback when unsure

If you cannot confidently classify (the prose is ambiguous, contains
unfamiliar synonyms, or you want a deterministic check before
dispatching), run the Python keyword router as fallback:

```bash
python -m vibecodekit.cli intent route "<original prose>"
```

It returns the slash-command list in JSON form (deterministic, fast,
offline).  You can either accept its output or ask the user a
clarifying question if the router emits a `Clarification`.

### Why LLM-primary?

- **Semantic understanding** — you handle synonyms, context, and
  free-form Vietnamese natively.  The Python router is limited to
  ~140 enumerated trigger phrases.
- **Context-aware** — you remember the recent conversation; the
  Python router is stateless.
- **Multi-language native** — you speak both VN and EN fluently
  without a hand-curated phrase table.
- **No reinvention** — the Python keyword router stays as a fast
  deterministic shortcut for CLI / CI / MCP clients that don't have an
  LLM available.

## Programmatic API (unchanged, for CLI / CI / MCP)

The Python `IntentRouter` class is **back-compat 100 %** for non-LLM
contexts:

```bash
python -m vibecodekit.cli intent classify "làm shop online"
python -m vibecodekit.cli intent route    "deploy to Vercel"
```

```python
from vibecodekit.intent_router import IntentRouter
r = IntentRouter()
match = r.classify("làm cho tôi shop online")
print(r.route(match))   # ['/vibe-scan', '/vibe-vision', '/vibe-rri', '/vibe-scaffold', '/vibe-verify']
print(r.explain(match)) # 'Đã hiểu ý bạn (95% chắc chắn). Sẽ chạy: …'
```

Use this when:
- Running outside an LLM context (CLI scripts, batch jobs, CI).
- Serving an MCP client that does its own dispatch.
- Writing golden tests that need deterministic output.
- Privacy-sensitive contexts where prose must stay local.

## Examples (LLM classification)

| Prose                                       | Routed to                                                          |
|---------------------------------------------|--------------------------------------------------------------------|
| `phân tích nhu cầu`                         | `/vibe-scan`                                                       |
| `xem tầm nhìn`                              | `/vibe-vision`                                                     |
| `audit chất lượng code`                     | `/vibe-verify`                                                     |
| `deploy lên production`                     | `/vibe-ship`                                                       |
| `scaffold landing page`                     | `/vibe-scaffold`                                                   |
| `nâng cấp Next.js 15`                       | `/vibe-task`                                                       |
| `tư vấn kiến trúc`                          | `/vibe-tip`                                                        |
| `update CLAUDE.md`                          | `/vibe-memory`                                                     |
| `chẩn đoán môi trường`                      | `/vibe-doctor`                                                     |
| `xem dashboard`                             | `/vibe-dashboard`                                                  |
| `làm shop online bán cà phê`                | `/vibe-scan` → `/vibe-vision` → `/vibe-rri` → `/vibe-scaffold` → `/vibe-verify` |
| `ra mắt sản phẩm landing page mới`          | `/vibe-scan` → `/vibe-vision` → `/vibe-rri` → `/vibe-scaffold` → `/vibe-verify` |
| `tinh chỉnh và đẩy lên production`          | `/vibe-refine` → `/vibe-ship`                                      |
| `kiểm tra bảo mật và review code`           | `/vibe-scan` → `/vck-review`                                       |
| `doctor selfcheck rồi tinh chỉnh polish nhẹ`| `/vibe-doctor` → `/vibe-refine`                                    |

See `references/39-intent-routing-llm-primary.md` for the full design
and decision log.

## Verb front-door (PR5+, song ngữ)

VN: Ngoài prose tự do, gõ `/vibe <verb>` cho 1 trong **8 verb chuẩn**
    để dispatch trực tiếp tới canonical slash command — ngắn hơn,
    đỡ phải nhớ tên dài.

EN: In addition to free-form prose, type `/vibe <verb>` for one of
    **8 canonical verbs** to dispatch directly to the canonical slash
    command — shorter and easier to remember.

| Verb     | → Canonical command | VN nghĩa                              | EN meaning                      |
|----------|---------------------|---------------------------------------|---------------------------------|
| `scan`   | `/vibe-scan`        | scan repo + docs                      | scout pass over repo + docs     |
| `plan`   | `/vibe-blueprint`   | blueprint architecture + interfaces   | architecture + data + interfaces |
| `build`  | `/vibe-scaffold`    | scaffold project từ preset            | scaffold runnable starter       |
| `review` | `/vck-review`       | adversarial 7-specialist review       | adversarial multi-specialist    |
| `qa`     | `/vck-qa`           | real-browser QA checklist + fix loop  | real-browser QA + fix loop      |
| `ship`   | `/vck-ship`         | test → review → commit → push → PR    | test → review → commit → push → PR |
| `audit`  | `/vibe-audit`       | 91-probe internal self-test           | 91-probe internal regression    |
| `doctor` | `/vibe-doctor`      | kiểm tra overlay cài đúng             | overlay health check            |

```bash
# CLI (in ra slash command đã quote, dễ pipe)
vibe verb scan
vibe verb ship --target vercel --prod
vibe verb               # in song ngữ help, list 8 verb
```

Verb không hợp lệ (vd. `vibe verb bogus`) trả exit code 2 + thông báo
8 verb hợp lệ.  5 command đã `deprecated: true` (PR4: `/vibe-ship`,
`/vibe-rri-t`, `/vibe-rri-ui`, `/vibe-rri-ux`; PR5: `/vck-qa-only`)
**không** nằm trong verb map — front-door luôn route tới canonical
đang sống.

## References

- `ai-rules/vibecodekit/references/00-overview.md`
- `ai-rules/vibecodekit/references/30-vibecode-master.md`
- `ai-rules/vibecodekit/references/39-intent-routing-llm-primary.md` (new — design log)
