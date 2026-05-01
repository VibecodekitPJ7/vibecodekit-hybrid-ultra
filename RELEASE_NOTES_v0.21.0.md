# VibecodeKit Hybrid Ultra v0.21.0 — Coverage Phase 6 release

**Release date**: 2026-04-30
**Type**: Coverage milestone (minor bump)
**Backward compat**: 100% — no breaking changes.

## Highlights

Lần thứ hai liên tiếp kể từ Phase 5, floor `fail_under` lock đúng
**spec target = actual TOTAL**: cả hai đều **90%**.  Sau cycle 12
(PR1 #15, PR2 #16, PR3 này):

* Global TOTAL coverage: 85% → **90%** (+5pp).
* `pyproject.toml [tool.coverage.report] fail_under` 85 → **90**.
* 13 module gap lớn nhất sau cycle 11 đều ≥ 97%:

| Module | Trước | Sau |
|--------|------:|----:|
| `task_runtime.py` | 76% | **97%** |
| `module_workflow.py` | 67% | **99%** |
| `mcp_servers/core.py` | 55% | **97%** |
| `eval_select.py` | 74% | **100%** |
| `skill_discovery.py` | 71% | **98%** |
| `event_bus.py` | 73% | **100%** |
| `install_manifest.py` | 74% | **99%** |
| `compaction.py` | 82% | **100%** |
| `denial_store.py` | 84% | **99%** |
| `learnings.py` | 83% | **97%** |
| `intent_router.py` | 86% | **98%** |
| `browser/state.py` | 87% | **97%** |
| `cost_ledger.py` | 89% | **100%** |

* 173 test mới qua 2 PR (1451 → **1624** passed).
* Conformance 87/87 met=True, ruff F401/F841/F811 clean, mypy strict 9
  module clean (không thay đổi từ v0.20.0).

## Upgrade guide

```bash
pip install --upgrade vibecodekit-hybrid-ultra==0.21.0
# hoặc reproducible:
uv sync --frozen
```

KHÔNG breaking change.  Mọi public API (`permission_engine.classify_cmd`
/ `decide` / `decide_typed` / `PermissionDecision`,
`scaffold_engine.ScaffoldEngine`, `intent_router.IntentRouter`,
`install_manifest.install`, `verb_router.route_verb`, methodology 7
hàm public) giữ nguyên shape.  `tools.json` deterministic, không thay
đổi từ v0.20.0.

## Deprecations

- `permission_engine.decide()` dict-return shape vẫn emit
  `DeprecationWarning`; dùng `decide_typed()` trả `PermissionDecision`
  dataclass.  **Removal target: v1.0.0.**

## Known limitations

- RBAC multi-tenant không hỗ trợ; single-agent permission model chỉ.
  Roadmap v0.22.0+ nếu user demand.
- `conformance_audit.py` coverage 83% (82 → 83, +1pp).  Module lớn
  nhất package (1214 stmt) với 87 probe function — còn 203 miss, chủ
  yếu exception-path trong từng probe body.  Defer sang Phase 7
  (cycle 13+) vì mỗi probe cần scenario setup riêng.
- Global coverage TOTAL 90% floor.  Phase 7 target: 93% qua polish
  `conformance_audit` (83→≥95%) + đưa `cli.py` +
  `deploy_orchestrator.py` trở lại scope qua subprocess test.

## Verify

```bash
VIBECODE_UPDATE_PACKAGE="$(pwd)/update-package" PYTHONPATH=./scripts \
  python3 -m pytest tests -q
# → 1624 passed.

PYTHONPATH=./scripts python3 -m vibecodekit.conformance_audit --threshold 1.0
# → parity: 100.00% (87/87).

python3 -m coverage run --source=scripts/vibecodekit -m pytest tests -q
python3 -m coverage report --fail-under=90
# → TOTAL 90%, exit 0.
```

## Scorecard Enterprise readiness

Không thay đổi từ v0.20.0 (thuần coverage milestone, không đụng
runtime/API):

- Solo dev: **A+** (CLI demo ~1.3s, faker/translator out-of-box).
- Small team: **A+** (permission strict-deny + audit log + team_mode).
- Enterprise: **A** (SECURITY.md + SBOM + 3-layer security CI
  [pip-audit + actionlint + CodeQL] + mypy strict 9/44 + coverage 90%;
  RBAC multi-tenant pending v0.22.0+).

## Next (v0.21.1 / v0.22.0 roadmap)

- Phase 7 coverage: TOTAL ≥ **93%** qua polish `conformance_audit` +
  đưa `cli.py` / `deploy_orchestrator.py` trở lại scope qua subprocess
  test.
- Mypy strict expand 9/44 → 25+/44 module.
- Optional RBAC multi-tenant nếu user demand.
- CodeQL custom queries cho VibecodeKit-specific vuln pattern (shell
  injection via subprocess wrapper, path traversal via `open()`
  without guard).
