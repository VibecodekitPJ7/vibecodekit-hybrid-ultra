# Anti-Patterns Gallery — 12 critical UX failures cho Vietnamese Enterprise SaaS

> Single source of truth: `methodology.anti_patterns_canonical()`.
> Mọi AP-XX dưới đây map 1:1 với entry trong API; thêm vào đây
> visualization BAD/GOOD + fix recipe + auto-detector mà API không
> ship được.
>
> Cách dùng:
> 1. Lúc design review — paste link `#ap-XX` vào comment.
> 2. Lúc code review — copy snippet "Detector" vào CI lint.
> 3. Lúc onboard team — đọc liền 12 AP để khỏi rơi vào bẫy quen thuộc.
>
> Cross-link:
> - [`references/32-rri-ux-critique.md`](32-rri-ux-critique.md) §11 (12-axis trace)
> - [`references/33-rri-ui-design.md`](33-rri-ui-design.md) §3 (component design rules)
> - [`references/29-rri-reverse-interview.md`](29-rri-reverse-interview.md) §4 (UX hostile testing)
> - `methodology.evaluate_anti_patterns_checklist(items)` — runtime check

---

## AP-01 — Modal-on-load

- **Issue**: Popup chặn ngay khi vào trang chủ (newsletter, cookie banner, "Xác nhận tuổi", upsell). Người dùng chưa kịp đọc gì đã phải đóng modal.
- **Persona impact**: 🏃 Speed Runner — interrupt flow; 👁 First-Timer — cảm giác bị spam; 📱 Mobile — modal full-screen nuốt dismiss button.
- **Dimension**: U1 Flow direction · U4 Feedback (negative attention).
- **Detection hint** (canonical): hero section bị overlay che ≥ 1.5 s sau load.

```
BAD:                                   GOOD:
┌───────────────────────────────┐      ┌───────────────────────────────┐
│ ╔═══════════════════════════╗ │      │ Trang chủ — content visible  │
│ ║  🎉 Đăng ký nhận tin?     ║ │      │ [hero] [feature] [pricing]   │
│ ║  Email: [_____________]   ║ │      │                              │
│ ║  [Đăng ký] [✕]            ║ │      │ ┌─ tooltip nhỏ ─────────────┐│
│ ╚═══════════════════════════╝ │      │ │ Đăng ký bản tin? [✕]    │ │
│ (hero section bị che)         │      │ └──────────────────────────┘ │
└───────────────────────────────┘      └───────────────────────────────┘
```

**Fix recipe**:
- Trì hoãn modal ≥ 30 s OR đợi user đã scroll ≥ 50 % page.
- Dùng inline banner / slide-in tray thay vì overlay full-screen.
- Save dismiss state vào `localStorage`; không show lại trong 30 ngày.

**Detector** (CI hint, ship trong `eslint-plugin-vibecode-ux/no-modal-on-load.js`):
```js
// Fail nếu phát hiện modal active < 1.5 s sau DOMContentLoaded
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.entryType === 'layout-shift' && entry.value > 0.1
        && performance.now() < 1500) {
      console.warn('AP-01 violation: modal-on-load detected');
    }
  }
});
observer.observe({ entryTypes: ['layout-shift'] });
```

---

## AP-02 — Hidden CTA

- **Issue**: Primary action không xuất hiện trong viewport đầu tiên — user phải scroll hoặc đoán.
- **Persona impact**: 🏃 Speed Runner — mất ≥ 3 s tìm CTA; 👵 Power User — học muscle memory không đúng vị trí.
- **Dimension**: U1 Flow direction · U2 Click depth.
- **Detection hint** (canonical): CTA dưới fold trên viewport 1366×768 / 390×844.

