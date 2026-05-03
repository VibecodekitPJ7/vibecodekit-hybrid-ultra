# RRI Requirements Matrix — OTB Budget Module

> Produced by Contractor during step 2 (RRI).  Homeowner đã sign-off
> ngày 2026-04-02 trước khi qua VISION.  Dùng canonical question bank
> trong `assets/rri-question-bank.json` (project type = `enterprise-module`,
> `expected_min = 45`).

---

## Project type & question budget
- **Project type:** `enterprise-module`
- **Minimum question budget:** 45 (đã hỏi 52)
- **Personas covered:** `end_user` (buyer/BA), `ba`, `qa`, `developer`, `operator` (5/5).
- **Modes covered:** `CHALLENGE`, `GUIDED`, `EXPLORE` (3/3, mỗi persona × mode ≥ 1 câu).

## Auto-answered (from SCAN)

| #  | Question                                        | Auto answer (evidence)                                                |
|---:|:------------------------------------------------|:----------------------------------------------------------------------|
| 1  | Currency unit + precision?                      | VND, `Decimal(18, 2)` (`tests/test_money_invariant.py`)               |
| 2  | Date format?                                    | DD/MM/YYYY UI, ISO-8601 storage (`core.localization.vnd`)             |
| 3  | Auth flow?                                      | CCCD/CMND middleware (`core.auth.cccd`)                               |
| 4  | Audit trail required?                           | YES — `core.audit.log` đã enforce CI rule                              |
| 5  | Existing PO module reuse?                       | `finance.purchase_order.api` đã production                            |
| 6  | RBAC pattern?                                   | `@requires_role(...)` decorator (`core.auth.rbac`)                    |

## Asked questions — by persona × mode (subset đại diện 16/52)

| Q-ID            | Persona     | Mode      | Question (paraphrased)                                               | Answer                                       |
|-----------------|-------------|-----------|----------------------------------------------------------------------|----------------------------------------------|
| S-EU-EX-01      | end_user    | EXPLORE   | Buyer thường nhập budget khi nào trong tháng?                         | Cuối tháng, deadline 28 hàng tháng           |
| S-EU-CH-02      | end_user    | CHALLENGE | Nếu hệ thống reject commit, buyer thấy lỗi gì?                       | Hiện đang chỉ "Lỗi không xác định" (PAINFUL) |
| S-EU-GU-03      | end_user    | GUIDED    | Buyer có cần xem actual vs plan realtime không?                      | Có — tối thiểu refresh < 30s                 |
| S-BA-CH-04      | ba          | CHALLENGE | Định nghĩa "over-budget" là gì? > plan, > plan + 5%, hay > LY actual? | > plan của tháng (đơn vị VND)                |
| S-BA-CH-05      | ba          | CHALLENGE | Approval threshold thay đổi theo ai?                                 | > 500M VND → CFO duyệt; ≤ 500M BA duyệt      |
| S-BA-GU-06      | ba          | GUIDED    | Có cần forecast không?                                               | Giai đoạn 1 không; giai đoạn 2 LSTM          |
| S-QA-CH-07      | qa          | CHALLENGE | Có scenario 2 buyer commit cùng category cùng lúc?                   | Có — bắt buộc test concurrent                |
| S-QA-GU-08      | qa          | GUIDED    | Tết freeze window là gì?                                             | 28 Tết → mùng 6 (cấu hình runtime)           |
| S-QA-EX-09      | qa          | EXPLORE   | Approve qua mạng yếu có rủi ro double-approve?                       | Có — cần idempotency key                     |
| S-DV-GU-10      | developer   | GUIDED    | Reuse `finance.ledger.service` pattern?                              | Yes — copy 90%, thêm OTB-specific lock       |
| S-DV-CH-11      | developer   | CHALLENGE | DB migration online hay offline?                                     | Offline 02:00 AM Sun (giờ Việt Nam)          |
| S-DV-EX-12      | developer   | EXPLORE   | Có cần GraphQL hay chỉ REST?                                          | Chỉ REST — match phần còn lại của app        |
| S-OP-CH-13      | operator    | CHALLENGE | Backup retention policy?                                             | 7-day point-in-time, 90-day full daily       |
| S-OP-GU-14      | operator    | GUIDED    | Alerting threshold?                                                  | p95 > 500ms hoặc 5xx > 0.5%                  |
| S-OP-EX-15      | operator    | EXPLORE   | Multi-region failover cần không?                                     | Không trong scope giai đoạn 1                |
| S-EU-EX-16      | end_user    | EXPLORE   | CFO approve trên mobile có offline mode không?                        | Không — required online (kèm clear UI)       |

