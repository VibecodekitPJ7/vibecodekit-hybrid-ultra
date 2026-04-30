# VibecodeKit Hybrid Ultra v0.18.0 — Coverage Phase 3 release

**Release date**: 2026-04-30
**Type**: Coverage milestone (minor bump, semver `0.17.0 → 0.18.0`)
**Backward compat**: 100% — zero breaking changes runtime, **chỉ thêm
test code + bump floor + cập nhật docs**.

## Highlights

### Coverage Phase 3 — 3 module 0% phủ kín

| Module | Stmt | Cycle 8 | Cycle 9 | Test added |
|--------|-----:|---------|---------|-----------:|
| `memory_writeback.py` | 229 | 0% | **100%** | +40 (PR1) |
| `manifest_llm.py`     |  67 | 0% | **100%** | +12 (PR2) |
| `auto_writeback.py`   |  66 | 0% | **100%** | +20 (PR2) |
| **Total**             | **362** | 0% | **100%** | **+72** |

Global TOTAL coverage: 72% → **76%** (+4pp).  Floor `fail_under`
72 → **76**.  Test count: 1122 → **1194** (+72 test, all passing).

### Phase 3 scope coverage

- **`memory_writeback.py`** (CLAUDE.md auto-maintain runtime, 5
  section detector + `MemoryWriteback` class + 4 method
  init/update/check/nest): 5 detector × 3 case (rich / malformed JSON
  fallback / empty repo) phủ Next.js / React / Expo / Node / Python /
  FastAPI / Django / Go / Rust / npm scripts / Makefile targets / 6
  layout convention / run-history malformed JSON tolerance / top-5
  error ranking / pytest / vitest / jest / conftest detection.  Class
  methods: dry-run idempotency, preserve user content ngoài marker,
  drift detection (missing/drifted/extra), path-traversal guard
  (`nest("..")` raise `ValueError`).
- **`manifest_llm.py`** (LLM-introspection manifest generator):
  frontmatter parser 5 nhánh (empty / inline list `[a, b, c]` /
  multi-line list `  - "x"` / quoted value / dash-orphan), `_ref_title`
  H1 + fallback, `build_manifest` 4 case (full + missing plugin →
  `FileNotFoundError` + SKILL.md optional + no refs dir), `emit` 2 case
  (default + explicit output + indent=4), `_main` argparse round-trip.
- **`auto_writeback.py`** (opportunistic CLAUDE.md refresh wired vào
  `session_start` hook): rate-limit (`should_refresh` 5 nhánh),
  opt-out marker (`auto_writeback_disabled`), state file lifecycle
  (`_read_last_run` malformed JSON / missing → 0.0; `_write_last_run`
  atomic write), `try_refresh` 7 nhánh (no_claude_md / opted_out /
  rate_limited / ok happy / force overrides opt-out / exception swallow
  primary + secondary state-write failure).

### Pragmatic floor decision (PR3 lock 72 → 76, NOT 80)

Spec ban đầu (cycle 8 RELEASE_NOTES) đặt mục tiêu Phase 3 = 80%
TOTAL.  Reality: phủ cả 3 module 0% (`memory_writeback` /
`manifest_llm` / `auto_writeback`) → **chỉ +4pp** (72 → 76), KHÔNG đủ
chạm 80%.  Còn ~277 stmt gap chủ yếu ở:

- `browser/manager.py` (178 stmt 0%)
- `mcp_client.py` (124 miss, 62%)
- `hook_interceptor.py` (62 miss, 33%)
- `auto_commit_hook.py` (59 miss, 40%)

Phase 4 (cycle 10) sẽ open scope sang `browser/*` submodule (domain
riêng, code-path lớn nhất chưa test) — phù hợp hơn việc cố push 80%
trong cycle 9 với floor break CI.  Same pragmatic pattern như cycle 8
PR2 (lock 72 thay vì 75).

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.18.0
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
- Global coverage TOTAL 76% floor (Phase 4 target: 80%, cần phủ
  `browser/*` 0% + reduce `mcp_client` / `hook_interceptor` /
  `auto_commit_hook` miss).
- mypy strict 9/44 module (chưa expand cycle 9 — defer cycle 10).

## Verify

```bash
git clone https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra
git checkout v0.18.0

VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q
# → 1194+ passed.

PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
# → 87/87 met=True.

rm -f .coverage && VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m coverage run --source=scripts/vibecodekit -m pytest tests -q
python3 -m coverage report --skip-empty --fail-under=76
# → TOTAL ≥ 76%, exit 0.

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

Không thay đổi từ v0.17.0 (thuần coverage milestone, không thay đổi
runtime / API surface):

| Tier        | Status   | Notes |
|-------------|----------|-------|
| Solo dev    | A+       | CLI demo ~1.3s; faker / error translator out-of-box. |
| Small team  | A+       | Permission engine strict-deny + audit log + team_mode CLI. |
| Enterprise  | A        | SECURITY.md + SBOM + 3-layer security CI + mypy strict 9 module + coverage 76%.  RBAC multi-tenant pending v0.19.0. |

## Tag instruction (manual)

Devin KHÔNG tự tag (thường không có perms).  User chạy:
```bash
git checkout main
git pull origin main
git tag v0.18.0
git push origin v0.18.0
```

## Next (v0.18.x / v0.19.0 roadmap)

- **Phase 4 coverage**: global TOTAL ≥ 80% (mở scope `browser/*`
  submodule + `hook_interceptor` + `auto_commit_hook` + `cli.py` qua
  subprocess test + `deploy_orchestrator.py`).
- **mypy strict expansion**: hiện 9/44 module → target +5 module
  (`memory_writeback` / `manifest_llm` / `auto_writeback` (mới phủ
  test) + `intent_router` / `conformance_audit`).
- **RBAC multi-tenant**: optional extension (nếu user demand).
- **CodeQL custom queries**: tune cho domain-specific anti-pattern.