```
BAD: viewport 1366×768                  GOOD: sticky CTA
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ Header                       │       │ Header                       │
│ Hero text rất dài...         │       │ Hero text                    │
│ ...                          │       │ [Đặt mua ngay →] ← above fold│
│ ...                          │       │ ...                          │
├─ FOLD ──────────────────────┤        ├─ FOLD ──────────────────────┤
│ ...                          │       │ Detail content...            │
│ [Đặt mua ngay →]  ← khuất    │       │   ┌────────────────────────┐ │
│ Footer                       │       │   │ [Đặt mua ngay →] sticky│ │
└──────────────────────────────┘       │   └────────────────────────┘ │
                                       └──────────────────────────────┘
```

**Fix recipe**:
- Đặt CTA chính trong 600 px đầu của viewport.
- Bổ sung sticky CTA ở mobile (chiếm bottom bar 56 px).
- Dùng heatmap (Hotjar) để verify ≥ 80 % click rơi vào above-fold CTA.

**Detector**:
```js
function findCtaAboveFold() {
  const ctas = document.querySelectorAll('[data-cta="primary"]');
  return [...ctas].some((el) => el.getBoundingClientRect().top < window.innerHeight);
}
if (!findCtaAboveFold()) console.warn('AP-02 violation: primary CTA below fold');
```

---

## AP-03 — Reverse-scroll trap

- **Issue**: Bước tiếp theo nằm phía TRÊN bước hiện tại — user phải scroll ngược, dễ tưởng app bị bug.
- **Persona impact**: 👁 First-Timer — lost confidence; ♿ Screen reader — flow rời rạc; 📱 Mobile — gesture conflict.
- **Dimension**: U1 Flow direction · U5 Return path.
- **Detection hint** (canonical): next-step ở `top < current.top`.

```
BAD: form đăng ký                       GOOD: linear top-down
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ Bước 2: Xác nhận             │       │ Bước 1: Thông tin (current)  │
│ [_____________________]      │       │ [_____________________]      │
│                              │       │ [_____________________]      │
│ Bước 1: Thông tin            │  ←┐   │                              │
│ [_____________________]      │   │   │ Bước 2: Xác nhận             │
│                              │   │   │ [_____________________]      │
│ [↑ Scroll lên bước 1]        │ ──┘   │ [Tiếp →]                     │
└──────────────────────────────┘       └──────────────────────────────┘
```

**Fix recipe**:
- Mọi step trong flow phải có `position.top` tăng dần theo step number.
- Auto-scroll-to-top khi step transition.
- Step indicator (1 / 4) cố định ở top — luôn visible.

**Detector**:
```js
const steps = document.querySelectorAll('[data-step]');
for (let i = 1; i < steps.length; i++) {
  const prev = steps[i-1].getBoundingClientRect().top;
  const curr = steps[i].getBoundingClientRect().top;
  if (curr < prev) console.warn(`AP-03 violation: step ${i+1} above step ${i}`);
}
```

---

## AP-04 — Form > 7 fields, no progressive disclosure

- **Issue**: 50-field form trên 1 trang gây cognitive overload, tỷ lệ abandon > 60 %.
- **Persona impact**: 🏃 Speed Runner — mệt mỏi; 👁 First-Timer — không biết bắt đầu từ đâu; 📱 Mobile — scroll vô tận.
- **Dimension**: U3 Cognitive load · U4 Progressive disclosure.
- **Detection hint** (canonical): `<form>` có > 7 input visible đồng thời.

```
BAD:                                    GOOD: wizard 4-step
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ Họ tên   [______________]    │       │ Bước 1/4: Cá nhân            │
│ Email    [______________]    │       │ Họ tên  [____________]       │
│ Phone    [______________]    │       │ Email   [____________]       │
│ Address  [______________]    │       │ Phone   [____________]       │
│ City     [______________]    │       │                              │
│ Job      [______________]    │       │   ━━━━○━━━━━━━━━━━━━━━━     │
│ Gender   [______________]    │       │   1    2    3    4           │
│ DOB      [______________]    │       │                              │
│ ... 42 trường nữa ...        │       │            [Tiếp →]          │
└──────────────────────────────┘       └──────────────────────────────┘
```

**Fix recipe**:
- Wizard ≤ 5 step, mỗi step ≤ 7 input.
- Dùng accordion / tab cho các nhóm field tùy chọn.
- Save draft tự động (`autosave: 5s` debounce) → resume sau.

