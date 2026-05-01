# VibecodeKit Hybrid Ultra v0.20.0 — Coverage Phase 5 release

**Release date**: 2026-04-30
**Type**: Coverage milestone (minor bump)
**Backward compat**: 100% — no breaking changes.

## Highlights

Lần đầu kể từ Phase 1, floor `fail_under` lock đúng **spec target =
actual TOTAL**: cả hai đều **85%**.  Sau cycle 11 (PR1 #12, PR2 #13,
PR3 này):

* Global TOTAL coverage: 80% → **85%** (+5pp).
* `pyproject.toml [tool.coverage.report] fail_under` 80 → **85**.
* 8 module gap lớn nhất sau cycle 10 đều ≥ 90%:

| Module | Trước | Sau |
|--------|------:|----:|
| `mcp_client.py` | 62% | **90%** |
| `browser/cli_adapter.py` | 33% | **99%** |
| `approval_contract.py` | 66% | **100%** |
| `memory_retriever.py` | 33% | **98%** |
| `recovery_engine.py` | 58% | **98%** |
| `dashboard.py` | 50% | **95%** |
| `mcp_servers/selfcheck.py` | 23% | **95%** |
| `doctor.py` | 68% | **94%** |

* 141 test mới qua 2 PR (1310 → **1451** passed).
* Conformance 87/87 met=True, ruff F401/F841/F811 clean, mypy strict 9
  module clean (không thay đổi từ v0.19.0).

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.20.0
# hoặc reproducible:
uv sync --frozen
```

KHÔNG breaking change.  Mọi public API (`permission_engine.classify_cmd`
/ `decide` / `decide_typed` / `PermissionDecision`,
`scaffold_engine.ScaffoldEngine`, `intent_router.IntentRouter`,
`install_manifest.install`, `verb_router.route_verb`, methodology 7
hàm public) giữ nguyên shape.  `tools.json` deterministic, không thay
đổi từ v0.19.0.

## Deprecations

- `permission_engine.decide()` dict-return shape vẫn emit
  `DeprecationWarning`; dùng `decide_typed()` trả `PermissionDecision`
  dataclass.  **Removal target: v1.0.0.**

## Known limitations

- Global TOTAL còn ~15% chưa cover — chủ yếu:
  - `conformance_audit.py` 217 miss / 1214 stmt (82%) — module lớn
    nhất, code-path nhánh switch theo probe slug, defer Phase 6.
  - `task_runtime.py` 114 miss / 468 stmt (76%) — async daemon code,
    cần stub asyncio.
  - `module_workflow.py` 80 miss / 239 stmt (67%) — multi-step
    workflow runner, cần fixture set lớn.
  - `browser/server.py` 9 stmt / 0% — nhánh tạo daemon process, defer
    cùng `cli.py` / `deploy_orchestrator.py` qua subprocess test.
- RBAC multi-tenant không hỗ trợ; single-agent permission model chỉ.
- Mypy strict 9/44 module (chưa thay đổi từ v0.17.0).

## Verify

```bash
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q
# → 1451+ passed.

PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
# → parity: 100.00% (87/87).

python3 -m coverage run --source=scripts/vibecodekit -m pytest tests --tb=no
python3 -m coverage report --fail-under=85
# → TOTAL 85%, exit 0.
```

## Next (v0.20.1 / v0.21.0 roadmap)

- Phase 6 coverage: global TOTAL ≥ 90% qua mở scope
  `conformance_audit.py` + `task_runtime.py` + `module_workflow.py` +
  `cli.py` / `deploy_orchestrator.py` qua subprocess test.
- Mypy strict expand 9/44 → 20+/44 module.
- Optional RBAC multi-tenant nếu user demand.
- CodeQL custom queries cho VibecodeKit-specific vuln pattern.
