# Blueprint — OTB Budget Module

> Locked sau VISION sign-off (2026-04-03).  Mọi thay đổi sau lock phải
> đi qua change-request → re-approval của Homeowner.

## 1. Problem statement (≤ 200 words)

Buyer của chuỗi retail fashion 220 store đang quản lý OTB budget bằng
file Excel chia sẻ qua email.  Hệ quả: (a) race condition cuối tháng
khi nhiều buyer commit cùng lúc, (b) không có audit trail nên CFO
không biết ai đổi số nào, (c) approval workflow phụ thuộc vào BA copy
số sang ERP thủ công, (d) Tết freeze window phụ thuộc vào reminder
email của BA.  Module mới sẽ replace flow Excel này bằng web UI +
REST API tích hợp vào codebase finance hiện hữu, với invariant:
**không một VND nào được commit/approve mà thiếu audit log đầy đủ.**

## 2. Scope
- **In scope:** `app/finance/otb/` (models/repo/service/api/migrations),
  3 frontend pages (`/otb/plan`, `/otb/approve`, `/otb/history`),
  2 Alembic migrations, 1 feature-flag config (`OTB_TET_FREEZE_ENABLED`).
- **Out of scope:** forecast (Phase 2), Excel template Bộ Tài chính
  (Phase 2), multi-region failover, native mobile app.

## 3. Success metrics

| Metric                                  | Current (Excel)  | Target (OTB module) | How measured                                    |
|:----------------------------------------|:-----------------|:--------------------|:------------------------------------------------|
| Time-to-commit budget (buyer)           | ~12 min          | ≤ 3 min p95         | Frontend telemetry (`commit_form.duration_ms`)  |
| Approval round-trip (BA + CFO)          | ~36 h            | ≤ 4 h p95           | DB: `created_at` of `commit` → `approve`       |
| % budget với audit trail đầy đủ         | ~62 %            | 100 %               | `core.audit.log` invariant test                 |
| Concurrent commit corruption rate       | ~3 sự cố / quý   | 0                   | RRI-T D3 stress test (50 buyer)                 |
| p95 `GET /budget?refresh` latency       | n/a              | ≤ 250 ms            | CloudWatch metric                               |

## 4. Entities & data flows

```
┌────────────────────────────────────────────────────────────────────────┐
│                     OTB Budget Module — Phase 1                        │
└────────────────────────────────────────────────────────────────────────┘

      Buyer (web)            BA / CFO (web + PWA)        Operator (CLI)
         │                           │                          │
         │ POST /budget              │ POST /budget/{id}        │
         │ PATCH /budget/{id}        │   /approve               │ alembic
         │ POST  /budget/{id}/commit │ GET  /budget?status=...  │ migrations
         ▼                           ▼                          ▼
   ┌─────────────────────────────────────────────┐         ┌────────────┐
   │             OTB API (FastAPI)               │         │ DB schema  │
   │   ┌──────────┐  ┌──────────┐  ┌──────────┐  │         │ migrations │
   │   │ Commit   │  │ Approve  │  │ Query    │  │         └────┬───────┘
   │   │ handler  │  │ handler  │  │ handler  │  │              │
   │   └────┬─────┘  └────┬─────┘  └────┬─────┘  │              │
   └────────┼─────────────┼─────────────┼────────┘              │
            ▼             ▼             ▼                       ▼
       ┌────────────────────────────────────┐         ┌────────────────┐
       │  OtbService (domain rules)         │         │ PostgreSQL 16  │
       │   - validate Tết freeze            │◄────────┤ otb_budget     │
       │   - optimistic lock (version)      │         │ otb_budget_line│
       │   - approval threshold ≤500M / >   │         │ otb_approval   │
       └────────────────┬───────────────────┘         │ audit_event    │
                        │                              └────────────────┘
                        ▼
                 ┌──────────────┐         ┌──────────────────┐
                 │ Redis lock   │         │ core.audit.log   │
                 │ (commit)     │         │ (append-only)    │
                 │ idempotency  │         └──────────────────┘
                 │ key (approve)│
                 └──────────────┘
```

Names of every node (5 services + 4 tables + 2 stores) đã match với
codebase hiện hữu.

## 4a. RRI Requirements matrix

> Mọi `REQ-*` từ `01-rri-requirements.md` map sang section blueprint
> + acceptance criteria.  Verify report (BƯỚC 7) reuses bảng này.

