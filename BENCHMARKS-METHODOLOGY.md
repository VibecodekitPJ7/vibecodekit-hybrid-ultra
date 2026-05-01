# Benchmarks & Methodology

> **TL;DR:** The "87/87 @ 100 %" number in our docs is a
> **self-conformance regression test**, not an external quality benchmark.
> It proves the runtime has not regressed since the last release — it
> does **not** measure code-generation quality, bug-fix rate, or
> reasoning depth.

---

## 1. What `conformance_audit` actually measures

`conformance_audit` (invoked via `/vibe-audit` or the CLI) runs 87
internal probes (at v0.16.2; count grows with each release) that check
**architectural invariants**:

| Category | Example probes | What it proves |
|---|---|---|
| Module wiring | "Does `intent_router` map all 42 slash commands?" | No dead-code or orphan modules |
| Hook coverage | "Are all 33 lifecycle events in `SUPPORTED_EVENTS`?" | Hook system is complete |
| ACL profiles | "Does `qa` role have `can_mutate=False`?" | Permission model intact |
| Frontmatter integrity | "Does every `/vck-*` command have `inspired-by:`?" | Attribution metadata present |
| Methodology gates | "Does RRI question bank cover 5 personas x 3 modes?" | Methodology coverage |
| Security hardening | "Is Unicode Cf-class normalisation applied?" | Permission bypass classes closed |

Passing 87/87 means: **"the runtime has not regressed against its own
specification."**

## 2. What it does NOT measure

| Dimension | Measured by | Status in VCK-HU |
|---|---|---|
| Code generation quality | HumanEval, MBPP, BigCodeBench | Not yet benchmarked |
| Real-world bug-fix rate | SWE-bench Lite, SWE-bench Verified | Not yet benchmarked |
| Reasoning depth | ARC, GPQA, MATH | Not yet benchmarked |
| Agent autonomy | METR HCAST, AgentBench, WebArena | Not yet benchmarked |
| End-user satisfaction | A/B test, NPS, task-completion rate | Not yet benchmarked |

**Important:** "100 % parity" in our docs refers to parity with the
project's own internal specification ("Giai phau mot Agentic Operating
System"), **not** parity with any external model or tool.

## 3. How to read our quality claims

| Claim in docs | What it actually means |
|---|---|
| "87/87 probes pass" | All internal regression invariants hold |
| "100 % parity" | Runtime matches its own architectural spec |
| "passes conformance audit" | Self-test gate; not an external benchmark |
| "588 pytest cases pass" | Unit + integration tests pass (code correctness) |
| "release-matrix L1+L2+L3 PASS" | Layout validation across 3 deployment modes |

## 4. Intent router accuracy (set-inclusion, N=104)

`tests/test_intent_router_golden.py` chạy `IntentRouter().classify()`
trên dataset có nhãn ở `tests/fixtures/intent_router_golden.jsonl`
(40 EN clear + 44 VI clear + 20 edge / ambiguous, total **104**
entries) và đo:

| Metric | Định nghĩa | Giá trị hiện tại | Gate |
|---|---|---|---|
| `set_inclusion_accuracy` | `mean(_entry_passes(expected, actual))` — `expected ⊆ actual` khi `expected` non-empty; **`actual == ∅`** khi `expected == ∅` (clarification expected) | **98.1 %** (102/104 ở v0.16.2 sau fix clarification-trigger override) | **≥ 75 %** (hard, không hạ ngưỡng nếu tụt) |
| `exact_match_accuracy` | `mean(expected == actual)` — báo cáo only | **88.5 %** (92/104) | ≥ 50 % (cảnh báo super set quá rộng) |
| Per-locale (EN, VI) | set-inclusion riêng từng locale | EN ≥ 75 %, VI ≥ 75 % | đảm bảo không lệch sang một locale |

