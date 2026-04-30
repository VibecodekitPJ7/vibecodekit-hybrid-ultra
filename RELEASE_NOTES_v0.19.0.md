# VibecodeKit Hybrid Ultra v0.19.0 — Coverage Phase 4 release (spec target HIT)

**Release date**: 2026-04-30
**Type**: Coverage milestone (minor bump, semver `0.18.0 → 0.19.0`)
**Backward compat**: 100% — zero breaking changes runtime, **chỉ thêm
test code + bump floor + cập nhật docs**.

## Highlights

### Coverage Phase 4 — spec target 80% HIT

| Module | Stmt | Cycle 9 | Cycle 10 | Δ pp | Test added |
|--------|-----:|--------:|--------:|-----:|-----------:|
| `hook_interceptor.py`   |  93 |  33% |  **98%** | **+65** | +31 (PR1) |
| `auto_commit_hook.py`   |  98 |  40% |  **99%** | **+59** | +37 (PR1) |
| `browser/manager.py`    | 178 |   0% | **100%** | **+100** | +48 (PR2) |
| **Total**               | **369** | mixed | **≥ 98%** | — | **+116** |

Global TOTAL coverage: 76% → **80%** (+4pp).  Floor `fail_under`
76 → **80** — Phase 4 spec target lock.  Test count: 1194 → **1310**
(+116 test, all passing, 0 skipped).

### Phase 4 scope coverage

- **`hook_interceptor.py`** (Claude-level hook runner under `.claw/hooks/`):
  - `_filter_env` (drop secret-like env keys: `*_TOKEN`, `*_KEY`,
    `*_PASSWORD`, `*_SECRET`, `OPENAI_*`, `ANTHROPIC_*` + bypass via
    `VIBECODE_HOOK_ALLOW_SECRETS=1`).
  - `_scrub_str` 4 token kind: AWS access key (`AKIA…`), OpenAI
    secret (`sk-…`), GitHub PAT (`ghp_…`), Authorization Bearer prefix.
  - `_scrub_payload` recursive nested dict/list/str + non-string scalar
    passthrough + bypass.
  - `_hook_cmd` (`.py` → `python3 path` / `.sh` → `bash path`).
  - `run_hooks` 7 nhánh: no `.claw/hooks/` dir / event dir missing /
    chmod implicit fallback / JSON decision parse / non-JSON stdout /
    malformed JSON `{` start / non-zero rc / `TimeoutExpired` → 124 /
    expose `$VIBECODE_HOOK_COMMAND` to hook script.
  - `is_blocked` 5 case (empty / deny / non-zero rc / allow override
    / zero rc no decision).
- **`auto_commit_hook.py`** (auto-checkpoint hook để khôi phục công
  việc khi crash):
  - `is_sensitive` 21 parametrize (13 sensitive: `.env*`, `*.pem`,
    `*.key`, `*credentials*`, `*token*` + 8 whitelist: `.env.example`,
    `package.json`, `README.md`, …).
  - `SensitiveFileGuard.check` 6 case: sensitive path / token-in-content
    `AKIA…` / safe path / safe content / OpenAI `sk-…` / RSA private
    key block (`-----BEGIN … PRIVATE KEY-----`).
  - `_opt_out` 3 case (env / lockfile / clear).
  - `_is_git_repo` / `_git_status_files` 5 case (real git init / non-
    repo / `FileNotFoundError` / 2 dirty / clean tree).
  - `AutoCommitHook.decide` 7 case (opt-out / not-git / nothing /
    sensitive blocked / debounced / malformed stamp fallback / ready).
  - `AutoCommitHook.commit` 3 case (refusal propagate / success bumps
    stamp + git log shows `[vibecode-auto] checkpoint test` / git
    failure no-stamp).
- **`browser/manager.py`** (Playwright-based real-browser QA runtime):
  - **Stub strategy**: inject `playwright.sync_api` vào `sys.modules`
    *trước* khi import manager (idempotent — nếu real playwright đã
    cài thì giữ nguyên).  Mock minimal protocol surface qua
    `_FakePage` / `_FakeContext` / `_FakeBrowser` / `_FakeChromium` /
    `_FakePlaywright` / `_FakeSyncPlaywrightHandle` — đủ để chạy logic
    100% mà không cần Chromium binary trong CI.
  - `BrowserManager.start` (idempotent + headless flag), `stop` (close
    contexts/browser/playwright + clear tabs + safe khi chưa start),
    `_open_tab` raises `RuntimeError` khi browser=None, `_tab` default
    + auto-create.
  - `run_read_verb` 10 verb: text / html / links / forms / aria
    (real tree + None fallback `{}`) / console / network / snapshot /
    tabs / status / unknown `ValueError` + tab extra switches active.
  - `run_write_verb` 10 verb: goto (default + explicit `wait_until` +
    assert URL non-empty), click (selector vs target fallback), fill,
    select, scroll (default `(0, 600)` vs explicit), wait_for,
    screenshot (default `Path.cwd()/vck-screenshot.png` vs explicit +
    `full_page=False`), set_cookie, new_tab (explicit name vs target
    fallback vs auto `tab-N`), close_tab (existing vs missing no-raise),
    unknown `ValueError`.
  - `get_manager` / `stop_manager` singleton lifecycle + `run_*_verb`
    module facades.

