# Case study — OTB (Open-To-Buy) Budget Module

> Pre-baked end-to-end run của **VIBECODE-MASTER 8-step workflow** áp dụng
> trên một enterprise-module thực tế: hệ thống quản lý ngân sách OTB cho
> retail buyer Vietnamese SaaS.  Mục đích là cho team mới vừa onboard có
> thể đọc tuần tự 11 file dưới đây để hiểu cách RRI → VISION → BLUEPRINT
> → TIPs → BUILD → RRI-T/UX → COVERAGE → VERIFY chạy thật, không phải
> chỉ template rỗng.

## Bối cảnh module

- **Domain:** Open-To-Buy budget management (retail finance).
- **User base:** 50+ buyer + 8 BA + 3 CFO (mid-cap fashion retailer Việt Nam).
- **Localization:** VND format, DD/MM/YYYY, CCCD/CMND auth, Vietnamese
  collation cho tên category.
- **Concurrency:** 50+ buyer cùng lúc nhập budget cuối kỳ; CFO approve
  qua mobile.
- **Compliance:** Audit trail mọi thay đổi (bắt buộc theo Thông tư
  200/2014/TT-BTC §40).

## Mục lục

| #   | File                              | Mô tả                                                  |
|----:|:----------------------------------|:-------------------------------------------------------|
| 0   | [`00-scan-report.md`](00-scan-report.md)                 | Scout's read-only scan codebase ban đầu                |
| 1   | [`01-rri-requirements.md`](01-rri-requirements.md)       | RRI matrix với REQ-001..REQ-020                        |
| 2   | [`02-vision.md`](02-vision.md)                           | Project type + stack proposal được Homeowner duyệt    |
| 3   | [`03-blueprint.md`](03-blueprint.md)                     | Blueprint locked sau VISION sign-off                  |
| 4   | [`04-task-graph.md`](04-task-graph.md)                   | DAG of TIPs (3 entry + dependencies)                  |
| 5   | [`05-tips/`](05-tips)                                    | 3 TIP specs điển hình (Class 1/2/3)                   |
| 6   | [`06-completion-reports/`](06-completion-reports)        | 3 completion report tương ứng                         |
| 7   | [`07-rri-t-results.jsonl`](07-rri-t-results.jsonl)       | 19 RRI-T entries → `evaluate_rri_t()` gate=PASS       |
| 8   | [`08-rri-ux-results.jsonl`](08-rri-ux-results.jsonl)     | 19 RRI-UX entries → `evaluate_rri_ux()` gate=PASS     |
| 9   | [`09-coverage-matrix.md`](09-coverage-matrix.md)         | Module × Dimension scoring final                       |
| 10  | [`10-verify-report.md`](10-verify-report.md)             | VERIFY = RRI Reverse Interview output                  |

## Cách dùng

### 1. Đọc tuần tự để học workflow
Đi từ `00-scan-report.md` → `10-verify-report.md` theo thứ tự.  Mỗi file
trỏ tới template gốc trong `assets/templates/` để bạn so sánh "rỗng" vs
"đã điền".

### 2. Replay RRI-T / RRI-UX runner
Hai file `.jsonl` được tạo theo schema của
`methodology.evaluate_rri_t()` và `methodology.evaluate_rri_ux()`.
Verify gate=PASS bằng cách:

```bash
PYTHONPATH=./scripts python3 -c "
from pathlib import Path
from vibecodekit import methodology
root = Path('references/examples/01-otb-budget-module')
print('RRI-T :', methodology.evaluate_rri_t(root / '07-rri-t-results.jsonl')['gate'])
print('RRI-UX:', methodology.evaluate_rri_ux(root / '08-rri-ux-results.jsonl')['gate'])
"
```

Kỳ vọng:

```
RRI-T : PASS
RRI-UX: PASS
```

### 3. Re-use cấu trúc cho module mới
Copy directory này, đổi tên thành `references/examples/02-<your-module>/`,
chỉnh sửa nội dung theo domain mới.  Bạn không cần copy `.jsonl` nếu
module mới chưa chạy RRI-T/UX, nhưng phải copy 9 file `.md` để giữ
parity với conformance probe `_probe_case_study_otb_budget`.

## Bản quyền
Case study này hư cấu — số liệu/tên buyer/category dưới đây không
phản ánh khách hàng thực.  Mọi tương đồng là ngẫu nhiên.