**Detector**:
```js
document.querySelectorAll('form').forEach((form) => {
  const inputs = form.querySelectorAll('input:not([type=hidden]), select, textarea');
  if (inputs.length > 7 && !form.querySelector('[role=tablist], [data-wizard-step]')) {
    console.warn(`AP-04 violation: form has ${inputs.length} fields, no progressive disclosure`);
  }
});
```

---

## AP-05 — Dropdown > 15 items, no search

- **Issue**: Combobox / select 50 + tỉnh / 200 + bank / 500 + sản phẩm mà không có ô search → user phải scroll mệt.
- **Persona impact**: 🏃 Speed Runner — slow; ♿ Screen reader — phải `arrow-down × N`; 📱 Mobile — list dài hơn viewport.
- **Dimension**: U2 Click depth · U3 Cognitive load.
- **Detection hint** (canonical): `<select>` / combobox > 15 option mà không có filter input.

```
BAD:                                   GOOD: combobox + search
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Tỉnh: [Hà Nội            ▼]  │      │ Tỉnh: [Hà Nội           ▼ ]  │
│   ├─ An Giang                │      │   🔍 [_____________ ]       │
│   ├─ Bà Rịa-Vũng Tàu         │      │   ↓ filter: "ha"             │
│   ├─ Bạc Liêu                │      │   ┌─────────────────────┐   │
│   ├─ Bắc Giang               │      │   │ Hà Giang            │   │
│   ├─ ... 59 tỉnh nữa ...     │      │   │ Hà Nam              │   │
│   └─ (scroll mệt)            │      │   │ Hà Nội              │   │
└──────────────────────────────┘      │   │ Hà Tĩnh             │   │
                                       │   └─────────────────────┘   │
                                       └──────────────────────────────┘
```

**Fix recipe**:
- Dùng combobox (Headless UI / cmdk) với input filter.
- Áp `aria-autocomplete="list"` để screen reader announce.
- Cache last-used trong `localStorage` để show top suggestion.

**Detector**:
```js
document.querySelectorAll('select').forEach((sel) => {
  if (sel.options.length > 15) {
    console.warn(`AP-05 violation: <select> has ${sel.options.length} options without filter`);
  }
});
```

---

## AP-06 — Empty state without guidance

- **Issue**: List rỗng / dashboard không data hiển thị "No data" trắng tinh, không CTA, không hướng dẫn → user nghĩ app bị lỗi.
- **Persona impact**: 👁 First-Timer — confused; 🏃 Speed Runner — mất thời gian guess.
- **Dimension**: U4 Progressive disclosure · U6 Feedback.
- **Detection hint** (canonical): empty container không có button / link / illustration explainer.

```
BAD:                                   GOOD:
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Đơn đặt hàng                 │      │ Đơn đặt hàng                 │
│                              │      │   ┌────────────────────────┐ │
│                              │      │   │ 📦 Chưa có đơn nào     │ │
│   No data                    │      │   │ Tạo đơn đầu tiên để    │ │
│                              │      │   │ bắt đầu theo dõi tồn   │ │
│                              │      │   │ kho và doanh thu.      │ │
│                              │      │   │ [+ Tạo đơn mới]        │ │
│                              │      │   └────────────────────────┘ │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Mỗi empty state phải có: icon / illustration + 1-2 dòng giải thích + 1 CTA hành động.
- Phân biệt 3 kiểu empty: "first-time" (CTA tạo mới), "filtered-empty" (CTA clear filter), "permission-empty" (link request access).

**Detector**:
```js
document.querySelectorAll('[data-empty-state]').forEach((node) => {
  const hasCta = node.querySelector('a, button');
  const hasIllust = node.querySelector('svg, img');
  if (!hasCta || !hasIllust) {
    console.warn('AP-06 violation: empty state missing CTA or illustration');
  }
});
```

---

## AP-07 — Silent failure

- **Issue**: Hành động fail (4xx / 5xx) nhưng UI không hiển thị bất cứ feedback nào — user không biết lỗi gì, làm lại bao nhiêu lần.
- **Persona impact**: 🏃 Speed Runner — retry vô nghĩa; 👵 Power User — mất trust; ♿ Screen reader — không có announce.
- **Dimension**: U6 Feedback · U7 VN text (error message Vietnamese).
- **Detection hint** (canonical): 4xx / 5xx không update `[role=alert]` / toast.

```
BAD:                                   GOOD: actionable error
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ [Đăng nhập]                  │      │ [Đăng nhập]                  │
│                              │      │   ⚠ Sai mật khẩu (sai 2/5).  │
│ (click → 401 → nothing)      │      │   Còn 3 lần thử trước khi    │
│                              │      │   khoá tài khoản 30 phút.    │
│                              │      │   [Quên mật khẩu?]           │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Mọi 4xx / 5xx phải push 1 entry vào `[role=alert]` (a11y live region).
- Error message Vietnamese tự nhiên + actionable next step.
- Distinguish: validation error (inline) vs network error (toast) vs auth error (redirect login).
- Log Sentry breadcrumb với request_id để CSKH tra cứu.

