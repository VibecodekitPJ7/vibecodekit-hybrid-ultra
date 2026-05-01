# Vision — OTB Budget Module

> Contractor's proposal sau RRI.  Homeowner reply `APPROVED`
> 2026-04-03.  Dựa trên `references/30-vibecode-master.md` §3 +
> `methodology.PROJECT_STACK_RECOMMENDATIONS` (row `enterprise-module`).

---

## Project type
`Enterprise-module` — bolt-on module gắn vào codebase finance hiện có
của khách hàng.  Reuse stack hiện hữu (FastAPI + SQLAlchemy + Postgres),
không introduce framework mới.

## Proposed stack

| Aspect            | Stack                                       | Rationale                                                              |
|:------------------|:---------------------------------------------|:-----------------------------------------------------------------------|
| Framework         | FastAPI 0.115 (đã có)                        | Reuse — không thêm runtime mới                                          |
| Styling / UI      | Next.js + Tailwind + shadcn/ui (đã có)       | Buyer dùng web; CFO dùng PWA                                            |
| State / data      | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic     | Đã production; thêm 4 bảng mới + 2 migration                            |
| Auth              | CCCD/CMND middleware (`core.auth.cccd`)      | Reuse 100%                                                              |
| Hosting           | AWS RDS + ECS Fargate (đã có)                | Same VPC, same observability stack (Sentry + CloudWatch)                |
| Notable extras    | Redis lock (concurrent commit), idempotency-key (Approve), feature flag `OTB_TET_FREEZE_ENABLED` | Mới ra Phase 1                                                          |

## Module surface (high-level)

```
finance/otb/
├── models.py          # Budget, BudgetLine, ApprovalRequest, AuditTrailLink
├── repository.py      # CRUD + concurrent-safe upsert (Redis lock)
├── service.py         # Domain logic: commit, approve, calc actual vs plan
├── tet_calendar.py    # Tết freeze window resolver (config-driven)
├── api.py             # 7 REST endpoints (xem §dưới)
└── migrations/
    ├── v001_create_otb_tables.py
    └── v002_index_actual_vs_plan.py
```

## REST endpoints (Phase 1, locked)

| Verb   | Path                                    | Auth          | Idempotent |
|:-------|:----------------------------------------|:--------------|:----------:|
| POST   | `/api/finance/otb/budget`               | buyer         | No         |
| PATCH  | `/api/finance/otb/budget/{id}`          | buyer (owner) | No         |
| GET    | `/api/finance/otb/budget`               | buyer/ba/cfo  | —          |
| GET    | `/api/finance/otb/budget/{id}`          | buyer/ba/cfo  | —          |
| POST   | `/api/finance/otb/budget/{id}/commit`   | buyer (owner) | No         |
| POST   | `/api/finance/otb/budget/{id}/approve`  | ba/cfo        | **Yes**    |
| GET    | `/api/finance/otb/budget/{id}/history`  | buyer/ba/cfo  | —          |

## Out of scope (Phase 1)
- Forecast (LSTM) — Phase 2.
- Excel template Bộ Tài chính — Phase 2.
- Multi-region failover — không cần Phase 1.
- Mobile native app — PWA đủ cho CFO.

## Risks & open trade-offs (cho Homeowner đọc)

1. **Optimistic lock vs pessimistic lock:** chọn **optimistic** (version
   column) vì đơn giản và tương thích với pattern `finance.ledger.service`.
   Trade-off: buyer phải retry nếu race; chấp nhận được vì 50 buyer / 200 SKU.
2. **Tết freeze runtime config vs hardcode:** chọn **runtime config**
   (`feature_flag` table + Redis cache) — dễ update mà không deploy.
3. **Audit log table mới vs reuse `core.audit.log`:** **reuse** — giữ
   single source of truth, viết qua adapter `OtbAuditAdapter`.
4. **Idempotency-key TTL:** 24h trong Redis — đủ cho mobile retry; sau
   24h request mới được coi là độc lập.

## Decision: APPROVED bởi Homeowner

```
Homeowner reply (2026-04-03 09:14 +07):
> APPROVED.  Lưu ý:
> - Phase 1 không cần forecast — đồng ý.
> - PWA cho CFO: ưu tiên responsive design, không cần install prompt.
> - Migration window 02:00 Sun — confirm với DBA team.
```

→ Contractor proceeds tới BLUEPRINT.