| REQ-ID  | Requirement (one-line)                                                | Blueprint section          | Source (RRI Q#) | Acceptance criteria                                           |
|:--------|:----------------------------------------------------------------------|:---------------------------|:----------------|:--------------------------------------------------------------|
| REQ-001 | Buyer nhập budget plan VND `Decimal(18,2)`                            | §4 Data flows / §5 inv #1  | S-EU-EX-01      | `tests/finance/otb/test_money.py::test_decimal_precision`     |
| REQ-002 | Realtime actual vs plan refresh ≤ 30s                                 | §4 Data flows              | S-EU-GU-03      | Frontend polling 30s + p95 latency ≤ 250ms                    |
| REQ-003 | Error message rõ khi reject commit                                    | §6 Risk #1                 | S-EU-CH-02      | RRI-UX critique U6 FEEDBACK ≥ 90% FLOW                        |
| REQ-004 | Approval workflow ≤500M BA / >500M CFO                                | §5 inv #3                  | S-BA-CH-05      | `tests/finance/otb/test_approve.py::test_threshold`           |
| REQ-005 | Over-budget = actual > plan tháng                                     | §4 Data flows              | S-BA-CH-04      | `service.is_over_budget(line) == (line.actual > line.plan)`   |
| REQ-006 | Concurrent commit detect/block (optimistic lock)                      | §5 inv #2 + §6 Risk #1     | S-QA-CH-07      | `tests/finance/otb/test_concurrent.py` (50 worker)            |
| REQ-007 | Tết freeze 28 Tết → mùng 6                                            | §5 inv #4                  | S-QA-GU-08      | `tet_calendar.is_frozen(today)` + feature flag                |
| REQ-008 | Approve idempotent (Idempotency-Key)                                  | §6 Risk #2                 | S-QA-EX-09      | `test_approve_idempotent` (replay key cho cùng kết quả)       |
| REQ-009 | DB migration offline 02:00–03:00 Sun                                  | §8 Rollback                | S-DV-CH-11      | `alembic upgrade head` < 60s; ops runbook                     |
| REQ-010 | Reuse `finance.ledger.service` pattern                                | §4 + §5 inv #5             | S-DV-GU-10      | Code review: copy-paste rate ≥ 70% — không re-implement audit |
| REQ-011 | REST only, no GraphQL                                                 | §4 API surface             | S-DV-EX-12      | OpenAPI spec — không có `/graphql`                            |
| REQ-012 | Audit trail mọi mutation                                              | §5 inv #6                  | SCAN auto       | `audit_event` row tồn tại cho mỗi commit/approve/reject       |
| REQ-013 | Backup PITR 7d, full 90d                                              | §8 Rollback                | S-OP-CH-13      | RDS snapshot policy doc                                       |
| REQ-014 | Alert p95 > 500ms hoặc 5xx > 0.5%                                     | §6 Risk #3                 | S-OP-GU-14      | CloudWatch alarm cấu hình                                     |
| REQ-015 | UI VND format `1.234.567,00 ₫`                                        | §5 inv #7                  | SCAN auto       | RRI-UX U7 VN TEXT 100% FLOW                                   |
| REQ-016 | UI date DD/MM/YYYY                                                    | §5 inv #7                  | SCAN auto       | RRI-UX U7 VN TEXT 100% FLOW                                   |
| REQ-017 | RBAC enforce decorator                                                | §5 inv #8                  | S-BA-CH-05      | `tests/finance/otb/test_rbac.py`                              |
| REQ-018 | History page paginated 20/page + filter                               | §4 API surface             | S-EU-GU-03      | `GET /history?page=1&filter=...` pagination test              |
| REQ-019 | Excel Bộ Tài chính — Phase 2                                          | §2 Out of scope            | open-Q          | DEFERRED                                                      |
| REQ-020 | PWA "Cần kết nối internet" khi offline                                | §6 Risk #4                 | S-EU-EX-16      | RRI-UX U6 FEEDBACK BROKEN-OFFLINE → FLOW                      |

## 4b. Task decomposition preview

```
Estimated tasks: 7 TIPs
Estimated effort: ~840 min total (14 h)

├── TIP-001: Schema + migration (Class 2)                  (~120 min)
├── TIP-002: Service layer + optimistic lock (Class 3)     (~180 min)
├── TIP-003: API endpoints (Class 2)                       (~120 min)
├── TIP-004: Tết freeze + feature flag (Class 1)           (~ 60 min)
├── TIP-005: Frontend plan/approve/history pages (Class 3) (~180 min)
├── TIP-006: PWA offline banner (Class 1)                  (~ 60 min)
└── TIP-007: RRI-T + RRI-UX runs (Class 1)                 (~120 min)
```

| TIP-ID  | Title                              | REQ covered                    | Effort (min) | Owner          |
|:--------|:-----------------------------------|:-------------------------------|:-------------|:---------------|
| TIP-001 | Schema + migration                 | REQ-001, REQ-009, REQ-013      | 120          | dev_finance    |
| TIP-002 | Service + optimistic lock          | REQ-005, REQ-006, REQ-010, REQ-012 | 180     | dev_finance    |
| TIP-003 | API endpoints                      | REQ-003, REQ-004, REQ-008, REQ-011, REQ-017, REQ-018 | 120 | dev_finance |
| TIP-004 | Tết freeze + feature flag          | REQ-007                        | 60           | dev_platform   |
| TIP-005 | Frontend pages                     | REQ-002, REQ-015, REQ-016      | 180          | fe_finance     |
| TIP-006 | PWA offline banner                 | REQ-020                        | 60           | fe_finance     |
| TIP-007 | RRI-T + RRI-UX runs                | All P0 P1                      | 120          | qa_lead        |

## 5. Invariants (must always hold)

1. Mọi tiền lưu là `Decimal(precision=18, scale=2)` đơn vị VND.
2. Mọi commit + approve đi qua optimistic lock (column `version`).
3. Approval threshold strict: ≤500M VND BA / >500M CFO; CFO có
   `force_override` flag được audit log.
4. Tết freeze window đọc từ `tet_calendar.is_frozen(date)` —
   feature flag toggle.
5. Service layer reuse `finance.ledger.service`; không re-implement
   audit hook hoặc lock primitive.
6. Mọi mutation ghi 1 row `audit_event` (đi qua `core.audit.log:write_event`).
7. UI hiển thị VND `1.234.567,00 ₫` + DD/MM/YYYY (RRI-UX U7).
8. RBAC enforce qua `@requires_role(...)`; service không tự kiểm tra role.

## 6. Risks & mitigations

| Risk                                              | Likelihood | Impact | Mitigation                                                      |
|:--------------------------------------------------|:----------:|:------:|:----------------------------------------------------------------|
| Race condition cùng category cuối tháng           |  High      |  High  | Optimistic lock (`version`) + Redis advisory lock per `category_id` |
| Mobile mạng yếu → CFO double-approve              |  Medium    |  High  | `Idempotency-Key` 24h Redis; replay → cùng kết quả              |
| p95 spike khi 50 buyer cùng poll                  |  Medium    |  Medium| Index `(period_id, store_id, category_id)`; CloudWatch alarm    |
| PWA offline silent fail                           |  Medium    |  Medium| Service worker show banner "Cần kết nối internet"               |
| Tết freeze bypass do bug feature flag             |  Low       |  High  | Default-on khi flag missing; CI test `test_tet_default_on`      |

## 7. Decision log

| Date       | Decision                          | Rationale                                       | Alternatives rejected            |
|:-----------|:----------------------------------|:------------------------------------------------|:---------------------------------|
| 2026-04-03 | Optimistic > pessimistic lock     | Đơn giản, match pattern ledger                   | Pessimistic (Redis advisory) — over-engineered cho 50 buyer |
| 2026-04-03 | Reuse `core.audit.log`            | Single source of truth                           | Tạo bảng audit riêng — dùng adapter là đủ |
| 2026-04-03 | PWA only, no native               | Resource Phase 1 không đủ                        | React Native — Phase 3+          |
| 2026-04-03 | Idempotency 24h TTL               | Mobile retry < 24h là realistic                  | 1h (quá ngắn), 7d (state bloat)  |

## 8. Rollback plan

- Schema: `alembic downgrade -1` (kiểm tra trước trên staging — < 30s).
- Code: `git revert <merge-sha>`; redeploy ECS service trong 5 phút.
- Feature flag fallback: `OTB_API_DISABLED=1` → API trả 503 với
  message "Module đang bảo trì" (cấu hình runtime, không cần deploy).
- DB-only rollback: tất cả ghi qua `audit_event` nên có thể replay
  từ snapshot 7-day PITR.

## 9. Sign-off

- Architect: Vibecode AI Architect — 2026-04-03
- Implementation Lead: Trần Minh (dev_finance) — 2026-04-03
- Security Auditor: Lê Hồng (security) — 2026-04-03
- Compliance Steward: Phạm Quang (compliance) — 2026-04-04