**Detector**:
```js
window.addEventListener('unhandledrejection', (event) => {
  const alert = document.querySelector('[role=alert]');
  if (!alert || !alert.textContent.trim()) {
    console.warn('AP-07 violation: silent failure — no [role=alert] update');
  }
});
```

---

## AP-08 — Lost session on accidental refresh

- **Issue**: User điền form 30 phút, lỡ F5 / back → mất sạch. Đặc biệt brutal cho mobile khi accidental swipe-back.
- **Persona impact**: 📱 Mobile — gesture conflict; 🏃 Speed Runner — mất thời gian; 👵 Power User — sợ refresh.
- **Dimension**: U5 Return path · U6 Feedback.
- **Detection hint** (canonical): không có `localStorage` / `sessionStorage` autosave.

```
BAD:                                   GOOD:
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Form 30 phút...              │      │ Form 30 phút                 │
│ [50 fields filled]           │      │ [50 fields filled]           │
│                              │      │ ✓ Đã lưu nháp lúc 14:32     │
│ (F5 lỡ tay)                  │      │                              │
│ ↓                            │      │ (F5 lỡ tay)                  │
│ Form trống tinh              │      │ ↓                            │
│ "Bạn chưa nhập gì"           │      │ ┌─────────────────────────┐  │
│                              │      │ │ Tìm thấy bản nháp 14:32 │  │
│                              │      │ │ [Tiếp tục] [Bỏ]         │  │
│                              │      │ └─────────────────────────┘  │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- `autosave: 5s` debounce, key = `draft:<form-id>:<user-id>` trong `localStorage`.
- Banner "Đã lưu nháp lúc HH:MM" — quan trọng để user trust mà không lo.
- TTL nháp: 7 ngày, sau đó tự xoá.
- Confirm dialog `beforeunload` chỉ khi có dirty chưa save.

**Detector**:
```js
const form = document.querySelector('form[data-long-form]');
const hasAutosave = form?.dataset.autosaveKey
  || window.addEventListener.toString().includes('beforeunload');
if (form && !hasAutosave) console.warn('AP-08 violation: long form without autosave');
```

---

## AP-09 — Tab/filter state reset on navigation

- **Issue**: User filter table, click row → detail page → click back → filter biến mất, phải lọc lại từ đầu.
- **Persona impact**: 👵 Power User — workflow đứt; 🏃 Speed Runner — lặp việc.
- **Dimension**: U5 Return path · U2 Click depth.
- **Detection hint** (canonical): URL không phản ánh filter; chỉ in-memory state.

```
BAD:                                   GOOD: URL state
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ /orders                      │      │ /orders?status=pending&q=ABC │
│ Filter: [pending] [ABC]      │      │ Filter: [pending] [ABC]      │
│ ▶ Click row 1                │      │ ▶ Click row 1                │
│   ↓                          │      │   ↓                          │
│ /orders/1                    │      │ /orders/1                    │
│   ↓ back                     │      │   ↓ back                     │
│ /orders (filter trống!)      │      │ /orders?status=pending&q=ABC │
│ user phải filter lại         │      │ filter restored              │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Sync filter / sort / pagination vào URL query string (Next.js router, React Router useSearchParams).
- Server-side render dùng URL state để hiển thị đúng ngay first paint.
- Save "last view" vào `localStorage` để landing page mở đúng tab last visited.

