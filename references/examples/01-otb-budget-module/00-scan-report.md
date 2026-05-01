# Scan report — OTB Budget Module

> Scout persona.  Read-only exploration của codebase hiện tại của khách
> hàng (mid-cap fashion retailer).  Không mutation.  Output này feed
> sang RRI để tự-trả lời các câu hỏi đã có evidence.

## Inputs
- Blueprint: chưa có (đây là module mới — sẽ tạo ở bước 3).
- Root: `app/finance/otb/` (đã agree với khách hàng từ kickoff call).

## Structure
```
app/
├── finance/
│   ├── ledger/                # Module hiện hữu — tham chiếu pattern
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── api.py
│   ├── purchase_order/        # Module hiện hữu — sẽ link OTB → PO
│   │   ├── models.py
│   │   └── api.py
│   └── otb/                   # ← Module mới sẽ build ở TIP-001..TIP-007
│       └── (empty)
├── core/
│   ├── auth/                  # CCCD/CMND middleware reuse
│   ├── audit/                 # Audit log table reuse — invariant strict
│   └── localization/          # VND format, DD/MM/YYYY
└── tests/
    └── finance/
        ├── ledger/
        └── purchase_order/
```

## Key modules (sẽ reuse / tham chiếu)
| Module                    | Role                                | Size (LOC) | Entry point                        |
|---------------------------|-------------------------------------|-----------:|------------------------------------|
| `core.auth.cccd`          | Vietnamese ID middleware            |        420 | `core.auth.cccd:verify_cccd`       |
| `core.audit.log`          | Append-only audit trail             |        310 | `core.audit.log:write_event`       |
| `core.localization.vnd`   | Currency formatter + parser         |        180 | `core.localization.vnd:format_vnd` |
| `finance.ledger.service`  | Generic ledger service (đã production) |     1245 | `finance.ledger.service:Ledger`    |
| `finance.purchase_order.api` | PO REST endpoints (đã production)  |        870 | `finance.purchase_order.api`       |

## Invariants discovered (codebase đã enforce)
- Mọi mutation tài chính ghi qua `core.audit.log:write_event` (codebase
  reject PR nếu service finance trực tiếp `INSERT/UPDATE` không qua
  audit hook → có CI rule trong `pre-commit` hiện hữu).
- Tất cả tiền lưu là `Decimal(precision=18, scale=2)` đơn vị VND
  (no float, no integer × 100).  Test `tests/test_money_invariant.py`
  đã enforce.
- `created_at`, `updated_at` luôn UTC + lưu kèm timezone offset
  `Asia/Ho_Chi_Minh` ở response layer.
- RBAC enforced ở `core.auth.rbac` — service layer không được tự kiểm
  tra role; phải đi qua decorator `@requires_role(...)`.

## Invariants chỉ partial-enforced (cần TIP cover)
- **Concurrent-edit detection chưa có** ở module ledger — sẽ thấy ở
  RRI-T D3 stress test → cần thiết kế optimistic lock cho OTB.
- **Audit log chưa có UI** — chỉ có CLI export.  Buyer/CFO phàn nàn
  không tra được history → flag cho VISION/BLUEPRINT.

## Dependencies
- Production: `fastapi==0.115.0`, `sqlalchemy==2.0.34`,
  `pydantic==2.9.2`, `psycopg[binary]==3.2.3`, `alembic==1.13.3`,
  `redis==5.1.1`, `python-dateutil==2.9.0.post0`.
- Dev/test: `pytest==8.3.3`, `pytest-asyncio==0.24.0`, `httpx==0.27.2`,
  `freezegun==1.5.1`, `coverage==7.6.4`.
- External services: PostgreSQL 16 (managed RDS), Redis 7.2 (ElastiCache),
  Sentry (saas), VNPay sandbox (chỉ giai đoạn 2 — không trong scope OTB).

## Patterns reused (Vibecode Pattern #)
| #  | Where used                              | How                                                              |
|----|-----------------------------------------|------------------------------------------------------------------|
| 9  | `core.auth.cccd` middleware             | Five-layer context defense — CCCD validate ở layer 2 (input)     |
| 6  | `core.audit.log` writer                 | Context modifier chain — append audit event sau mutation         |
| 4  | `finance.ledger.service` worker pool    | Concurrency-safe partitioning theo `account_id`                  |
| 35 | `finance.ledger.*` overall              | Enterprise-module pattern — separate models/repo/service/api     |

## Risks surfaced for blueprint
1. Concurrent over-budget commit — 2 buyer cùng commit budget cùng category, race tiền vượt plan → cần optimistic lock + post-commit validation.
2. CFO approve qua mobile mạng yếu — có thể double-approve nếu retry → idempotency key bắt buộc.
3. VND rounding khi tính `actual / plan × 100%` — phải cố định round half-even.
4. Tết freeze — không cho commit budget từ 28 Tết → mùng 6 (regulatory hoặc internal policy?).
5. CCCD vs CMND legacy — buyer cũ dùng CMND 9 số, mới CCCD 12 số.  Auth middleware đã handle nhưng audit log lưu raw → mask khi xuất report.

## Open questions cho Architect/Homeowner
- [ ] Budget granularity: theo tháng / quý / mùa (SS/AW)?
- [ ] Approval threshold: ai duyệt > X tỷ VND?
- [ ] Có cần forecast (linear regression vs LSTM) hay chỉ plan-vs-actual?
- [ ] Mobile native hay PWA cho CFO?
- [ ] Export Excel có cần đúng template Bộ Tài chính không?
