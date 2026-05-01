# Verify report — OTB Budget Module

> QA persona writes this.  Focus là **falsify** success claim, không
> confirm.  Gọi là VERIFY = RRI Reverse Interview Output theo
> `references/29-rri-reverse-interview.md` §6 (post-build phase).

## Inputs
- TIPs: `05-tips/tip-001-spec.md`, `tip-002-spec.md`, `tip-003-spec.md`
- Blueprint: `03-blueprint.md` §4a (RRI Requirements matrix)
- Commit range: `a1b2c3d4..c9d0e1f2` (TIP-001 → TIP-003 inclusive)
- Test branch: `release/otb-phase1-rc1`

## 1. Requirement traceability matrix

| REQ-ID  | Description                                                     | Status     | Evidence                                                      | Owner        |
|:--------|:----------------------------------------------------------------|:-----------|:--------------------------------------------------------------|:-------------|
| REQ-001 | Decimal(18,2) VND lưu chính xác                                 | DONE       | `tests/finance/otb/test_money.py::test_decimal_precision`     | dev_finance  |
| REQ-002 | Realtime actual vs plan refresh ≤ 30s                          | DONE       | Frontend polling + p95 latency 178ms                          | fe_finance   |
| REQ-003 | Error message rõ khi reject commit                              | DONE       | RRI-UX-010, RRI-UX-019; Vietnamese error bank                 | fe_finance   |
| REQ-004 | Approval workflow ≤500M BA / >500M CFO                          | DONE       | `tests/finance/otb/test_approve.py::test_threshold`           | dev_finance  |
| REQ-005 | Over-budget = actual > plan tháng                               | DONE       | `service.is_over_budget()` + 4 test cases                     | dev_finance  |
| REQ-006 | Concurrent commit detect/block                                  | DONE       | `test_concurrent.py::test_50_buyers_one_winner`               | dev_finance  |
| REQ-007 | Tết freeze 28 Tết → mùng 6                                      | DONE       | `tet_calendar.is_frozen()` + feature flag tests               | dev_platform |
| REQ-008 | Approve idempotent (Idempotency-Key)                            | DONE       | `test_approve.py::test_idempotent_replay`                     | dev_finance  |
| REQ-009 | DB migration offline 02:00–03:00 Sun                            | DONE       | Alembic 22.4s + ops runbook `docs/ops/otb-migration.md`       | operator     |
| REQ-010 | Reuse `finance.ledger.service` pattern                          | DONE       | Code review checklist sign-off                                | dev_finance  |
| REQ-011 | REST only, no GraphQL                                           | DONE       | OpenAPI spec snapshot — no `/graphql`                         | dev_finance  |
| REQ-012 | Audit trail mọi mutation                                        | DONE       | `audit_event` row per commit/approve/reject — invariant test  | dev_finance  |
| REQ-013 | Backup PITR 7d, full 90d                                        | DONE       | RDS snapshot policy doc + 3 restore drills                    | operator     |
| REQ-014 | Alert p95 > 500ms hoặc 5xx > 0.5%                               | DONE       | CloudWatch alarm `otb-api-p95-degraded`                        | operator     |
| REQ-015 | UI VND format `1.234.567,00 ₫`                                  | DONE       | RRI-UX-016 FLOW; manual review                                 | fe_finance   |
| REQ-016 | UI date DD/MM/YYYY                                              | DONE       | RRI-UX-017 FLOW; e2e test                                      | fe_finance   |
| REQ-017 | RBAC enforce decorator                                          | DONE       | `tests/finance/otb/test_rbac.py` (3 cases)                    | dev_finance  |
| REQ-018 | History pagination 20/page + filter                             | DONE       | `test_api.py::test_pagination_filter`                         | dev_finance  |
| REQ-019 | Excel template Bộ Tài chính                                     | DEFERRED   | Phase 2 — ticket OTB-440                                      | ba           |
| REQ-020 | PWA "Cần kết nối internet" khi offline                          | DONE       | RRI-UX-014 FLOW; manual offline test                           | fe_finance   |

## 2. Coverage summary

| Metric                          | Value |
|:--------------------------------|:------|
| Total REQ-* in blueprint        | 20    |
| Implemented (DONE)              | 19    |
| Partial                         | 0     |
| Missing                         | 0     |
| Deferred (excluded from gate)   | 1 (REQ-019) |
| Coverage %                      | 19 / (20 − 1) = **100 %** |