**Detector**:
```js
const filterChange = new MutationObserver(() => {
  if (location.search === '' && document.querySelector('[data-filter-active]')) {
    console.warn('AP-09 violation: filter active but URL has no query string');
  }
});
filterChange.observe(document.body, { subtree: true, attributes: true });
```

---

## AP-10 — Touch target < 44 × 44 px

- **Issue**: Nút mobile chỉ 24 × 24 px (icon-only) → bấm nhầm liên tục, đặc biệt với người lớn tuổi / tay run.
- **Persona impact**: 📱 Mobile — chính; ♿ Motor impairment — không bấm trúng.
- **Dimension**: U1 Flow direction · U6 Feedback.
- **Detection hint** (canonical): click target < 44 px ở viewport ≤ 480 px (Apple HIG).

```
BAD:                                   GOOD:
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Đơn 001  [✏][🗑][📋]         │      │ Đơn 001                      │
│         (3 icon 16×16 px,    │      │   [Sửa     ] [Xoá] [Sao chép]│
│         click area dính nhau)│      │   (mỗi nút ≥ 44×44 px,      │
│                              │      │    spacing 8 px)             │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Tối thiểu 44 × 44 px (Apple HIG) hoặc 48 × 48 dp (Material Design).
- Spacing giữa 2 button ≥ 8 px.
- Nếu icon-only nhỏ, bọc trong `<button>` padding 12 px để tăng hit area.

**Detector**:
```js
if (window.innerWidth <= 480) {
  document.querySelectorAll('button, a').forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width < 44 || rect.height < 44) {
      console.warn(`AP-10 violation: touch target ${rect.width}×${rect.height} < 44px`, el);
    }
  });
}
```

---

## AP-11 — Date format ambiguity

- **Issue**: Không clarify `01/02/2026` là 1-Feb hay 2-Jan → user nhập sai sinh ngày, thanh toán sai chu kỳ.
- **Persona impact**: 👁 First-Timer — confused; 🌐 Localization — ambiguous DD/MM vs MM/DD; 👵 Power User — bug subtle.
- **Dimension**: U7 VN text · U4 Progressive disclosure.
- **Detection hint** (canonical): date input không có placeholder / `aria-describedby` format.

```
BAD:                                   GOOD: explicit format
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Ngày sinh: [01/02/2026]      │      │ Ngày sinh: [01/02/2026]      │
│            ↑                 │      │   📅 Định dạng: DD/MM/YYYY   │
│ 1-Feb hay 2-Jan???           │      │   (1 tháng 2 năm 2026)       │
│                              │      │                              │
│ [Submit]                     │      │ [Hôm nay 15/04/2026]         │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Explicit placeholder `DD/MM/YYYY` (Vietnam standard).
- `aria-describedby` chỉ định format cho screen reader.
- Date picker UI — không bắt user gõ tay.
- Server-side luôn store ISO 8601 (`2026-02-01`) — chỉ render DD/MM/YYYY ở UI.

**Detector**:
```js
document.querySelectorAll('input[type=date], input[type=text][data-date]').forEach((inp) => {
  if (!inp.placeholder || !inp.placeholder.match(/D{1,2}\/M{1,2}\/Y{2,4}/i)) {
    console.warn('AP-11 violation: date input without DD/MM/YYYY hint');
  }
});
```

---

## AP-12 — VND format errors