> **Lịch sử**:
>
> * Baseline trước fix vacuous-pass (Devin Review báo trên PR #28) là
>   98.1 % (102/104).  Bug: 10 entry tag `ambiguous` có
>   `expected_intents = []` luôn vacuously pass
>   `expected.issubset(actual)` (empty set là subset của mọi set) →
>   router có thể trả intent thay vì Clarification mà vẫn pass.  Sau
>   fix #29, 1 entry mới hiện hình thành miss
>   (`"không biết làm sao luôn á"` → router trả `{BUILD}` chỉ vì
>   `"làm"` nằm trong BUILD trigger list) → 97.1 % (101/104).
> * Sau follow-up clarification-trigger override (PR sau #31): thêm
>   `_CLARIFICATION_TRIGGERS` (VN: `"không biết"`, `"luôn á"`, `"làm
>   sao"`, `"bí quá"`, ...; EN: `"i'm stuck"`, `"no idea"`, `"not
>   sure how"`, ...).  Khi prose match clarification trigger và không
>   có intent đạt `high_conf`, router trả `Clarification` thay vì
>   low-conf guess.  Accuracy quay lại **98.1 %** (102/104) với
>   semantic đúng (entry "không biết làm sao luôn á" pass đúng nhờ
>   route Clarification, không phải vacuous-pass).

Không phải benchmark code-quality (như HumanEval) — đây thuần là
classification accuracy của bộ phân loại keyword + multi-tier weighted
scoring.  Mục đích: đảm bảo prose tiếng Việt + tiếng Anh + slash
typing đều land đúng `/vibe-*` / `/vck-*` slash command.

Cách rerun:

```bash
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" \
  PYTHONPATH=./scripts python3 -m pytest \
    tests/test_intent_router_golden.py -v
```

Threshold `0.75` được hard-code trong test.  **KHÔNG hạ ngưỡng** nếu
baseline tụt xuống dưới — sửa router (mở rộng `TIER_1` triggers, điều
chỉnh weight) hoặc cập nhật JSONL kèm methodology note ở đây.

### 4.1 Intent router release matrix dump (PR4)

Mỗi minor / patch release commit kèm 1 file
`benchmarks/intent_router_<VERSION>.json` chứa confusion matrix
deterministic (per-intent tp/fp/fn/tn + per-locale accuracy + miss-pair
clusters).  File này là **release artefact** — diff giữa version cho
biết router cải thiện / regress ở chỗ nào, không cần rerun benchmark.

Schema chi tiết + cách interpret xem `benchmarks/README.md`.

Regenerate sau khi bump VERSION:

```bash
PYTHONPATH=./scripts python3 tools/dump_intent_confusion.py
# → ghi benchmarks/intent_router_<VERSION>.json
```

Test `tests/test_benchmarks_intent_dump.py` ép buộc:

- File `benchmarks/intent_router_<current-VERSION>.json` tồn tại.
- Schema hợp lệ (đủ key bắt buộc, kiểu dữ liệu đúng).
- `set_inclusion_accuracy` ≥ 0.75 (cùng gate golden eval).

## 4b. Observability (PR2 — structured logging)

VibecodeKit xuất structured log cho mọi event security-critical — decision
của ``permission_engine``, scrub của ``hook_interceptor``, tool-call cycle
của ``tool_executor``, denial append của ``denial_store``.  Log được emit
qua helper ``scripts/vibecodekit/_logging.py`` (stdlib-only, không thêm
dependency) và ghi ra ``stderr`` (``stdout`` vẫn là contract của CLI
``print()``).

Env switches:

| Env | Default | Ý nghĩa |
|---|---|---|
| ``VIBECODE_LOG_LEVEL`` | ``INFO`` | ``DEBUG`` / ``INFO`` / ``WARNING`` / ``ERROR`` / ``CRITICAL``; invalid → ``INFO``. |
| ``VIBECODE_LOG_JSON`` | unset | ``=1`` xuất JSON 1-line cho mỗi record (tiện ``jq`` / ELK / Loki pipeline). |

Ví dụ pipe log sang ``jq``:

```bash
VIBECODE_LOG_LEVEL=DEBUG VIBECODE_LOG_JSON=1 \
  PYTHONPATH=./scripts python3 -m vibecodekit.cli demo 2>&1 1>/dev/null \
  | jq 'select(.name == "vibecodekit.permission_engine")'
```

Invariants:

- ``logger.propagate = False`` cho mỗi logger tạo qua helper — tránh bão
  log khi downstream cài root handler (Sentry, DataDog, syslog).
- ``print()`` trong CLI entrypoint (``cli.py``, ``demo.py``, và ``_main``
  của module ``permission_engine`` / ``tool_executor`` / …) **không** bị
  đổi — chúng là contract stdout của ``python -m vibecodekit.<mod>``.
- JSON formatter thuần ``json.dumps`` stdlib — **không** import
  ``structlog`` / ``python-json-logger`` (giữ DNA Python-pure).

Event catalog (stable names, mở rộng theo release):

| Logger | Event | Level | Khi xảy ra |
|---|---|---|---|
| ``vibecodekit.permission_engine`` | ``permission_decision`` | INFO/WARNING | Mỗi deny / denial-fatigue ask / bypass-unsafe override. |
| ``vibecodekit.denial_store`` | ``denial_recorded`` | DEBUG | Mỗi lần append denial vào store (JSONL + fcntl lock). |
| ``vibecodekit.hook_interceptor`` | ``hook_env_scrubbed`` | INFO | Khi env subprocess bị scrub secret. |
| ``vibecodekit.tool_executor`` | ``tool_plan_start`` / ``tool_plan_end`` | INFO | Entry / exit của ``execute_blocks``. |

---

## 4c. Permission engine coverage (PR4 — strict deny + safe exceptions)

v0.16.2 + PR4 mở rộng Layer 4 của permission engine thành 3 tầng:

* **Layer 4b — Strict deny (9 pattern, port từ gstack).** Mỗi pattern có
  ``rule_id`` ổn định (``R-*``) + ``severity=high``.  Catalog đầy đủ
  trong ``SECURITY.md`` §"Strict-deny catalog".
* **Layer 4c — Safe-exception list cho ``rm -rf``.** 13 build artifact
  (``node_modules``, ``dist``, ``__pycache__``, …) → ``decision != "deny"``
  khi command là ``rm -rf <safe_target>...``.  Chặn mọi dạng có shell
  metachar (``$(`` / ``` ` ``` / ``;`` / ``&`` / ``|`` / ``<`` / ``>``)
  → giảm nuisance "ask" khi clean workspace, không mở bypass channel.
* **Layer 4 (existing) — Dangerous patterns.** Fallback cho các dạng
  blocked không khớp Layer 4b.  Audit log dùng
  ``R-DANGEROUS-PATTERN-FALLBACK`` + ``severity=medium``.

### Audit log (``~/.vibecode/security/attempts.jsonl``)

* JSONL, 1 entry/quyết định deny, ghi qua ``_platform_lock`` (fcntl +
  msvcrt fallback).
* Format: ``{ts, decision, rule_id, cmd_hash, mode, severity}`` — chỉ
  ``sha256:<32-char-prefix>`` của command, không plaintext.
* Rate cap 60/60s sliding window.  Overflow → ``dropped_count`` trong
  sidecar ``attempts.meta.json`` (rotate hourly qua ``hour_key``).
* Override path: env ``VIBECODE_AUDIT_LOG_DIR`` (test isolation) +
  fallback ``tempfile.gettempdir()`` khi ``$HOME`` không writable.

### Test coverage

``tests/test_permission_engine_strict_deny.py`` (25 test):

* 11 parametrized strict-deny probe → decision=deny + rule_id expected.
* 6 safe-exception probe → không deny.
* Counter-probe: ``rm -rf /etc`` vẫn deny, ``rm -rf $(whoami)`` vẫn deny,
  ``chmod 755 ./script.sh`` không deny.
* Audit log smoke: ghi đủ 6 field; plaintext secret KHÔNG leak ra file.
* Rate cap: 70 deny trong 1 window → ≤60 entry, ``dropped_count > 0``.
* ``cmd_hash`` stability + fallback tempdir.

---

## 4.5. Coverage gate (cycle 6 PR3 → cycle 12 PR3)

Per-module coverage floors (`pyproject.toml` `[tool.coverage]`):

| Module                                 | Phase 1 (cycle 6) | Phase 2a (cycle 7) | Phase 2b (cycle 8) | Phase 3 (cycle 9) | Phase 4 (cycle 10) | Phase 5 (cycle 11) | Phase 6 (cycle 12) |
|----------------------------------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `scripts/vibecodekit/tool_executor.py` | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) |
| `scripts/vibecodekit/team_mode.py`     |  41% | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) | **≥ 80%** (98%) |
| `scripts/vibecodekit/vn_faker.py`      |   0% | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) |
| `scripts/vibecodekit/vn_error_translator.py` | 0% | **≥ 80%** (100%) | **≥ 80%** (100%, +3 test) | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) | **≥ 80%** (100%) |
| `scripts/vibecodekit/memory_writeback.py` | 0% | 0% | 0% | **100%** (+40 test) | **100%** | **100%** | **100%** |
| `scripts/vibecodekit/manifest_llm.py`  |   0% | 0% | 0% | **100%** (+12 test) | **100%** | **100%** | **100%** |
| `scripts/vibecodekit/auto_writeback.py` | 0% | 0% | 0% | **100%** (+20 test) | **100%** | **100%** | **100%** |
| `scripts/vibecodekit/hook_interceptor.py` | 33% | 33% | 33% | 33% | **98%** (+31 test) | **98%** | **98%** |
| `scripts/vibecodekit/auto_commit_hook.py` | 40% | 40% | 40% | 40% | **99%** (+37 test) | **99%** | **99%** |
| `scripts/vibecodekit/browser/manager.py` |   0% | 0% | 0% | 0% | **100%** (+48 test) | **100%** | **100%** |
| `scripts/vibecodekit/mcp_client.py`    | 62% | 62% | 62% | 62% | 62% | **90%** (+45 test) | **90%** |
| `scripts/vibecodekit/browser/cli_adapter.py` | 33% | 33% | 33% | 33% | 33% | **99%** (+28 test) | **99%** |
| `scripts/vibecodekit/approval_contract.py` | 66% | 66% | 66% | 66% | 66% | **100%** (+24 test) | **100%** |
| `scripts/vibecodekit/memory_retriever.py` | 33% | 33% | 33% | 33% | 33% | **98%** (+9 test) | **98%** |
| `scripts/vibecodekit/recovery_engine.py` | 58% | 58% | 58% | 58% | 58% | **98%** (+7 test) | **98%** |
| `scripts/vibecodekit/dashboard.py`     |  50% | 50% | 50% | 50% | 50% | **95%** (+7 test) | **95%** |
| `scripts/vibecodekit/mcp_servers/selfcheck.py` | 23% | 23% | 23% | 23% | 23% | **95%** (+13 test) | **95%** |
| `scripts/vibecodekit/doctor.py`        |  68% | 68% | 68% | 68% | 68% | **94%** (+8 test) | **94%** |
| `scripts/vibecodekit/task_runtime.py`  | 76% | 76% | 76% | 76% | 76% | 76% | **97%** (+47 test) |
| `scripts/vibecodekit/module_workflow.py` | 67% | 67% | 67% | 67% | 67% | 67% | **99%** (+41 test) |
| `scripts/vibecodekit/mcp_servers/core.py` | 55% | 55% | 55% | 55% | 55% | 55% | **97%** (+15 test) |
| `scripts/vibecodekit/eval_select.py`   | 74% | 74% | 74% | 74% | 74% | 74% | **100%** (+13 test) |
| `scripts/vibecodekit/skill_discovery.py` | 71% | 71% | 71% | 71% | 71% | 71% | **98%** (+10 test) |
| `scripts/vibecodekit/event_bus.py`     | 73% | 73% | 73% | 73% | 73% | 73% | **100%** (+5 test) |
| `scripts/vibecodekit/install_manifest.py` | 74% | 74% | 74% | 74% | 74% | 74% | **99%** (+3 test) |
| `scripts/vibecodekit/compaction.py`    | 82% | 82% | 82% | 82% | 82% | 82% | **100%** (+6 test) |
| `scripts/vibecodekit/denial_store.py`  | 84% | 84% | 84% | 84% | 84% | 84% | **99%** (+5 test) |
| `scripts/vibecodekit/learnings.py`     | 83% | 83% | 83% | 83% | 83% | 83% | **97%** (+4 test) |
| `scripts/vibecodekit/intent_router.py` | 86% | 86% | 86% | 86% | 86% | 86% | **98%** (+4 test) |
| `scripts/vibecodekit/browser/state.py` | 87% | 87% | 87% | 87% | 87% | 87% | **97%** (+11 test) |
| `scripts/vibecodekit/cost_ledger.py`   | 89% | 89% | 89% | 89% | 89% | 89% | **100%** (+4 test) |
| **TOTAL** (global gate)                | ≥ 60% (61%) | ≥ 70% (72%) | **≥ 72%** (72%) | **≥ 76%** (76%) | **≥ 80%** (80%) | **≥ 85%** (85%) | **≥ 90%** (90%) |

`omit` rationale (cycle 7 PR2):

* `cli.py` — user-facing stdout entry point (96 prints intentional, đã
  carve-out cycle 6 PR4).  Phase 3 sẽ test qua subprocess.
* `deploy_orchestrator.py` — heavy subprocess + git mock; phù hợp PR
  riêng cycle 8.

Phase 2b (cycle 8 PR2) — vn_error_translator polish:

* 3 test bổ sung trong `tests/test_vn_error_translator.py`:
  - **Graceful degrade** khi `_yaml is None` (monkeypatch sys.modules).
  - **Multi-YAML ranking** — 2 file cùng pattern, confidence cao đứng
    đầu.
  - **Multi-line traceback chain** — root-cause ranked correctly.
* Module đã đạt 100% từ cycle 7 với PyYAML installed; 3 test mới mở
  rộng *behavior coverage* (xác nhận degrade path, ranking semantics).
* Global TOTAL floor 70 → 72 để khoá achievement actual sau cycle 7
  (KHÔNG dám raise lên 75 trong PR2 vì TOTAL hiện tại 72% — đẩy lên
  75% cần mở scope sang `memory_writeback.py` 0% / `manifest_llm.py` 0%
  / `auto_writeback.py` 0%, phù hợp Phase 3).

Phase 3 (cycle 9 PR1 + PR2 + PR3) — module 0% phủ kín:

* **PR1**: `tests/test_memory_writeback.py` (+40 test) phủ
  `memory_writeback.py` (229 stmt, 0% → **100%**).  5 section detector
  + 4 method `MemoryWriteback` (init/update/check/nest, dry-run, drift,
  path-traversal guard) + helpers + 2 dataclass shape.
* **PR2**: `tests/test_manifest_llm_and_auto_writeback.py` (+32 test)
  phủ `manifest_llm.py` (67 stmt) + `auto_writeback.py` (66 stmt) → cả
  hai đều **100%**.  Frontmatter parser 5 nhánh, build_manifest 4 case,
  RefreshDecision dataclass + try_refresh 7 nhánh (gồm exception swallow
  primary + secondary state-write failure).
* **PR3**: bump `fail_under` 72 → **76** (lock actual TOTAL
  achievement +4pp).  Mục tiêu spec ban đầu Phase 3 = 80% defer Phase 4
  vì sau khi cover 3 module 0% chỉ +4pp (72→76), KHÔNG đủ chạm 80%.
  Còn ~277 stmt gap chủ yếu ở `browser/manager.py` (178 stmt 0%),
  `mcp_client.py` (124 miss), `hook_interceptor.py` (62 miss),
  `auto_commit_hook.py` (59 miss).

Phase 4 (cycle 10 PR1 + PR2 + PR3) — hoàn tất spec target 80%:

* **PR1**: `tests/test_hook_interceptor_and_auto_commit.py` (+68 test)
  phủ `hook_interceptor.py` (93 stmt, 33% → **98%**, +65pp) +
  `auto_commit_hook.py` (98 stmt, 40% → **99%**, +59pp).  Test cover:
  `_filter_env` (drop secret-like env keys), `_scrub_str` /
  `_scrub_payload` recursive (AWS/sk-/ghp_/Bearer/private-key + bypass
  `VIBECODE_HOOK_ALLOW_SECRETS=1`), `run_hooks` 7 nhánh (chmod
  fallback, JSON decision parse, TimeoutExpired → 124, command env),
  `is_blocked` 5 case; `is_sensitive` 21 parametrize, `Sensitive
  FileGuard.check` 6 case (path + 3 token type + private key block),
  `AutoCommitHook.decide` 7 case (opt-out / not-git / nothing /
  sensitive / debounced / malformed stamp / ready), `commit` 3 case
  (refusal / success bumps stamp / git failure no-stamp).  TOTAL 76 → 78.
* **PR2**: `tests/test_browser_manager.py` (+48 test) phủ
  `browser/manager.py` (178 stmt, 0% → **100%**).  Stub
  `playwright.sync_api` vào `sys.modules` *trước* khi import (idempotent
  với real playwright).  Mock minimal protocol surface
  (`_FakePage`/`_FakeContext`/`_FakeBrowser`/`_FakeChromium`/
  `_FakePlaywright`).  `BrowserManager.start` (idempotent + headless),
  `stop` (close all + clear), `_open_tab` raises khi browser=None,
  `run_read_verb` 10 verb, `run_write_verb` 10 verb, `get_manager`
  singleton lifecycle.  TOTAL 78 → 80.
* **PR3**: bump `fail_under` 76 → **80** — Phase 4 spec target
  HIT.  Lock toan bộ +4pp từ 2 PR đầu.

Phase 5 (cycle 11 PR1 + PR2 + PR3) — đẩy TOTAL từ 80 → 85 lock spec:

* **PR1**: `tests/test_mcp_client_and_cli_adapter.py` (+73 test) phủ
  `mcp_client.py` (330 stmt, 62% → **90%**, +28pp) +
  `browser/cli_adapter.py` (94 stmt, 33% → **99%**, +66pp).  Test
  cover: manifest helpers (`load_manifest` / `save_manifest` /
  `register_server` / `disable_server`), 3 transport (`_call_inproc`
  5 case / `_call_stdio_oneshot` 7 case / `_call_stdio_handshake`
  + dispatcher 5 case), `_resolve` / `list_tools` / `call_tool`
  (timeout clamp + invalid fallback + inproc dispatch); `StdioSession`
  12 case (open idempotent / send-recv request / log-noise skip /
  timeout / server exit / send-after-close / BrokenPipe / initialize
  success+error / list_tools success+error / call_tool / public
  request+notify / context manager / stderr_tail).  `DaemonClient` 12
  case (DaemonNotRunning state missing/dead PID / state alive /
  `is_daemon_alive` / health+command+shutdown HTTP roundtrip /
  shutdown URL fallback / `_send` URLError + empty body + invalid
  JSON), `main` CLI 7 case.  Strategy mới: real `os.pipe()` fd cho
  selectors register (BytesIO fake bị EPERM trong CI sandbox);
  monkeypatch `DefaultSelector.select` luôn return synthetic ready
  event; monkeypatch `urllib.request.urlopen` qua `_FakeUrlopen`
  context manager — không bind real socket.  TOTAL 80 → 82.
* **PR2**: `tests/test_phase5_module_polish.py` (+68 test) phủ 6 module
  gap nhỏ/vừa.  `approval_contract.py` (123 stmt, 66% → **100%**, +34pp,
  24 test cover full lifecycle: `_validate_appr_id` reject path
  traversal / `create` unknown kind+risk / default+custom options /
  `list_pending` filter resolved + skip malformed / `get` invalid id
  + missing + merges response + skip malformed response / `respond`
  invalid id + unknown id + invalid choice / `wait` timeout auto-deny +
  malformed retry + deadline_exceeded / `clear_resolved`).
  `memory_retriever.py` (54 stmt, 33% → **98%**, +65pp, 9 test cover:
  diacritic strip Tiếng Việt, NFC casefold, header split, OSError
  swallow, retrieve rank by overlap + zero overlap + limit).
  `recovery_engine.py` (45 stmt, 58% → **98%**, +40pp, 7 test cover
  permission_denied jump / context_overflow + prompt_too_large jump /
  full ladder walk LEVELS / terminal_error after exhausted / reset /
  to_dict / `_main` CLI smoke).  `dashboard.py` (66 stmt, 50% →
  **95%**, +45pp, 7 test cover summarise empty + with-events +
  malformed-jsonl / `denials.json` read + corrupted / `_main` smoke +
  `--json` mode).  `mcp_servers/selfcheck.py` (66 stmt, 23% → **95%**,
  +72pp, 13 test cover ping/echo/now / `_handle` initialize +
  initialized notification + tools.list + tools.call ok+unknown+bad-
  args+runtime-error / shutdown / unknown method / unknown notification
  silent / `_main` loop với parse-error envelope rid=None).
  `doctor.py` (62 stmt, 68% → **94%**, +26pp, 8 test cover empty dir /
  installed-only fail / skill_repo layout / advisory present in root /
  runtime placeholder warns / runtime assets missing warns / `_main`
  smoke + installed-only nonzero exit).  TOTAL 82 → **85**.
* **PR3** (cycle 11): bump `fail_under` 80 → **85** — Phase 5 spec
  target HIT.  Lock toàn bộ +5pp từ 2 PR đầu.  Lần đầu kể từ Phase 1
  floor match đúng spec target — KHÔNG còn pragmatic gap.

Phase 6 (cycle 12 PR1 + PR2 + PR3) — đẩy TOTAL từ 85 → 90 lock spec:

* **PR1**: `tests/test_phase6_task_runtime_module_workflow.py`
  (+88 test) phủ 2 module core-runtime lớn.  `task_runtime.py`
  (468 stmt, 76% → **97%**, +21pp, 47 test cover: `_is_valid_task_id`
  valid/invalid regex · `create_task` unknown-kind · `_read_index`
  missing+malformed · `list_tasks` filter+sort · `get_task` invalid
  · `read_task_output` invalid/unknown/missing/window/unicode ·
  `start_local_bash` success/fail/timeout/kill · `kill_task`
  invalid/unknown/terminal/no-pid · `drain_notifications`
  invalid/atomic/malformed/no-file · `check_stalls`
  producing/quiet/prompt/missing · `start_local_workflow`
  bash/sleep/write/unknown/path-escape/exception/failure +on_error
  continue · `start_monitor_mcp` success+failure · `start_dream`
  consolidation · `wait_for` terminal/timeout/unknown).
  `module_workflow.py` (239 stmt, 67% → **99%**, +32pp, 41 test cover
  Pattern F workflow 11 detector + probe 3 case + reuse_inventory
  ordering + module_plan 5 routing branch với error + _slug + main CLI
  probe/plan subcommand).  TOTAL 85 → 87.
* **PR2**: `tests/test_phase6_small_modules_polish.py` (+85 test) phủ
  10 module medium-small (xem CHANGELOG v0.21.0 chi tiết từng module).
  Đặc biệt: `mcp_servers/core.py` (111 stmt, 55% → **97%**, +42pp) qua
  15 test cover MCP stdio JSON-RPC 2.0 protocol dispatch; `eval_select`
  / `event_bus` / `compaction` / `cost_ledger` đều 100%; `denial_store`
  / `install_manifest` 99%; `learnings` / `intent_router` /
  `skill_discovery` / `browser/state` 97-98%.  `conformance_audit.py`
  (1214 stmt, 82% → **83%**, +1pp) qua 4 test cover `_main` human+JSON+
  failing-threshold + exception branch inside `audit()` loop
  (monkeypatch forced-fail probe).  TOTAL 87 → **90**.
* **PR3** (this): bump `fail_under` 85 → **90** — Phase 6 spec target
  HIT.  Lock toàn bộ +5pp từ 2 PR đầu.  Lần thứ hai liên tiếp kể từ
  Phase 5 floor match đúng spec target — KHÔNG pragmatic gap.

Rationale: `tool_executor.py` là hot-path subprocess execute — module
nguy hiểm nhất, đáng có coverage cao nhất.  Phase 2a (cycle 7) phủ thêm
3 module Vietnamese-locale (faker / error translator) + team
coordination layer.  Phase 2b (cycle 8) chỉ polish vn_error_translator
+ lock floor.  Phase 3 (cycle 9) phủ kín 3 module 0% còn lại
(`memory_writeback` / `manifest_llm` / `auto_writeback`) bằng 72 test
mới — đạt 100% mỗi nhưng global TOTAL chỉ +4pp do scale module nhỏ vs
gap còn lại lớn.  Phase 4 (cycle 10) hoàn tất spec target 80% qua
mở scope `browser/manager.py` (178 stmt 0% → 100%) +
`hook_interceptor.py` (33% → 98%) + `auto_commit_hook.py` (40% →
99%).  Tổng 116 test mới qua 3 PR.  Phase 5 (cycle 11) đẩy spec target
85% qua mở scope `mcp_client.py` (62% → 90%) + `browser/cli_adapter.py`
(33% → 99%) + `approval_contract.py` (66% → 100%) + 5 module polish
(`memory_retriever` / `recovery_engine` / `dashboard` / `selfcheck` /
`doctor`).  Tổng 141 test mới qua 2 PR + 1 release PR.  Phase 6
(cycle 12) hoàn tất spec target 90% qua `task_runtime.py` (76 → 97)
+ `module_workflow.py` (67 → 99) + 10 module medium-small (55-89%
→ 97-100%).  Tổng 173 test mới qua 2 PR + 1 release PR.  Phase 7
(cycle 13) là **documentation expansion** thuần — KHÔNG đổi runtime,
KHÔNG đổi `fail_under` (giữ 90).  PR1 thêm pre-baked case study
`references/examples/01-otb-budget-module/` (11 file, OTB Budget cho
Vietnamese retail finance), PR2 thêm `references/anti-patterns-gallery.md`
(12 AP-XX với BAD/GOOD viz + Fix recipe + Detector), PR3 thêm
`references/37-color-psychology.md` (7 industry palette + WCAG + VN
cultural) + `references/38-font-pairing.md` (5 use-case stack + VN
subset support).  Conformance probe count 87 → **91**, tests 1615 →
**1695** (+80 từ 4 test file mới), public API surface 100 % stable.
Phase 8 (future cycle 14+) sẽ polish `conformance_audit.py` 83% →
≥95% (còn 203 miss lớn nhất, 91 probe function với exception-path
coverage thiếu) + đưa `cli.py` / `deploy_orchestrator.py` trở lại
scope qua subprocess test — mục tiêu global TOTAL ≥ 93%.  Mypy
strict expand từ 9/44 module → 25+/44.  Optional RBAC multi-tenant
nếu user demand.

CI gate (xem `.github/workflows/ci.yml` step "pytest with coverage"):

```bash
python -m coverage run --source=scripts/vibecodekit -m pytest tests -q
python -m coverage report
python -m coverage report --include='scripts/vibecodekit/tool_executor.py' \
    --fail-under=80
python -m coverage xml -o coverage.xml
```

Coverage XML upload qua `actions/upload-artifact@v4` cho per-PR view.

---

## 5. Roadmap for external benchmarks (Phase 2)

We plan to add external benchmark runs to provide ground-truth quality
numbers.  Candidates (in order of implementation priority):

1. **HumanEval** (164 tasks) — classic function-completion benchmark.
   Low cost (~$5/run), fast (~10 min), well-understood baseline.
2. **MBPP** (974 tasks) — broader function-level benchmark.
3. **SWE-bench Lite** (300 tasks) — real-world bug fixes on real repos.
   Industry-standard for agent evaluation.
4. **BigCodeBench** (1140 tasks) — harder function-level tasks.

Results will be tracked in `benchmarks/` with timestamp + git SHA,
run nightly on `main`, and referenced from this document.

---

## 6. Contributing benchmark results

If you run VCK-HU against any external benchmark, we welcome PRs adding
results to `benchmarks/<benchmark-name>/results.json`.  Include:

- Git SHA of the VCK-HU version tested
- Benchmark version / split used
- Raw pass rate and any relevant metrics
- Hardware / model backend used
- Cost per run

See `CONTRIBUTING.md` for general PR guidelines.
