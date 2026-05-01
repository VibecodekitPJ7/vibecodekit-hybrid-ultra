# TIP-003 — OTB API endpoints + idempotency

> Risk class **2** (schema-compatible — thêm endpoints, không đổi DB).

## SVPFI
- **Scope:** `app/finance/otb/api.py` (7 endpoints), `app/finance/otb/idempotency.py`. Reuse middleware `core.auth.cccd` + `core.audit.log`.
- **Verification:** Adversarial test gồm: (a) approve replay với cùng `Idempotency-Key` → cùng response 200; (b) approve khác key → 200 mới; (c) buyer commit khi Tết freeze → 409 với message rõ.
- **Principles:** REST only (REQ-011), idempotent approve (REQ-008), error message rõ (REQ-003), RBAC enforce (REQ-017), pagination (REQ-018).
- **Failure modes:**
  1. Idempotency cache miss khi Redis down → mitigation: trả 503 + retry-after, không silent-allow duplicate.
  2. Pagination integer overflow nếu client gửi `page=99999999` → mitigation: cap `page * size ≤ 10000`, trả 400.
  3. RBAC bypass nếu client gửi cookie tampered → mitigation: middleware đã verify, test `test_rbac_bypass_attempt` cover.
- **Interfaces:**
  - `POST /api/finance/otb/budget` body=`BudgetCreate`
  - `PATCH /api/finance/otb/budget/{id}` body=`BudgetUpdate`, header `If-Match: <version>`
  - `POST /api/finance/otb/budget/{id}/commit` (no body)
  - `POST /api/finance/otb/budget/{id}/approve` body=`ApprovalDecision`, header `Idempotency-Key`
  - `GET /api/finance/otb/budget?status=...&page=1&size=20`
  - `GET /api/finance/otb/budget/{id}`
  - `GET /api/finance/otb/budget/{id}/history?page=1&size=20`

## Risk class
- [ ] Class 1
- [x] Class 2 — schema-compatible mutation (additive endpoints).
- [ ] Class 3
- [ ] Class 4

## Execution plan
```json
{
  "turns": [
    {"tool_uses": [
      {"tool": "read_file", "input": {"path": "app/finance/purchase_order/api.py"}}
    ]},
    {"tool_uses": [
      {"tool": "write_file", "input": {"path": "app/finance/otb/api.py"}},
      {"tool": "write_file", "input": {"path": "app/finance/otb/idempotency.py"}}
    ]},
    {"tool_uses": [
      {"tool": "shell", "input": {"cmd": "pytest tests/finance/otb/test_api.py -q"}},
      {"tool": "shell", "input": {"cmd": "pytest tests/finance/otb/test_approve.py -q"}}
    ]}
  ]
}
```

## Rollback
```
git revert <merge-sha>
# API là additive — rollback chỉ revert code; FE pages chưa refer endpoints này nên không broken.
```

## Acceptance criteria

1. `tests/finance/otb/test_api.py::test_post_budget_201` xanh.
2. `tests/finance/otb/test_approve.py::test_idempotent_replay` xanh — REQ-008.
3. `tests/finance/otb/test_api.py::test_error_message_clear` xanh — REQ-003.
4. `tests/finance/otb/test_api.py::test_pagination_filter` xanh — REQ-018.
5. `tests/finance/otb/test_rbac.py::test_buyer_cannot_approve` xanh — REQ-017.
6. OpenAPI spec không có `/graphql` (REQ-011).
7. Coverage `app/finance/otb/api.py` ≥ 90%.

## Sign-off
- Implementation Lead: Trần Minh — 2026-04-06
- Compliance Steward: Phạm Quang — 2026-04-06
