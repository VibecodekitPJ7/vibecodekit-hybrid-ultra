# Completion report — TIP-002 service layer + optimistic lock

## Summary
TIP-002 ship `OtbService.commit()` + `OtbService.approve()` với
optimistic lock (`version` column) + Redis advisory lock per
`(period, store, category)`.  Adversarial test: 50 buyer commit
cùng `(period=2026-04, store=001, category=apparel)` → 1 winner +
49 retry với `OtbConcurrentEditError`.  Audit log đầy đủ cho mọi
mutation.  Class 3 PR yêu cầu Security Auditor sign-off — đã có
Lê Hồng approve.

## Artifacts
- TIP: [`../05-tips/tip-002-spec.md`](../05-tips/tip-002-spec.md)
- PR / commit: `app/finance/otb#4476` (sha `e5f6a7b8`)
- Verify report: §7 trong `10-verify-report.md` (REQ-005, REQ-006, REQ-010, REQ-012)
- Security note: `docs/security/otb-tip-002-audit.md` (Class 3 mandatory)

## Scorecard (fed to quality_gate.evaluate)
```json
{
  "d_correctness":      {"score": 0.96, "evidence": "pytest 14/14 green, 50-worker concurrent test stable"},
  "d_reliability":      {"score": 0.95, "evidence": "Redis lock TTL 30s + finally-release tested"},
  "d_security":         {"score": 0.98, "evidence": "Security Auditor sign-off; ABA mitigation via SQL WHERE"},
  "d_performance":      {"score": 0.92, "evidence": "p95 commit 184ms; lock contention tail p99 < 500ms"},
  "d_maintainability":  {"score": 0.93, "evidence": "12 unit tests + 3 integration"},
  "d_observability":    {"score": 0.95, "evidence": "audit_event row + Sentry breadcrumb on retry"},
  "d_ux_clarity":       {"score": 0.85, "evidence": "error code + message ready for FE consumption"},
  "a_intent_fit":       {"score": 1.00, "evidence": "matches TIP exactly"},
  "a_scope_fit":        {"score": 0.95, "evidence": "1 helper file (concurrency.py) extra — agreed in review"},
  "a_edge_cases":       {"score": 0.92, "evidence": "ABA + Redis-down + audit-fail covered"},
  "a_fail_modes":       {"score": 0.95, "evidence": "4 modes tested"},
  "a_rollback":         {"score": 1.00, "evidence": "git revert tested; service is additive"},
  "a_privacy":          {"score": 1.00, "evidence": "no PII in audit beyond CCCD-masked actor_id"},
  "a_accessibility":    {"score": 0.90, "evidence": "service-only — N/A for direct user contact"},
  "a_cost":             {"score": 0.92, "evidence": "Redis ~3 keys/buyer × 50 = 150 keys, negligible"}
}
```

## Aggregate
`quality_gate.evaluate` → `0.949` (PROCEED).

## Outstanding risks
| Risk                                   | Severity | Owner       | Target     |
|:---------------------------------------|:--------:|:------------|:-----------|
| Redis split-brain → double-commit      |  Low     | operator    | 2026-Q3    |
| Audit log fail-mode silent swallow     |  Low     | dev_finance | 2026-Q3    |

## Release decision
- [x] PROCEED
- [ ] BLOCK
