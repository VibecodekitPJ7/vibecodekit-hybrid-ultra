# 37 — Color psychology by industry (Vietnamese Enterprise SaaS)

> Mở rộng `references/34-style-tokens.md` §2 (CP-01..CP-06 generic) thành
> **7 industry-tuned palettes** áp dụng trực tiếp cho Vietnamese B2B /
> retail / government / healthcare context.  Mỗi palette ship đầy đủ:
> primary / secondary / accent HEX, WCAG contrast pair, Vietnamese
> cultural note, color-blind safety mapping, dark-mode mapping.
>
> Cross-link:
> - [`34-style-tokens.md`](34-style-tokens.md) §2 — generic CP-01..CP-06 tokens.
> - [`38-font-pairing.md`](38-font-pairing.md) — pair palette + font cho stack hoàn chỉnh.
> - `methodology.COLOR_PSYCHOLOGY` — runtime catalog (giữ nguyên 6-entry generic).
>
> File này KHÔNG override `methodology.COLOR_PSYCHOLOGY` — nó là layer
> consume-side (industry → CP mapping) cho `/vibe-vision`.

---

## 1. 7 base palettes by industry

| Industry          | Primary             | Secondary             | Accent              | Rationale                                              |
|:------------------|:--------------------|:----------------------|:--------------------|:-------------------------------------------------------|
| Finance / Retail  | `#1E3A8A` blue-800  | `#F1F5F9` slate-100   | `#DC2626` red-600   | Trust + urgency cho alert / over-budget               |
| Healthcare        | `#059669` emerald-600 | `#ECFDF5` emerald-50 | `#2563EB` blue-600  | Calm + trustworthy + info                             |
| E-commerce        | `#DC2626` red-600   | `#FFF1F2` rose-50     | `#F59E0B` amber-500 | Urgency + warmth (Tết promo / sale)                   |
| Education         | `#7C3AED` violet-600 | `#F5F3FF` violet-50  | `#10B981` emerald-500 | Wisdom + growth (success state khoá học)            |
| SaaS B2B          | `#0F172A` slate-900 | `#F8FAFC` slate-50    | `#06B6D4` cyan-500  | Professional + tech accent                            |
| Government        | `#064E3B` emerald-900 | `#F0FDF4` emerald-50 | `#DC2626` red-600   | Authority + clarity + alert                           |
| Logistics         | `#EA580C` orange-600 | `#FFF7ED` orange-50   | `#1E40AF` blue-800  | Energy + reliability cho route status                 |

> Tất cả primary đều ≥ AA contrast (4.5 :1) trên trắng `#FFFFFF`.
> Verify bằng `getContrast(primary, '#FFFFFF') >= 4.5` (chrome/axe).
> Accent dùng trên surface secondary (50-100 step) để đạt AA cho text-sm.

### Primary × text contrast quick reference

| Industry       | Primary  | Text trắng AA? | Text trắng AAA? | Recommended text |
|:---------------|:---------|:---------------|:----------------|:-----------------|
| Finance        | #1E3A8A  | ✓ (10.7 :1)    | ✓               | `#FFFFFF`        |
| Healthcare     | #059669  | ✓ (4.6 :1)     | ✗               | `#FFFFFF` only ≥ 18 px |
| E-commerce     | #DC2626  | ✓ (4.9 :1)     | ✗               | `#FFFFFF` only ≥ 18 px |
| Education      | #7C3AED  | ✓ (5.7 :1)     | ✗               | `#FFFFFF` ≥ 14 px |
| SaaS B2B       | #0F172A  | ✓ (17.5 :1)    | ✓               | `#FFFFFF`        |
| Government     | #064E3B  | ✓ (10.0 :1)    | ✓               | `#FFFFFF`        |
| Logistics      | #EA580C  | ✓ (4.6 :1)     | ✗               | `#FFFFFF` ≥ 18 px |

## 2. WCAG contrast guidelines (industry-agnostic)

| Use                  | Min contrast | Examples                                  |
|:---------------------|:-------------|:------------------------------------------|
| Body text (≤ 18 px)  | 4.5 :1 (AA)  | text-base default                         |
| Large text (≥ 18 px / ≥ 14 px bold) | 3 :1 (AA) | h1-h3, button text                  |
| AAA body             | 7 :1 (AAA)   | finance / healthcare statutory mandate   |
| UI components / icon | 3 :1 (AA)    | input border, focus ring, status dot     |
| Disabled text        | none required (but ≥ 2.5 :1 đề xuất for usability) |
| Brand mark on hero   | none (decorative) but ≥ 4.5 :1 nếu chứa text |

Recommended tooling:
- **Chrome DevTools** → Inspect element → Styles → Color picker hiển thị contrast ratio inline.
- **axe DevTools** extension cho automated AA scan toàn page.
- **Stark** Figma plugin để verify ngay từ design giai đoạn.
- CI: `pa11y-ci` hoặc `lighthouse-ci` set `--accessibility-score=90` floor.

## 3. Vietnamese cultural color associations

Vietnamese-specific semantic load — KHÔNG được bỏ qua khi UI ship cho thị trường VN.

