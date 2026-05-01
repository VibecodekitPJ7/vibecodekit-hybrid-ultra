# TIP-002 — OTB service layer + optimistic lock

> Risk class **3** (behaviour change in service module — concurrent commit).

## SVPFI
- **Scope:** `app/finance/otb/service.py`, `app/finance/otb/repository.py`, `app/finance/otb/concurrency.py`. Không touch API layer (TIP-003 sẽ wire).
- **Verification:** Adversarial concurrent test với 50 buyer commit cùng category → tất cả phải PASS (1 winner, 49 retry-with-conflict).
- **Principles:** Invariant #2 (optimistic lock), #5 (reuse ledger pattern), #6 (audit log invariant).
- **Failure modes:**
  1. ABA: buyer A commit, buyer B commit, buyer A retry với version cũ (vô tình) → mitigation: version monotonic increment + SQL `WHERE version = :expected`.
  2. Redis advisory lock không release nếu service crash mid-commit → mitigation: TTL 30s + finally-block release.
  3. Audit log fail (DB drop) → mitigation: rollback transaction, không silent-swallow.
  4. Race khi 2 buyer commit khác category cùng store → không phải race (lock theo `(period, store, category)` granularity).
- **Interfaces:**
  - `OtbService.commit(line_id: int, expected_version: int, actor: User) -> Budget`
  - `OtbService.is_over_budget(line: BudgetLine) -> bool`
  - Raises `OtbConcurrentEditError` (HTTP 409 ở TIP-003).

## Risk class
- [ ] Class 1 — read-only / additive
- [ ] Class 2 — schema-compatible mutation
- [x] Class 3 — behaviour change in a single module.
- [ ] Class 4 — cross-cutting / security

## Execution plan
```json
{
  "turns": [
    {"tool_uses": [
      {"tool": "read_file", "input": {"path": "app/finance/ledger/service.py"}}
    ]},
    {"tool_uses": [
      {"tool": "write_file", "input": {"path": "app/finance/otb/service.py"}},
      {"tool": "write_file", "input": {"path": "app/finance/otb/repository.py"}},
      {"tool": "write_file", "input": {"path": "app/finance/otb/concurrency.py"}}
    ]},
    {"tool_uses": [
      {"tool": "shell", "input": {"cmd": "pytest tests/finance/otb -q -k concurrent"}},
      {"tool": "shell", "input": {"cmd": "pytest tests/finance/otb/test_service.py -q"}}
    ]}
  ]
}
```

## Rollback
```
git revert <merge-sha>
# Service is additive: rollback chỉ cần revert code; schema giữ nguyên.
```

## Acceptance criteria

1. `tests/finance/otb/test_concurrent.py::test_50_buyers_one_winner` xanh — REQ-006.
2. `tests/finance/otb/test_service.py::test_audit_event_per_commit` xanh — REQ-012.
3. `tests/finance/otb/test_service.py::test_threshold_500m` xanh — REQ-004.
4. Coverage `app/finance/otb/service.py` ≥ 92%.
5. Code review sign-off của Security Auditor (Class 3 yêu cầu).

## Sign-off
- Implementation Lead: Trần Minh — 2026-04-05
- Security Auditor: Lê Hồng — 2026-04-05
- Compliance Steward: Phạm Quang — 2026-04-05