## Requirements — by persona

| REQ-ID  | Requirement                                                                                       | Source (Q-ID) | Priority | Persona     |
|:--------|:--------------------------------------------------------------------------------------------------|:--------------|:--------:|:-----------|
| REQ-001 | Buyer nhập budget plan theo (category × tháng × store), đơn vị VND chính xác `Decimal(18, 2)`     | S-EU-EX-01    | P0       | end_user    |
| REQ-002 | Buyer xem realtime actual vs plan, refresh ≤ 30s                                                  | S-EU-GU-03    | P0       | end_user    |
| REQ-003 | Hiển thị error message rõ ràng khi reject commit (no "Lỗi không xác định")                        | S-EU-CH-02    | P0       | end_user    |
| REQ-004 | Approval workflow: ≤ 500M VND → BA duyệt; > 500M → CFO duyệt                                     | S-BA-CH-05    | P0       | ba          |
| REQ-005 | Định nghĩa over-budget = actual > plan của tháng đó                                              | S-BA-CH-04    | P1       | ba          |
| REQ-006 | Concurrent commit cùng category phải detect và block (optimistic lock)                            | S-QA-CH-07    | P0       | qa          |
| REQ-007 | Tết freeze (28 Tết → mùng 6) — block tất cả commit, cấu hình runtime                              | S-QA-GU-08    | P1       | qa          |
| REQ-008 | Approve API idempotent (idempotency-key header bắt buộc cho mạng yếu)                             | S-QA-EX-09    | P0       | qa          |
| REQ-009 | DB migration offline window 02:00 → 03:00 AM Sun                                                 | S-DV-CH-11    | P1       | developer   |
| REQ-010 | Reuse pattern từ `finance.ledger.service` — không re-implement audit/lock                         | S-DV-GU-10    | P1       | developer   |
| REQ-011 | REST endpoints — không thêm GraphQL                                                              | S-DV-EX-12    | P2       | developer   |
| REQ-012 | Audit trail mọi mutation (insert/update/approve/reject) → bảng `audit_event`                      | SCAN auto     | P0       | qa          |
| REQ-013 | Backup PITR 7 ngày, full 90 ngày                                                                 | S-OP-CH-13    | P1       | operator    |
| REQ-014 | Alerting p95 > 500ms hoặc 5xx > 0.5%                                                             | S-OP-GU-14    | P1       | operator    |
| REQ-015 | UI VND format `1.234.567,00 ₫`, không dùng `,` thousands                                         | SCAN auto     | P0       | end_user    |
| REQ-016 | UI date format DD/MM/YYYY                                                                        | SCAN auto     | P0       | end_user    |
| REQ-017 | RBAC: chỉ buyer được commit; chỉ BA/CFO được approve; CFO được force-override                    | S-BA-CH-05    | P0       | ba          |
| REQ-018 | History page paginated (20 entries/page) + filter theo người + theo ngày                          | S-EU-GU-03    | P1       | end_user    |
| REQ-019 | Export Excel template Bộ Tài chính (cột "Mã chương / Mã NSNN") — giai đoạn 2                      | open-Q        | P3       | ba          |
| REQ-020 | Mobile CFO PWA (no native) — show clear "Cần kết nối internet" khi offline                        | S-EU-EX-16    | P0       | end_user    |

## Mode coverage check (must be all-green before VISION)

| Persona     | CHALLENGE asked | GUIDED asked | EXPLORE asked |
|:-----------|:---------------:|:------------:|:-------------:|
| end_user    |        ✓        |      ✓       |       ✓       |
| ba          |        ✓        |      ✓       |       ✓       |
| qa          |        ✓        |      ✓       |       ✓       |
| developer   |        ✓        |      ✓       |       ✓       |
| operator    |        ✓        |      ✓       |       ✓       |

## Sign-off

- Contractor: VibecodeKit Architect (Devin Run #1) — 2026-04-02
- Homeowner: CFO + Head of Buying — 2026-04-02 (`APPROVED`)