### Floor decision (PR3 lock 76 → 80 — Phase 4 spec target HIT)

Cycle 9 PR3 lock pragmatic 76 (defer Phase 3 spec 80% sang Phase 4 vì
3 module 0% không đủ +pp).  Cycle 10 PR1 + PR2 phủ thêm 369 stmt mới
qua 116 test → TOTAL +4pp đúng đủ chạm spec target 80%.

PR3 cycle 10 (this) bump `fail_under` 76 → **80** — *spec-target lock*,
KHÔNG còn pragmatic.  Đây là lần đầu tiên global coverage gate đạt
80% kể từ cycle 6 PR3 đặt floor 60% Phase 1.

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.19.0
# hoặc reproducible:
uv sync --frozen
```

KHÔNG có migration script bắt buộc.  KHÔNG có deprecation mới — cập
nhật v0.17.0 deprecation `permission_engine.decide()` vẫn áp dụng
(removal target v1.0.0).

## Deprecations

(Carry-over từ v0.17.0, không thêm mới.)

- `permission_engine.decide()` dict-return shape vẫn emit
  `DeprecationWarning`. Dùng `decide_typed()` cho `PermissionDecision`
  dataclass. **Removal target: v1.0.0.**

## Known limitations

- RBAC multi-tenant không được hỗ trợ; single-agent permission model.
- Global coverage TOTAL 80% floor (Phase 5 target: 85%, cần mở scope
  `mcp_client.py` 62% + `browser/cli_adapter.py` 33% + đưa `cli.py` /
  `deploy_orchestrator.py` trở lại scope qua subprocess test).
- mypy strict 9/44 module (chưa expand cycle 10 — defer cycle 11+).
- `browser/manager.py` test dùng stub `playwright.sync_api` cho CI
  thuần stdlib (không cài `[browser]` extras); real Playwright event
  callbacks (`_on_console`, `_on_request`, `_on_response`) excluded
  qua `# pragma: no cover` vì stubs không emit events.

## Verify

```bash
git clone https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra
git checkout v0.19.0

VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q
# → 1310+ passed.

PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
# → 87/87 met=True.

rm -f .coverage && VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m coverage run --source=scripts/vibecodekit -m pytest tests -q
python3 -m coverage report --skip-empty --fail-under=80
# → TOTAL ≥ 80%, exit 0.

PYTHONPATH=./scripts python3 -m mypy --strict \
  scripts/vibecodekit/permission_engine.py \
  scripts/vibecodekit/scaffold_engine.py \
  scripts/vibecodekit/verb_router.py \
  scripts/vibecodekit/denial_store.py \
  scripts/vibecodekit/_audit_log.py \
  scripts/vibecodekit/tool_executor.py \
  scripts/vibecodekit/team_mode.py \
  scripts/vibecodekit/task_runtime.py \
  scripts/vibecodekit/subagent_runtime.py
# → Success: no issues found in 9 source files.
```

## Tier readiness

Không thay đổi từ v0.18.0 (thuần coverage milestone, không thay đổi
runtime/API):

- **Solo dev**: A+ (CLI demo 1.3s, faker/translator out-of-box).
- **Small team**: A+ (permission strict-deny + audit log + team_mode
  CLI + auto-commit checkpoint hook 99% covered).
- **Enterprise**: A (SECURITY.md + SBOM + 3-layer security CI [pip-
  audit + actionlint + CodeQL] + mypy strict 9/44 + coverage TOTAL
  80% spec target HIT; RBAC multi-tenant pending v0.20.0+).

## Tag instruction (manual — Devin không có perms)

```bash
git checkout main && git pull origin main
git tag v0.19.0 && git push origin v0.19.0
```

## Next (v0.19.1 / v0.20.0 roadmap)

- Phase 5 coverage: global TOTAL ≥ 85% qua mở scope `mcp_client.py`
  + `browser/cli_adapter.py` + đưa `cli.py` / `deploy_orchestrator.py`
  trở lại scope.
- Mypy strict expand 9/44 → 20+/44 module.
- Optional RBAC multi-tenant nếu user demand.
- CodeQL custom queries cho VibecodeKit-specific vuln pattern.
