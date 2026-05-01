# Completion report — TIP-001 schema + Alembic migration

## Summary
TIP-001 ship 3 bảng (`otb_budget`, `otb_budget_line`, `otb_approval`) và
1 Alembic migration `v001_create_otb_tables`.  Migration chạy 22.4s
trên staging snapshot 220 store × 24 tháng.  Index composite tạo
CONCURRENTLY (no lock > 2s).  Audit FK `ON DELETE RESTRICT`.  Đã merge
qua PR #4471 sau Compliance Steward sign-off.

## Artifacts
- TIP: [`../05-tips/tip-001-spec.md`](../05-tips/tip-001-spec.md)
- PR / commit: `app/finance/otb#4471` (sha `a1b2c3d4`)
- Verify report: §7 trong `10-verify-report.md` (REQ-001, REQ-009, REQ-013)
- Security note: N/A (Class 2 không yêu cầu)

## Scorecard (fed to quality_gate.evaluate)
```json
{
  "d_correctness":      {"score": 1.00, "evidence": "pytest 5/5 green, coverage 96%"},
  "d_reliability":      {"score": 0.95, "evidence": "rollback alembic downgrade tested 3x"},
  "d_security":         {"score": 1.00, "evidence": "no new tool classes; FK ON DELETE RESTRICT"},
  "d_performance":      {"score": 0.92, "evidence": "alembic upgrade 22.4s p95 < 30s"},
  "d_maintainability":  {"score": 0.95, "evidence": "docstrings + 8 tests"},
  "d_observability":    {"score": 0.90, "evidence": "audit_event hook present"},
  "d_ux_clarity":       {"score": 0.90, "evidence": "no UI in this TIP — schema docs complete"},
  "a_intent_fit":       {"score": 1.00, "evidence": "matches TIP exactly — 3 tables only"},
  "a_scope_fit":        {"score": 1.00, "evidence": "no files outside declared scope"},
  "a_edge_cases":       {"score": 0.90, "evidence": "6/7 covered (multi-region failover deferred)"},
  "a_fail_modes":       {"score": 0.95, "evidence": "3 modes documented + test"},
  "a_rollback":         {"score": 1.00, "evidence": "downgrade tested in CI"},
  "a_privacy":          {"score": 1.00, "evidence": "no PII surfaced; CCCD masked at audit layer"},
  "a_accessibility":    {"score": 0.90, "evidence": "schema-only — N/A (carry-over from blueprint baseline)"},
  "a_cost":             {"score": 0.95, "evidence": "1 new index, ~120 MB"}
}
```

## Aggregate
`quality_gate.evaluate` → `0.957` (PROCEED threshold ≥ 0.90).

## Outstanding risks
| Risk                          | Severity | Owner       | Target     |
|:------------------------------|:--------:|:------------|:-----------|
| Index bloat sau 12 tháng      |  Low     | dev_finance | 2026-Q4    |
| Snapshot restore latency      |  Low     | operator    | 2026-Q3    |

## Release decision
- [x] PROCEED
- [ ] BLOCK
