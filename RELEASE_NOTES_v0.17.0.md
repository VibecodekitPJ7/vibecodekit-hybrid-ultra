# VibecodeKit Hybrid Ultra v0.17.0 — Enterprise-ready release

**Release date**: 2026-04-30
**Type**: Enterprise hardening (minor bump, semver `0.16.2 → 0.17.0`)
**Backward compat**: 100% — zero breaking changes runtime.

## Highlights

- **Security**:
  - `SECURITY.md` + threat model + responsible-disclosure policy.
  - `permission_engine` 9-pattern strict-deny (network, fs traversal,
    privileged exec, secret extraction…) + audit log rate-cap 60/60s.
  - Typed `PermissionDecision` dataclass (`decide_typed()`), legacy
    dict shape `decide()` deprecated → removal v1.0.0.
- **Supply chain**:
  - `uv.lock` reproducible install.
  - `.github/workflows/security.yml`: pip-audit (SCA) + CycloneDX SBOM
    weekly cron + on-PR.
  - `.github/workflows/actionlint.yml`: workflow lint.
  - `.github/workflows/codeql.yml` (cycle 8 PR3): CodeQL SAST scan
    `security-extended` + `security-and-quality` queries weekly cron
    (Tuesday 06:00 UTC) + on-PR.
  - Dependabot enable cho pip + github-actions ecosystem.
- **Type safety**:
  - mypy `--strict` clean trên **9 core module** (was 5 ở cycle 6 / 0
    ở cycle 5): `permission_engine`, `scaffold_engine`, `verb_router`,
    `denial_store`, `_audit_log`, `tool_executor`, `team_mode`,
    `task_runtime`, `subagent_runtime` (was 68 errors total ở cycle 5).
- **Test discipline**:
  - 1119+ tests, **coverage TOTAL 72% gate** (Phase 2b, was 60% Phase 1
    cycle 6 → 70% Phase 2a cycle 7 → 72% Phase 2b cycle 8).
  - Per-module gates ≥ 80%: `tool_executor` 98%, `team_mode` 98%,
    `vn_faker` 100%, `vn_error_translator` 100%.
- **Observability**: structured `logging` (stderr human-readable mặc
  định + JSON khi `VIBECODE_LOG_JSON=1`), audit log writeback.
- **Governance**: canonical org `VibecodekitPJ7` (rebrand #9 — FINAL,
  hard-locked CI guard, KHÔNG có env-gated bypass).

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.17.0
# hoặc reproducible:
uv sync --frozen
```

KHÔNG có migration script bắt buộc.  Caller dùng `decide()` được
khuyến nghị migrate sang `decide_typed()` — xem `SECURITY.md` §
"Permission engine API" và `examples/permission_engine_typed.py`.

## Deprecations

- `permission_engine.decide()` dict-return shape emit
  `DeprecationWarning("decide() returns dict; use decide_typed() for "
  "PermissionDecision dataclass; removal v1.0.0")`. Dùng
  `decide_typed()` trả `PermissionDecision`. **Removal target: v1.0.0.**

## Known limitations

- RBAC multi-tenant không được hỗ trợ; single-agent permission model.
- `vn_error_translator.py` per-module coverage 100% nhưng chỉ 20 test
  case — semantic edge case khác (e.g. unicode codepoint ngoài BMP)
  chưa được test.  Theo dõi cycle 9.
- Global coverage TOTAL 72% floor (Phase 3 target: 80%, đạt được khi
  scope mở rộng phủ `memory_writeback.py` 0% / `manifest_llm.py` 0% /
  `auto_writeback.py` 0%).

## Verify

```bash
git clone https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra
git checkout v0.17.0

VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q
# → 1119+ passed.

PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
# → 87/87 met=True.

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

python3 -m ruff check scripts/vibecodekit examples --select F401,F841,F811
# → All checks passed!
```

## Tier readiness

| Tier        | Status   | Notes |
|-------------|----------|-------|
| Solo dev    | A+       | CLI demo ~1.3s; faker / error translator out-of-box. |
| Small team  | A+       | Permission engine strict-deny + audit log + team_mode CLI. |
| Enterprise  | A        | SECURITY.md + SBOM + 3-layer security CI + mypy strict 9 module. RBAC multi-tenant pending v0.18.0. |

(Tăng từ A− cycle 7 → **A/A+** cycle 8 — production-ready cho cả 3 tier.)

## Tag instruction (manual)

Devin KHÔNG tự tag (thường không có perms).  User chạy local:
```bash
git checkout main
git pull origin main
git tag v0.17.0
git push origin v0.17.0
```

## Next (v0.17.1 / v0.18.0 roadmap)

- **Phase 3 coverage**: global TOTAL ≥ 80% (mở scope `memory_writeback`,
  `manifest_llm`, `auto_writeback`).
- **mypy strict full**: hiện 9/44 module → target 44/44.
- **RBAC multi-tenant**: optional extension (nếu user demand).
- **CodeQL custom queries**: tune cho domain-specific anti-pattern.
