# Hướng dẫn cho người mới — VibecodeKit Hybrid Ultra v0.25.0

> **Đối tượng:** Người không phải developer — chủ sản phẩm, founder,
> nhà tư vấn, nhà phân tích, người đang dùng ChatGPT / Claude Code /
> Cursor để build project nhỏ và muốn đi từ "ý tưởng" tới "sản phẩm
> chạy được" mà chỉ cần **mô tả dự án bằng tiếng Việt**.
>
> **Bạn cần biết gì trước:** chỉ cần biết gõ chat, copy-paste, mở
> terminal đôi lúc.  Không cần biết Python / Git / TypeScript.
>
> **Tốc độ đọc:** ~20 phút.  Bạn có thể nhảy thẳng tới
> [§4 Worked example](#4-worked-example--app-quản-lý-chi-tiêu-gia-đình)
> nếu muốn xem ngay 1 ví dụ A→Z.

---

## Mục lục

1. [Tool này là gì?](#1-tool-này-là-gì)
2. [Bạn cần chuẩn bị gì?](#2-bạn-cần-chuẩn-bị-gì)
3. [Cài đặt 3 bước](#3-cài-đặt-3-bước)
4. [Worked example — App quản lý chi tiêu gia đình](#4-worked-example--app-quản-lý-chi-tiêu-gia-đình)
5. [Hiểu output: pipeline 8 bước](#5-hiểu-output-pipeline-8-bước)
6. [Tính năng mới v0.22.0](#6-tính-năng-mới-v0220)
7. [10 lệnh hay dùng nhất](#7-10-lệnh-hay-dùng-nhất)
8. [FAQ + xử lý lỗi](#8-faq--xử-lý-lỗi)
9. [Bước tiếp theo](#9-bước-tiếp-theo)

---

## 1. Tool này là gì?

VibecodeKit Hybrid Ultra là **bộ "luật chơi"** cho AI coding agent (ChatGPT,
Claude Code, Claw Code, Codex, Cursor) để biến **một câu mô tả tiếng Việt
mơ hồ** thành **một dự án phần mềm chạy được** — qua 8 bước có thể
kiểm tra được:

```
Mô tả 1 dòng  →  scan kho code  →  hỏi 16 câu RRI  →  chốt vision
   ↓
chốt blueprint  →  chia 5-30 task TIP  →  build từng task  →  verify
   ↓
sản phẩm chạy được
```

Bạn không cần học pipeline.  Bạn chỉ gõ:

```
/vibe Tôi muốn làm app quản lý chi tiêu cho gia đình
```

…và để tool tự đi qua 8 bước.  Mỗi bước in ra một file `.md` để bạn
duyệt.  Nếu bước nào lỗi, tool sẽ hỏi lại bằng tiếng Việt.

**Vì sao cần tool này thay vì gõ thẳng vào ChatGPT?**

| Nếu bạn... | Vấn đề | VibecodeKit giúp |
|:----------|:-------|:-----------------|
| Mô tả "làm app" → AI sinh code thẳng | Code lỗi vặt, thiếu test, thiếu spec | Bắt AI làm 8 bước có document trước khi code |
| Mô tả khác lần 2 | AI quên context | Lưu blueprint + RRI vào `.md`, AI đọc lại |
| Muốn kiểm tra UX | "Trông OK" — không có thước đo | RRI-UX gate 7 dimension × 8 stress axes |
| Muốn tránh lỗi UI hay gặp | Tự nhớ thuộc | Anti-pattern catalog 12 lỗi kèm BAD/GOOD |
| Cần chọn màu / font | Tốn thời gian Pinterest | 7 palette + 5 font pair sẵn theo ngành |

---

## 2. Bạn cần chuẩn bị gì?

Trước khi bắt đầu, đảm bảo máy bạn có 3 thứ:

### 2.1. Python ≥ 3.9

Mở Terminal (Mac/Linux) hoặc PowerShell (Windows), gõ:

```bash
python3 --version
```

- Nếu thấy `Python 3.9.x` trở lên → OK ✓
- Nếu lỗi `command not found` → tải Python tại
  https://www.python.org/downloads/ (chọn bản 3.11 hoặc 3.12, tick
  "Add to PATH" lúc cài).

### 2.2. Một trong các AI coding CLI

Chọn 1 (không cần cả 3):

| CLI | Phù hợp khi | Tải |
|:----|:-----------|:----|
| **Claude Code** | Bạn có account Anthropic, muốn UX đẹp | https://docs.anthropic.com/en/docs/claude-code |
| **ChatGPT (web)** | Không muốn cài CLI, dùng trình duyệt | https://chat.openai.com (paid) |
| **Cursor** | Bạn quen IDE-style, muốn code + chat trộn | https://cursor.sh |

Nếu chưa có gì cả: dùng **ChatGPT web** đơn giản nhất — không cần cài.

### 2.3. ~5 phút để cài VibecodeKit

Xem [§3 Cài đặt](#3-cài-đặt-3-bước) bên dưới.

> **Mẹo:** Nếu bạn dùng macOS, chạy `brew install python@3.12 git` trước.
> Nếu Windows, cài Python từ https://python.org và Git từ https://git-scm.com.

---

## 3. Cài đặt 3 bước

### Bước 3.1 — Tải tool

Mở Terminal, đi tới thư mục bạn muốn lưu (ví dụ Desktop):

```bash
cd ~/Desktop
git clone https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra.git
cd vibecodekit-hybrid-ultra
```

Hoặc nếu chưa có Git: tải zip tại
https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra/archive/refs/heads/main.zip
→ giải nén → mở Terminal trong thư mục đã giải nén.

### Bước 3.2 — Cài runtime

```bash
pip3 install -e .
```

Lệnh này cài 1 gói Python tên `vibecodekit-hybrid-ultra` để bạn có thể
gõ `vibecodekit` từ bất cứ đâu.

### Bước 3.3 — Test cài đúng

```bash
vibecodekit demo
```

Bạn nên thấy output kiểu:

```
====================================================================
  VibecodeKit Hybrid Ultra — 6-step offline demo (zero LLM call)
====================================================================
  Step 1/6: doctor health-check               OK
  Step 2/6: permission engine (5 cases)       OK
  Step 3/6: conformance audit (92 probes)     OK
  Step 4/6: scaffold preview                  OK
  Step 5/6: intent router                     OK
  Step 6/6: MCP selfcheck                     OK
====================================================================
  Demo complete in 1.0s — zero network, zero LLM calls.
====================================================================
```

Thấy "Demo complete" → cài thành công ✓

> **Có lỗi?** Đọc [§8 FAQ](#8-faq--xử-lý-lỗi) trước khi panic.

---

## 4. Worked example — "App quản lý chi tiêu gia đình"

Đây là ví dụ A→Z giả lập user nontech mô tả 1 ý tưởng → tool đi qua 8
bước → ra blueprint chi tiết.  Bạn có thể copy-paste y nguyên.

### 4.1. Mở AI CLI ưa thích

Ví dụ với **Claude Code**:

```bash
cd ~/Desktop/vibecodekit-hybrid-ultra
claude-code
```

Hoặc **Cursor**: mở Cursor, kéo thả thư mục `vibecodekit-hybrid-ultra`
vào IDE, mở Composer (Cmd/Ctrl+I).

### 4.2. Gõ master command `/vibe` với mô tả tiếng Việt

```
/vibe Tôi muốn làm app quản lý chi tiêu cho gia đình.

Yêu cầu:
- Nhập khoản chi (ngày, số tiền VND, danh mục: ăn uống / nhà cửa /
  giao thông / giải trí / khác)
- Xem tổng theo tuần / tháng
- Cảnh báo khi vượt ngân sách danh mục
- Cho phép 2 vợ chồng cùng nhập từ điện thoại
- Tiếng Việt, format VND có dấu phẩy ngàn
```

### 4.3. Tool tự đi qua 8 bước

AI sẽ chạy tự động qua các bước (mỗi bước in ra 1 file `.md`):

#### Bước 1 — `/vibe-scan`: tool quét repo

Tool đọc thư mục dự án (lúc này còn rỗng), tạo file `scan-report.md`
liệt kê: stack hiện tại = chưa có, không có `package.json`, không có
git history.  Đề xuất: dự án mới hoàn toàn → đi sang `/vibe-rri`.

#### Bước 2 — `/vibe-rri`: tool hỏi 16 câu RRI tiếng Việt

Đây là bước quan trọng nhất.  Tool hỏi **16 câu Reverse Requirement
Interview** (RRI) để chốt phạm vi.  Bạn trả lời từng câu bằng tiếng
Việt:

```
Q1 — Ai là người dùng chính? (chọn 1-3)
A: Vợ chồng, ~30 tuổi, có 1 con nhỏ, thu nhập 15-30 triệu/tháng

Q2 — Người dùng đang dùng giải pháp nào?
A: Excel + Google Sheet, hoặc app Money Lover phiên bản miễn phí

Q3 — Tại sao họ không hài lòng?
A: Excel mất công nhập tay, Money Lover chỉ 1 tài khoản, không share

Q4 — Khi nào họ muốn dùng app?
A: Sau bữa ăn, đi siêu thị về, cuối tháng

Q5 — 3 tính năng "phải có" (must-have) là gì?
A: 1. Nhập nhanh 1-tap
   2. Xem tổng tháng
   3. 2 người cùng nhập

... (16 câu, ~10 phút điền)
```

> Gặp câu khó? Tool có **Vietnamese persona suggestions** — gõ "skip"
> nó sẽ điền giả định mặc định, bạn xem rồi sửa.

Output: `rri-results.md` — đầy đủ 16 Q&A và 20 REQ-001..REQ-020.

#### Bước 3 — `/vibe-vision`: chốt stack

Tool đọc `rri-results.md`, đề xuất:

```markdown
# Vision

**Project type:** Mobile-first PWA (Progressive Web App)
**Why:** 2 user dùng từ điện thoại, không cần install native app

**Stack:**
- Frontend: Next.js 14 (App Router) + Tailwind + shadcn/ui
- Backend: tRPC + Prisma ORM
- DB: SQLite (dev) → Turso (production, edge SQLite)
- Auth: NextAuth (Google login — 2 vợ chồng đã có Gmail)
- Hosting: Vercel free tier

**Why not native?**
- 2 user, không cần performance native
- Cài đặt 0 phút (mở trình duyệt là dùng được)
- Chi phí $0/tháng tại Vercel free + Turso free
```

Bạn approve hoặc đề nghị thay đổi (ví dụ: "không dùng Google login,
dùng email + password").  Tool cập nhật.

#### Bước 4 — `/vibe-blueprint`: chốt kiến trúc

Tool sinh `blueprint.md` chi tiết:

- **Data model** (4 bảng: User, Account, Transaction, Category)
- **API endpoints** (8 endpoints tRPC: createTransaction, listTransactions,
  getMonthlySummary, ...)
- **UI screens** (6 screen: Login, Home, AddTransaction, History,
  MonthlyReport, Settings)
- **Invariants** (10 ràng buộc bất biến: amount > 0, date không tương
  lai, mỗi user chỉ thấy data của account mình, …)
- **Risks** (5 rủi ro top: timezone, race-condition khi 2 vợ chồng nhập
  cùng lúc, format VND, encoding tiếng Việt, GDPR/Vietnam Cybersecurity Law)

#### Bước 5 — `/vibe-task graph`: chia thành TIPs

Tool chia blueprint thành **5-15 Tactical Implementation Plans (TIPs)**
sắp theo DAG (đồ thị phụ thuộc):

```
TIP-001 (schema + migration)
   ↓
TIP-002 (auth NextAuth setup)
   ↓
TIP-003 (createTransaction API + form)  ←  TIP-004 (listTransactions)
   ↓                                       ↓
TIP-005 (MonthlyReport screen)
   ↓
TIP-006 (alert vượt ngân sách)
```

Mỗi TIP có spec chi tiết: input/output, edge case, test cần viết.

> 💡 Bạn có thể bắt chước pattern viết TIP từ ví dụ
> `references/examples/01-otb-budget-module/05-tips/` (xem [§6.1](#61-pre-baked-case-study-otb-budget)).

#### Bước 6 — `/vibe-scaffold`: tool sinh code khung

```bash
/vibe-scaffold dashboard
```

Hoặc dùng preset gần nhất: `dashboard` (admin dashboard với KPI cards
+ chart placeholder — phù hợp với app quản lý chi tiêu).

Tool tạo các file:

```
my-budget-app/
├── app/                  # Next.js routes
├── components/           # React components
├── lib/db.ts             # Prisma client
├── prisma/schema.prisma  # 4 bảng đã design
├── public/               # tĩnh
├── tests/                # pytest + playwright
├── package.json
└── README.md
```

Bạn có thể chạy `pnpm install && pnpm dev` để xem khung chạy ngay
(localhost:3000 — chưa có data thật).

#### Bước 7 — `/vibe-verify`: kiểm tra chất lượng

Sau khi tự (hoặc nhờ AI) viết code thật vào khung, gõ:

```
/vibe-verify
```

Tool chạy:
- 96 conformance probe (kiểm tra structure)
- RRI-T gate (functional testing 7 dimensions × 8 stress axes)
- RRI-UX gate (UX testing 7 dimensions × 5 personas)
- Anti-pattern check (12 AP — xem [§6.2](#62-anti-pattern-catalog-12-ap))
- VN checklist (format VND, ngày DD/MM, encoding UTF-8)

Output: `verify-report.md` — coverage matrix, list các REQ đã làm /
chưa làm, các risk còn open.

#### Bước 8 — `/vibe-ship`: deploy

Khi verify xong, gõ:

```
/vibe-ship
```

Tool tạo PR, push lên GitHub, deploy Vercel.  Bạn được URL public.

### 4.4. Tổng thời gian

| Stage | Thời gian thực |
|:------|:---------------|
| 4.1 Mở CLI + paste prompt | 1 phút |
| 4.2 RRI 16 câu | 10 phút |
| 4.3 Vision + Blueprint approve | 5 phút |
| 4.4 Task graph review | 5 phút |
| 4.5 Code (tự / AI assist) | 4-8 giờ tuỳ scope |
| 4.6 Verify + iterate | 2-4 giờ |
| 4.7 Ship | 30 phút |
| **Tổng** | **8-13 giờ → 1-2 ngày làm việc** |

So với cách "tự nghĩ rồi gõ ChatGPT" (~3-5 ngày + nhiều bug do thiếu
spec) thì **nhanh gấp 2-3 lần** và **chất lượng cao hơn rõ rệt** (vì
mọi thứ đều có document + test).

---

## 5. Hiểu output: pipeline 8 bước

Mỗi bước in ra 1 file Markdown.  Không bỏ qua bước nào — bước trước
là input cho bước sau.

| Step | Lệnh | File output | Bạn đọc gì? |
|:-----|:-----|:------------|:-----------|
| 1 | `/vibe-scan` | `scan-report.md` | Stack hiện tại + 5 risk top |
| 2 | `/vibe-rri` | `rri-results.md` | 16 Q&A + 20 REQ-001..REQ-020 |
| 3 | `/vibe-vision` | `vision.md` | Stack proposal + Why + Why-not |
| 4 | `/vibe-blueprint` | `blueprint.md` | Data + API + UI + Invariant + Risk |
| 5 | `/vibe-task graph` | `task-graph.md` | DAG of TIPs |
| 5b | `/vibe-tip` | `05-tips/tip-NNN.md` | Spec mỗi task chi tiết |
| 6 | `/vibe-scaffold` | code thật | Bạn coding hoặc AI assist |
| 6b | (mỗi TIP xong) | `06-completion-reports/tip-NNN.md` | Score + carry-forward |
| 7 | `/vibe-verify` | `verify-report.md` | Coverage matrix + REQ status |
| 8 | `/vibe-ship` | PR link + deploy URL | Sản phẩm sống |

### 5.1. Mẫu xem trước

Để xem output thực tế trông thế nào, đọc thư mục:

```
references/examples/01-otb-budget-module/
├── README.md                        # Tổng quan case study
├── 00-scan-report.md                # Output bước 1
├── 01-rri-requirements.md           # Output bước 2
├── 02-vision.md                     # Output bước 3
├── 03-blueprint.md                  # Output bước 4
├── 04-task-graph.md                 # Output bước 5
├── 05-tips/
│   ├── tip-001-spec.md              # Output bước 5b
│   ├── tip-002-spec.md
│   └── tip-003-spec.md
├── 06-completion-reports/
│   ├── tip-001-report.md            # Output bước 6b
│   ├── tip-002-report.md
│   └── tip-003-report.md
├── 07-rri-t-results.jsonl           # Functional test data
├── 08-rri-ux-results.jsonl          # UX test data
├── 09-coverage-matrix.md            # Module × Dimension scoring
└── 10-verify-report.md              # Output bước 7
```

Đây là 1 dự án **OTB Budget Module** (cho retailer Việt Nam) đã chạy
qua đủ 8 bước.  Bạn có thể bắt chước cấu trúc cho dự án của mình.

---

## 6. Tính năng mới v0.22.0

v0.22.0 (cycle 13 polish) thêm 4 tài liệu reference + 1 bộ ví dụ A-Z
để giúp bạn ra quyết định nhanh hơn ở các giai đoạn vision / blueprint:

### 6.1. Pre-baked case study OTB Budget

📁 `references/examples/01-otb-budget-module/`

**Dùng khi:** Bạn không biết spec dự án nên trông thế nào / lúng túng
ở bước RRI hoặc Blueprint.

**Cách dùng:**

```bash
# Mở từng file lên đọc
cat references/examples/01-otb-budget-module/README.md
cat references/examples/01-otb-budget-module/01-rri-requirements.md
cat references/examples/01-otb-budget-module/03-blueprint.md
```

Hoặc gõ trong AI CLI:

```
Tôi đang làm app quản lý chi tiêu gia đình.  Mở case study
references/examples/01-otb-budget-module/ và bắt chước cấu trúc
RRI + Blueprint cho domain "personal finance" thay vì "retail OTB".
```

AI sẽ học pattern, tự sinh `01-rri-requirements.md` và `03-blueprint.md`
phù hợp với app của bạn.

### 6.2. Anti-pattern catalog 12 AP

📁 `references/anti-patterns-gallery.md`

**Dùng khi:** Lúc design UI, bạn muốn tránh **12 lỗi UX phổ biến nhất**
mà Vietnamese enterprise SaaS hay mắc.

**12 anti-patterns:**

| ID | Tên | Tóm tắt |
|:--:|:----|:--------|
| AP-01 | Modal-on-load | Bật modal ngay lúc trang load |
| AP-02 | Hidden CTA | Nút Submit nằm dưới fold không scroll thấy |
| AP-03 | Reverse-scroll trap | Bắt user cuộn ngược lên |
| AP-04 | Form 50 fields | Form quá dài, không progressive disclosure |
| AP-05 | Dropdown 100 items | Dropdown không có search |
| AP-06 | Empty state trắng | "No data" màn trắng tinh không hướng dẫn |
| AP-07 | Silent failure | Lỗi không hiện thông báo |
| AP-08 | Lost session | Refresh là mất hết data đang nhập |
| AP-09 | Tab state reset | Đổi tab xong filter bị reset |
| AP-10 | Touch target nhỏ | Nút < 44×44 px trên mobile |
| AP-11 | Date format mơ hồ | DD/MM hay MM/DD? |
| AP-12 | VND format sai | "1000000đ" thay vì "1.000.000 ₫" |

Mỗi entry có **BAD** vs **GOOD** ASCII visualization + **Fix recipe**
cụ thể + **Detector JS snippet** để bạn paste vào browser DevTools
console kiểm tra trang.

**Cách dùng nhanh:**

```bash
# Đọc 1 anti-pattern cụ thể
grep -A 30 "AP-04" references/anti-patterns-gallery.md
```

Hoặc gõ trong AI CLI:

```
Áp dụng anti-patterns gallery (references/anti-patterns-gallery.md)
để review my-app/components/SignupForm.tsx — báo các AP-xx vi phạm
và fix recipe cho từng cái.
```

AI sẽ check form đó với 12 AP và báo lỗi (nếu có).  Hoặc gõ CLI:

```bash
vibecodekit anti-patterns list      # liệt kê 12 AP
vibecodekit anti-patterns check ...  # evaluate với JSON checklist
```

### 6.3. Color psychology — pick palette by industry

📁 `references/37-color-psychology.md`

**Dùng khi:** Lúc design, bạn cần chọn màu chính cho app nhưng không
biết nên dùng xanh hay đỏ.

**7 industry palettes** đã chốt sẵn:

| Industry | Primary | Use case |
|:---------|:-------:|:---------|
| Finance/Retail | `#1E3A8A` (xanh navy) | Ngân hàng, retail OTB |
| Healthcare | `#059669` (xanh lá) | Phòng khám, app sức khoẻ |
| E-commerce | `#DC2626` (đỏ) | Shop online, flash sale |
| Education | `#7C3AED` (tím) | Edtech, online course |
| SaaS B2B | `#0F172A` (đen navy) | Dashboard nội bộ |
| Government | `#064E3B` (xanh rừng) | Cổng dịch vụ công |
| Logistics | `#EA580C` (cam) | Giao hàng, vận tải |

Cộng với:
- **WCAG contrast guidelines** (đảm bảo người khiếm thị đọc được)
- **Vietnamese cultural color associations** (Đỏ = chúc mừng/Tết, Vàng =
  vượng, Trắng = tang — tránh dùng sai context)
- **Color-blind safety** (8% nam giới bị mù màu — design đừng chỉ dựa
  vào màu)
- **Dark mode mapping** (nếu app có dark mode, đây là cách map)

**Cho app quản lý chi tiêu gia đình:** dùng palette **Finance** (xanh
navy) — vừa đáng tin cậy vừa khiến user bình tĩnh khi đối mặt với số.

### 6.4. Font pairing — pick font by use case

📁 `references/38-font-pairing.md`

**Dùng khi:** Lúc design, không biết nên dùng font Roboto hay Inter
hay Be Vietnam Pro.

**5 font pair** đã chốt:

| Use case | Heading | Body | Phù hợp |
|:---------|:--------|:-----|:--------|
| Modern SaaS | Plus Jakarta Sans | Inter | Dashboard B2B |
| Corporate | Be Vietnam Pro | Inter | Tài chính, government |
| Editorial | Playfair Display | Source Sans 3 | Blog, content |
| Tech-forward | Space Grotesk | DM Sans | AI tools, dev tools |
| Friendly consumer | Manrope | Inter | E-commerce, edu |

Tất cả 5 pair đều **support Vietnamese subset đầy đủ** (đã smoke-test
với câu mẫu: *"Ứng dụng quản lý ngân sách OTB cho buyer phụ trách
quần áo nữ"*).

Cộng với:
- **Type scale ladder** (Display 48-72px → Label 12-13px) — chuẩn cho
  desktop và mobile
- **Loading strategy** (`next/font/google` với `display: swap`,
  preload subset)
- **Fallback stack** (nếu font không tải được)
- **5 anti-patterns AP-VNF-01..05** (lỗi font hay gặp với tiếng Việt)

**Cho app quản lý chi tiêu gia đình:** dùng pair **Friendly consumer**
(Manrope + Inter) — dễ đọc, mềm mại, phù hợp với gia đình.

---

## 7. 10 lệnh hay dùng nhất

Bạn không cần nhớ hết 42 slash command.  10 lệnh sau đủ cho 95% use case:

| Lệnh | Khi nào dùng |
|:-----|:-------------|
| `/vibe <prose>` | Mọi lúc — master router tự dispatch sang đúng command |
| `/vibe-scan` | Khi bắt đầu dự án mới hoặc onboard repo cũ |
| `/vibe-rri` | Khi cần chốt requirements với 16 Q&A |
| `/vibe-blueprint` | Khi cần thiết kế kiến trúc (sau RRI) |
| `/vibe-scaffold <preset>` | Khi cần code khung chạy được nhanh |
| `/vibe-tip <id>` | Khi cần spec chi tiết 1 task |
| `/vibe-verify` | Khi build xong, cần kiểm tra chất lượng |
| `/vibe-ship` | Khi sẵn sàng deploy |
| `/vibe-doctor` | Khi nghi ngờ cài sai (sanity check) |
| `/vibe-audit` | Khi muốn xem 92 probe self-test (rare) |

### 7.1. Verb shortcut (siêu ngắn)

Nếu lười gõ tên dài, dùng 8 verb chuẩn:

```bash
/vibe scan      # = /vibe-scan
/vibe plan      # = /vibe-blueprint
/vibe build     # = /vibe-scaffold
/vibe review    # = /vck-review (adversarial 7-specialist)
/vibe qa        # = /vck-qa (real-browser checklist)
/vibe ship      # = /vck-ship (test → review → commit → push → PR)
/vibe audit     # = /vibe-audit
/vibe doctor    # = /vibe-doctor
```

### 7.2. Pipeline shortcut

Để chạy 1 lèo từ scan → ship cho project mới:

```bash
/vibe pipeline launch shop online bán cà phê
```

Tool sẽ tự gọi sequence: `scan → vision → rri → scaffold → verify → ship`.

> ⚠️ Pipeline tự động bỏ qua bước nếu output đã có (idempotent).
> Bạn có thể `Ctrl+C` giữa chừng và resume sau.

---

## 8. FAQ + xử lý lỗi

### Q1 — `vibecodekit demo` báo `command not found`

```bash
# Thử dùng module path:
PYTHONPATH=./scripts python3 -m vibecodekit.cli demo

# Nếu vẫn không được, kiểm tra Python version:
python3 --version  # phải ≥ 3.9

# Cài lại:
pip3 install -e . --force-reinstall
```

### Q2 — `pip3` báo "externally-managed-environment"

(Xảy ra trên Ubuntu 23+, macOS với Homebrew Python.)  Tạo virtual env:

```bash
python3 -m venv .venv
source .venv/bin/activate         # macOS/Linux
# hoặc
.\.venv\Scripts\Activate.ps1      # Windows PowerShell

pip install -e .
```

### Q3 — Tool không hiểu mô tả tiếng Việt của tôi

Có 2 nguyên nhân thường gặp:

1. **Mô tả quá ngắn** ("làm app shop") → tool route confidence thấp →
   nó hỏi 1 câu clarification.  Trả lời rõ hơn.
2. **Tool không chạy intent classifier** → bạn đang dùng AI CLI khác
   (không phải Claude Code / Codex / Cursor có support).  Workaround:
   gõ thẳng command cụ thể (`/vibe-scan` thay vì `/vibe`).

### Q4 — Code AI sinh ra bị lỗi

Đó là chuyện thường — AI không phải lúc nào cũng đúng 100%.  Cách
khắc phục:

```bash
# Chạy verify để xem lỗi cụ thể
/vibe-verify

# Đọc verify-report.md, ghi lại REQ-XXX còn fail
# Quay lại AI CLI, paste:
"Verify báo REQ-005 fail vì <lý do trong report>.  Sửa code ở
file <path> để pass."
```

### Q5 — Làm sao biết tool có version mới hơn?

```bash
# Kiểm tra version đang cài
vibecodekit --version    # hoặc: python3 -c "from vibecodekit import __version__; print(__version__)"

# Cập nhật
cd ~/Desktop/vibecodekit-hybrid-ultra
git pull origin main
pip install -e . --upgrade
```

Hoặc theo dõi releases:
https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra/releases

### Q6 — Tôi không muốn dùng git, có cách nào?

Có.  Tải zip từ
https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra/archive/refs/heads/main.zip
→ giải nén → mở Terminal vào thư mục → `pip3 install -e .`.

### Q7 — Tool có gửi data của tôi đi đâu không?

**Không.**  VibecodeKit là **stdlib-only** (chỉ dùng thư viện Python
core, không có network call).  Bạn có thể tự verify:

```bash
grep -r "import requests\|import urllib\|import http" scripts/vibecodekit/
# → 0 kết quả ngoài hook trong tools/* (không phải runtime)
```

LLM call (gửi text tới Claude/ChatGPT) chỉ xảy ra ở phía AI CLI bạn
dùng — không phải tool này.

### Q8 — Tôi build app cho khách hàng Việt Nam, cần check gì cuối?

Chạy `vibecodekit vn-check` — tool kiểm tra:
- Format VND (`1.234.567 ₫` chuẩn, không phải `1234567 đồng`)
- Format ngày (`DD/MM/YYYY` không phải MM/DD)
- Encoding tiếng Việt (UTF-8 không bị lỗi à á ạ)
- CCCD/CMND validation (12 chữ số / 9 chữ số)
- Số điện thoại VN (+84 hoặc 0)
- Timezone Asia/Ho_Chi_Minh

```bash
# Tạo file flags.json với các kiểm tra bạn đã pass:
echo '{"vnd_format": true, "date_dmy": true, "utf8_encoding": true,
       "cccd_validation": true, "phone_vn": true,
       "timezone_hcm": true}' > flags.json

vibecodekit vn-check --file flags.json
```

(Hoặc gõ trong AI CLI: `Apply VN checklist for my project per
methodology.VN_CHECKLIST_ITEMS — generate flags.json based on actual
state of repo`.)

### Q9 — Tôi không phải dev, làm sao deploy?

Dùng **Vercel** — drag & drop:
1. Mở https://vercel.com (đăng ký bằng GitHub)
2. Click "Add New" → "Project"
3. Import repo của bạn
4. Click "Deploy" — Vercel tự build, cho URL public sau 2 phút.

Free tier: 100 GB bandwidth/tháng, đủ cho app gia đình ~1000 user.

### Q10 — Tool có hỗ trợ nhiều ngôn ngữ ngoài tiếng Việt + Anh?

v0.22.0 chỉ optimized cho **VN + EN**.  Tiếng khác (Indo, Thai, …)
dùng được nhưng cultural color/font hint không apply.  Roadmap v0.23+
sẽ mở rộng SEA locales.

---

## 9. Bước tiếp theo

Sau khi quen với 8-step pipeline:

### 9.1. Đọc thêm

- 📘 `USAGE_GUIDE.md` — 17 section đầy đủ, ~2700 dòng (cho power user)
- 📘 `references/29-rri-reverse-interview.md` — Method luận cốt lõi
  của RRI (16 câu Q&A)
- 📘 `references/30-vibecode-master.md` — Triết lý 3 vai (Chủ nhà /
  Chủ thầu / Thợ) × 8 bước
- 📘 `references/anti-patterns-gallery.md` — 12 AP với BAD/GOOD viz
- 📘 `references/37-color-psychology.md` — 7 industry palette
- 📘 `references/38-font-pairing.md` — 5 use-case font pair
- 📘 `RELEASE_NOTES_v0.22.0.md` — Highlight cycle 13

### 9.2. Tham khảo case study đầu tiên

Đọc `references/examples/01-otb-budget-module/` — case study đầy đủ
A→Z cho 1 module retail enterprise.  Bắt chước pattern này cho dự án
của bạn.

### 9.3. Cộng đồng

- GitHub Issues: https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra/issues
- GitHub Discussions: (đang setup)
- Telegram (đang setup)

### 9.4. Đóng góp

Nếu bạn:
- Tìm thấy lỗi → mở Issue
- Có ý tưởng feature → mở Discussion
- Muốn sửa typo / doc → fork + Pull Request
- Có case study muốn share → tạo `references/examples/02-<your-domain>/`

Tất cả đóng góp đều welcome.

---

## Bonus: Cheatsheet 1 trang

In ra dán bàn làm việc:

```
┌──────────────────────────────────────────────────────────────┐
│  VibecodeKit Hybrid Ultra v0.25.0 — 1-page cheatsheet        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CÀI:    pip3 install -e .                                   │
│  TEST:   vibecodekit demo                                    │
│  HELP:   /vibe                  (master router)              │
│                                                              │
│  PIPELINE 8 BƯỚC (mọi project):                              │
│                                                              │
│  1. /vibe-scan        →  scan-report.md                      │
│  2. /vibe-rri         →  rri-results.md (16 Q&A)             │
│  3. /vibe-vision      →  vision.md                           │
│  4. /vibe-blueprint   →  blueprint.md                        │
│  5. /vibe-task graph  →  task-graph.md                       │
│  6. /vibe-scaffold    →  code khung                          │
│  7. /vibe-verify      →  verify-report.md                    │
│  8. /vibe-ship        →  PR + deploy URL                     │
│                                                              │
│  HOẶC 1 LÈO:                                                 │
│      /vibe pipeline launch <mô tả>                           │
│                                                              │
│  REFERENCE NHANH:                                            │
│   • Anti-pattern  →  references/anti-patterns-gallery.md     │
│   • Color palette →  references/37-color-psychology.md       │
│   • Font pair     →  references/38-font-pairing.md           │
│   • Case study    →  references/examples/01-otb-budget-…     │
│                                                              │
│  HỖ TRỢ VN:                                                  │
│   • vibecodekit vn-check →  VND, DD/MM, UTF-8, CCCD          │
│   • Tất cả font pair   →  Vietnamese subset đầy đủ           │
│   • Tất cả 16 RRI Q    →  song ngữ VN/EN                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

**Phản hồi & câu hỏi:** Mở issue tại
https://github.com/VibecodekitPJ7/vibecodekit-hybrid-ultra/issues

**Phiên bản tài liệu:** v0.25.0 (2026-05-03) — Cycle 15 — Cycle 14/13 polish features vẫn áp dụng