Release-gate condition: Coverage ≥ 85 % AND Missing == 0 → ✅ **PASS**.

## 3. Adversarial tests (≥ 3)

| #  | Test                                                                          | Outcome | Notes                                                                |
|:--:|:------------------------------------------------------------------------------|:--------|:---------------------------------------------------------------------|
|  1 | 50 buyer commit cùng `(period, store, category)`                              | pass    | 1 winner, 49 retry với 409                                           |
|  2 | Approve replay với cùng Idempotency-Key 100 lần                               | pass    | Cùng response 200, không double-mutate                               |
|  3 | Cookie tampered → request approve                                             | pass    | 401 + audit event `auth.cookie_tampered`                              |
|  4 | Tết freeze active + buyer commit                                              | pass    | 409 với message Vietnamese rõ                                         |
|  5 | DB connection drop giữa lúc audit_event INSERT                                | partial | Service log error + rollback transaction OK; *carry-forward to Phase 1.1* |
|  6 | Buyer mạng yếu, request timeout 30s, retry không Cancel                       | partial | UI show banner; *carry-forward ticket OTB-433*                       |
|  7 | CFO mobile bảng so sánh 7 cột scroll ngang                                    | partial | FRICTION; *carry-forward Phase 2 ticket OTB-431*                     |

## 4. Edge cases covered

- [x] Empty input (POST /budget với body rỗng → 422 schema error)
- [x] Malformed input (số âm, VND > Decimal max)
- [x] Over-sized input (1000 budget line trong 1 request → 413)
- [x] Concurrent duplicate request (test #1 ở §3)
- [x] Offline / network failure (RRI-UX-014, RRI-UX-015)
- [x] Permission denied mid-flight (test #3 ở §3)
- [x] Partial state (rollback during commit — test #5 ở §3)

## 5. Regressions

| Area                            | Before (v1.0-pre)   | After (v1.0)         | Delta            |
|:--------------------------------|:--------------------|:---------------------|:-----------------|
| `finance.ledger` test suite     | 1 240 pass / 0 fail | 1 240 pass / 0 fail  | 0 (isolated)     |
| `finance.purchase_order` p95    | 102 ms              | 105 ms               | +3 ms (acceptable) |
| Audit log throughput            | 1 200 evt/s          | 1 290 evt/s          | +7.5 % (positive)|
| OpenAPI snapshot                | n/a                 | 7 endpoints added     | controlled diff  |

## 6. Unverifiable claims

- Buyer onboard < 10 phút — kiểm chứng được trên 5 buyer mới (avg 7.2
  phút).  Claim "100% buyer onboard < 10 phút" *không* falsifiable trong
  Phase 1 (chưa đủ sample size); chỉ giữ "trung bình ≤ 10 phút".
- "Audit log đầy đủ 100 %" — falsifiable bằng invariant test
  `tests/test_audit_invariant.py`; *carry* bug RRI-T-008 (DB drop edge)
  vẫn còn nên giảm claim thành "≥ 99.9 % audit coverage trong điều
  kiện vận hành bình thường".

## 7. Scorecard feed-in (per axis)
```json
{
  "a_edge_cases":    {"score": 0.92, "evidence": "7/7 categories covered, 4 fully passing + 3 carry"},
  "a_fail_modes":    {"score": 0.93, "evidence": "12 failure modes documented, 11 tested"},
  "a_rollback":      {"score": 1.00, "evidence": "alembic downgrade + git revert tested"},
  "a_accessibility": {"score": 0.92, "evidence": "axe-core 0 critical, 2 minor (carry Phase 1.1)"}
}
```

## 8. Release decision

- [x] PROCEED — RRI-T gate PASS, RRI-UX gate PASS, all P0 REQ DONE,
      0 P0 fail/broken, 4 carry-forward đều P1.
- [ ] BLOCK

Sign-off:

- QA Lead: Phạm Hà — 2026-04-09
- Implementation Lead: Trần Minh — 2026-04-09
- Architect: Vibecode AI Architect — 2026-04-09
- Compliance Steward: Phạm Quang — 2026-04-09
