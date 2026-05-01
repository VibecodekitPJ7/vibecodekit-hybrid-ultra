# TIP-001 — OTB schema + Alembic migration

> Risk class **2** (schema-compatible mutation, append-only).
> One TIP = one mergeable PR.  Verify report dưới completion-report.

## SVPFI
- **Scope:** `app/finance/otb/models.py`, `app/finance/otb/migrations/v001_create_otb_tables.py`, `app/finance/otb/__init__.py`. Không touch ledger / PO module.
- **Verification:** Đã pre-verify migration chạy < 30s trên staging snapshot (220 store × 24 tháng × 8 category = ~42k rows seed). Adversarial test còn lại: rollback `alembic downgrade -1` + replay forward.
- **Principles:** Invariant #1 (Decimal 18,2), #6 (audit trail mọi mutation). Reuse pattern `finance.ledger.models`.
- **Failure modes:**
  1. Migration timeout > 60s khi DB > 100k rows → mitigation: `CREATE INDEX CONCURRENTLY` (Postgres) cho composite index `(period_id, store_id, category_id)`.
  2. Foreign key cascade delete vô tình xoá audit row → mitigation: FK `audit_event_id` để `ON DELETE RESTRICT`.
  3. Default value cho `version=0` không apply lên existing rows (không có existing rows nên N/A nhưng ghi rõ trong runbook).
- **Interfaces:**
  - `class Budget(Base)` — table `otb_budget`.
  - `class BudgetLine(Base)` — table `otb_budget_line`.
  - `class ApprovalRequest(Base)` — table `otb_approval`.
  - `class AuditTrailLink(Base)` — view-like join helper, không bảng riêng.

## Risk class
- [ ] Class 1 — read-only / additive; no user-visible change.
- [x] Class 2 — schema-compatible mutation (append-only).
- [ ] Class 3 — behaviour change in a single module.
- [ ] Class 4 — cross-cutting / security-sensitive / DB migration.

## Execution plan
```json
{
  "turns": [
    {"tool_uses": [
      {"tool": "list_files", "input": {"path": "app/finance/ledger"}},
      {"tool": "read_file",  "input": {"path": "app/finance/ledger/models.py"}}
    ]},
    {"tool_uses": [
      {"tool": "write_file", "input": {"path": "app/finance/otb/models.py"}},
      {"tool": "write_file", "input": {"path": "app/finance/otb/migrations/v001_create_otb_tables.py"}}
    ]},
    {"tool_uses": [
      {"tool": "shell", "input": {"cmd": "alembic upgrade head"}},
      {"tool": "shell", "input": {"cmd": "pytest tests/finance/otb/test_money.py -q"}}
    ]}
  ]
}
```

## Rollback
```
alembic downgrade -1
git revert <merge-sha>
```

## Acceptance criteria

1. `tests/finance/otb/test_money.py::test_decimal_precision` xanh — REQ-001.
2. `alembic upgrade head` < 60s trên staging với DB sao chép production (220 store).
3. `audit_event` row tồn tại cho mỗi commit/approve/reject.
4. Index `idx_otb_budget_line_period_store_cat` được tạo CONCURRENTLY (no lock > 5s).
5. `from app.finance.otb.models import Budget, BudgetLine, ApprovalRequest` import sạch — không circular.

## Sign-off
- Implementation Lead: Trần Minh — 2026-04-04
- Compliance Steward: Phạm Quang — 2026-04-04
