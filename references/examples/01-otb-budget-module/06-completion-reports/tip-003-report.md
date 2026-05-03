# Completion report — TIP-003 API endpoints + idempotency

## Summary
TIP-003 ship 7 REST endpoints (`POST /budget`, `PATCH`, `GET`, `commit`,
`approve`, `history`).  Approve có `Idempotency-Key` header bắt buộc
(TTL 24h Redis) → replay trả cùng response 200.  Pagination
`?page=&size=` capped 10000.  Error message Vietnamese rõ ràng (no
"Lỗi không xác định").  RBAC enforce qua `@requires_role`.  Coverage
api.py 93%.  Đã merge PR #4481.

## Artifacts
- TIP: [`../05-tips/tip-003-spec.md`](../05-tips/tip-003-spec.md)
- PR / commit: `app/finance/otb#4481` (sha `c9d0e1f2`)
- Verify report: §7 trong `10-verify-report.md` (REQ-003, REQ-004, REQ-008, REQ-011, REQ-017, REQ-018)
- Security note: N/A (Class 2)

## Scorecard (fed to quality_gate.evaluate)
```json
{
  "d_correctness":      {"score": 0.94, "evidence": "pytest 22/22 green, OpenAPI snapshot diff clean"},
  "d_reliability":      {"score": 0.93, "evidence": "Redis idempotency replay 24h soak test"},
  "d_security":         {"score": 0.96, "evidence": "RBAC bypass attempt test green; cookie tamper rejected"},
  "d_performance":      {"score": 0.94, "evidence": "p95 GET /budget 142ms (target ≤ 250ms)"},
  "d_maintainability":  {"score": 0.92, "evidence": "Pydantic v2 schemas + 22 tests"},
  "d_observability":    {"score": 0.95, "evidence": "Sentry breadcrumb cho approve replay events"},
  "d_ux_clarity":       {"score": 0.90, "evidence": "Vietnamese error message bank — RRI-UX U6 90% FLOW"},
  "a_intent_fit":       {"score": 1.00, "evidence": "matches TIP exactly — 7 endpoints"},
  "a_scope_fit":        {"score": 1.00, "evidence": "no files outside declared scope"},
  "a_edge_cases":       {"score": 0.92, "evidence": "Idempotency replay + cap pagination + RBAC tested"},
  "a_fail_modes":       {"score": 0.93, "evidence": "Redis-down + invalid-key + tamper covered"},
  "a_rollback":         {"score": 1.00, "evidence": "Additive — git revert clean"},
  "a_privacy":          {"score": 0.96, "evidence": "PII không log raw (CCCD masked, account_id hashed)"},
  "a_accessibility":    {"score": 0.90, "evidence": "API only — FE TIP-005 cover WCAG"},
  "a_cost":             {"score": 0.94, "evidence": "Redis ~1 key per approve, TTL 24h"}
}
```

## Aggregate
`quality_gate.evaluate` → `0.945` (PROCEED).

## Outstanding risks
| Risk                                   | Severity | Owner       | Target     |
|:---------------------------------------|:--------:|:------------|:-----------|
| Idempotency cache stampede sau outage  |  Medium  | operator    | 2026-Q3    |
| Rate-limit chưa có (chờ TIP-008)       |  Low     | dev_platform| 2026-Q4    |

## Release decision
- [x] PROCEED
- [ ] BLOCK