- **Issue**: Số tiền hiển thị `1234567` thay vì `1.234.567 ₫` — user khó đọc, dễ tưởng `12,345.67` (USD).
- **Persona impact**: 🏃 Speed Runner — chậm parse; 👵 Power User — mất trust hệ thống tài chính; 🌐 Localization.
- **Dimension**: U7 VN text · U6 Feedback.
- **Detection hint** (canonical): không dùng `Intl.NumberFormat('vi-VN', currency: 'VND')`.

```
BAD:                                   GOOD:
┌──────────────────────────────┐      ┌──────────────────────────────┐
│ Tổng: 1234567                │      │ Tổng: 1.234.567 ₫            │
│ Phí : 50000                  │      │ Phí : 50.000 ₫               │
│ Cuối: 1284567                │      │ Cuối: 1.284.567 ₫            │
│                              │      │                              │
│ (số trông như USD; thiếu ₫;  │      │ (đúng chuẩn VN: dot-thousands │
│  không thousands separator)  │      │  + ký hiệu ₫ phía sau)       │
└──────────────────────────────┘      └──────────────────────────────┘
```

**Fix recipe**:
- Dùng `Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' })`.
- KHÔNG self-roll regex thay thế dấu chấm — Intl handle edge cases.
- Storage: lưu integer VND (không float để tránh rounding error).
- Input mask: `1.234.567` khi nhập, gửi `1234567` lên backend.

**Detector**:
```js
document.querySelectorAll('[data-currency=VND]').forEach((el) => {
  const txt = el.textContent.trim();
  // Pattern: [+-]?[1-9]\d{0,2}(\.\d{3})*\s*₫?
  if (!/^[+\-]?\d{1,3}(\.\d{3})*\s*₫$/.test(txt) && !/^0\s*₫$/.test(txt)) {
    console.warn(`AP-12 violation: VND format wrong: ${txt!r}`);
  }
});
```

---

## Quick reference — 12 AP × Dimension matrix

| AP-XX | Name                                      | U1 | U2 | U3 | U4 | U5 | U6 | U7 |
|:-----:|:------------------------------------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| AP-01 | Modal-on-load                              | ●  |    |    | ●  |    |    |    |
| AP-02 | Hidden CTA                                 | ●  | ●  |    |    |    |    |    |
| AP-03 | Reverse-scroll trap                        | ●  |    |    |    | ●  |    |    |
| AP-04 | Form > 7 fields, no progressive disclosure |    |    | ●  | ●  |    |    |    |
| AP-05 | Dropdown > 15 items, no search             |    | ●  | ●  |    |    |    |    |
| AP-06 | Empty state without guidance               |    |    |    | ●  |    | ●  |    |
| AP-07 | Silent failure                             |    |    |    |    |    | ●  | ●  |
| AP-08 | Lost session on refresh                    |    |    |    |    | ●  | ●  |    |
| AP-09 | Tab/filter reset on navigation             |    | ●  |    |    | ●  |    |    |
| AP-10 | Touch target < 44 px                       | ●  |    |    |    |    | ●  |    |
| AP-11 | Date format ambiguity                      |    |    |    | ●  |    |    | ●  |
| AP-12 | VND format errors                          |    |    |    |    |    | ●  | ●  |

## Maintenance contract

- Tên 12 AP-XX KHÔNG được đổi — đã wire vào `methodology.anti_patterns_canonical()` và conformance probe #89.
- Khi thêm AP mới (AP-13+), update **đồng thời** 4 nơi:
  1. `methodology.py::anti_patterns_canonical()` (source of truth)
  2. File này (visualization + fix recipe)
  3. `references/32-rri-ux-critique.md` (12-axis trace)
  4. Conformance probe count (`tests/test_anti_patterns_gallery.py`)

## See also

- [`32-rri-ux-critique.md`](32-rri-ux-critique.md) — RRI-UX 7-dim critique methodology
- [`30-vibecode-master.md`](30-vibecode-master.md) — vibecode master workflow & UX guide
- [`33-rri-ui-design.md`](33-rri-ui-design.md) — component design rules / UI checklist
- `methodology.evaluate_anti_patterns_checklist(items)` — runtime auto-check