| Color    | Cultural association          | UI implication                                      |
|:---------|:------------------------------|:----------------------------------------------------|
| Đỏ 🔴    | **Chúc mừng** / khẩn cấp     | Tết banner, alert, KHÔNG dùng cho tang lễ form    |
| Vàng 🟡  | **Vượng** / quyền lực        | Premium, gold tier, KHÔNG dùng cho error / delete |
| Trắng ⚪ | **Tang** (lễ tang)           | Cẩn thận trong wedding / celebration UI           |
| Đen ⚫   | Trang trọng / sang           | Luxury, formal — KHÔNG dùng cho children product |
| Xanh lá 🟢 | Phát triển / sinh khí       | Growth, success, eco — universal positive         |
| Xanh dương 🔵 | Tin cậy / chính thống    | Finance, gov, healthcare — universal trust        |
| Tím 🟣   | Trí tuệ / sáng tạo           | Education, beauty, creativity                     |
| Cam 🟠   | Năng lượng / nhiệt           | Logistics, food delivery, casual SaaS             |

**Tránh** (anti-pattern):
- Vàng làm error color → user nghĩ thông báo tích cực, miss critical.
- Trắng trên hero của wedding/celebration product → cảm giác tang.
- Đỏ bão hoà toàn UI → "alert fatigue", giảm urgency của true alert.

**Khuyến nghị**:
- Tết campaign — `#DC2626` red + `#FBBF24` gold accent (đỏ chúc mừng + vàng vượng).
- Compliance / tax UI — xanh dương + xám (chính thống, tránh đỏ trừ khi error thực).
- Healthcare consumer — xanh lá + xanh dương (calm + trust), tránh đỏ trừ medical alert.

## 4. Color-blind safety

8 % nam giới VN có color-vision deficiency (CVD) — chủ yếu deuteranomaly (yếu xanh-đỏ).
Mọi UI critical KHÔNG được rely 100 % vào màu.

| CVD type        | Population | Affected pair              | Mitigation                              |
|:----------------|:-----------|:---------------------------|:----------------------------------------|
| Deuteranomaly   | ~5 %       | Đỏ ↔ xanh lá              | Thêm icon ✓ / ✕ + text label          |
| Protanomaly     | ~1 %       | Đỏ tối ↔ xanh             | Tăng saturation difference + pattern   |
| Tritanomaly     | ~0.01 %    | Xanh dương ↔ vàng        | Thêm border / shape différenciation   |
| Achromatopsia   | < 0.003 %  | Toàn bộ                   | Đảm bảo grayscale-only mode usable     |

**Status indicator** — đừng chỉ dùng màu:

```
BAD (chỉ màu):                          GOOD (màu + icon + text):
●  ●  ●                                 ✓ Active   ⚠ Warning   ✕ Failed
xanh đỏ vàng                            (xanh lá) (vàng)      (đỏ)
```

**Test tool**:
- `Chrome DevTools` → Rendering tab → Emulate vision deficiency (4 modes).
- `Stark` Figma plugin → Color Blind simulator.
- CI: optional, screenshot diff dùng `pixelmatch` ở các CVD mode.

## 5. Dark mode mapping

Mỗi palette industry phải có dark counterpart — KHÔNG đơn thuần invert.

| Industry          | Light primary | Dark primary       | Light bg     | Dark bg              |
|:------------------|:--------------|:-------------------|:-------------|:---------------------|
| Finance / Retail  | `#1E3A8A`     | `#60A5FA` blue-400 | `#FFFFFF`    | `#020617` slate-950  |
| Healthcare        | `#059669`     | `#34D399` em-400   | `#FFFFFF`    | `#022C22` em-950     |
| E-commerce        | `#DC2626`     | `#F87171` red-400  | `#FFFFFF`    | `#1F1F1F`            |
| Education         | `#7C3AED`     | `#A78BFA` vio-400  | `#FFFFFF`    | `#1E1B2E`            |
| SaaS B2B          | `#0F172A`     | `#E2E8F0` slate-200 | `#FFFFFF`   | `#020617`            |
| Government        | `#064E3B`     | `#10B981` em-500   | `#FFFFFF`    | `#022C22`            |
| Logistics         | `#EA580C`     | `#FB923C` or-400   | `#FFFFFF`    | `#1F1109`            |

**Rule of thumb**:
- Dark primary = **light primary 2-step lighter** (Tailwind 600 → 400).
- Dark bg KHÔNG dùng pure black `#000` — gây OLED smearing; dùng 950 step.
- Status colors (success / warn / error) giữ nguyên hue, chỉ tăng lightness.
- Dark mode contrast cũng phải đạt AA (4.5 :1) — verify lại.

**Auto-derive trong Tailwind**:

```js
// tailwind.config.js
const palette = require('./palettes/finance');
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: palette.light.primary, dark: palette.dark.primary },
        bg:      { DEFAULT: palette.light.bg,      dark: palette.dark.bg },
      },
    },
  },
  darkMode: 'class', // toggle <html class="dark">
};
```

## 6. See also

- [`34-style-tokens.md`](34-style-tokens.md) §2 — generic CP-01..CP-06 (6 entries).
- [`38-font-pairing.md`](38-font-pairing.md) — pair palette với font cho complete style stack.
- [`anti-patterns-gallery.md`](anti-patterns-gallery.md) §AP-12 — VND format errors related semantic color.
- `methodology.COLOR_PSYCHOLOGY` — runtime catalog (6-entry generic CP-01..CP-06).
