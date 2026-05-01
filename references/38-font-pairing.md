# 38 — Font pairing (Vietnamese-first)

> Mở rộng `references/34-style-tokens.md` §1 (FP-01..FP-06 generic) thành
> **5 use-case font stacks** với explicit Vietnamese-subset support
> requirement, type-scale ladder, loading strategy + fallback chain.
>
> Cross-link:
> - [`34-style-tokens.md`](34-style-tokens.md) §1 — generic FP-01..FP-06 + §3 Vietnamese typography rules (VN-01..VN-12).
> - [`37-color-psychology.md`](37-color-psychology.md) — pair font + palette cho complete stack.
> - `methodology.FONT_PAIRINGS` — runtime catalog (giữ nguyên 6-entry generic).

---

## 1. 5 recommended font pairs (use-case oriented)

| Pair               | Heading             | Body              | Use case                              |
|:-------------------|:--------------------|:------------------|:--------------------------------------|
| **Modern SaaS**    | Plus Jakarta Sans   | Inter             | B2B dashboards, dev-tools             |
| **Corporate**      | Be Vietnam Pro      | Inter             | Finance, government, compliance       |
| **Editorial**      | Playfair Display    | Source Sans 3     | Blog, content site, knowledge base   |
| **Tech-forward**   | Space Grotesk       | DM Sans           | AI / dev-tools landing                |
| **Friendly consumer** | Manrope         | Inter             | E-commerce, education, food delivery |

> Tất cả ship qua Google Fonts; load đầy đủ subset `latin, latin-ext, vietnamese`
> qua `next/font/google` hoặc Tailwind `@import` chuẩn.

## 2. Vietnamese subset support requirement

| Font                | Vietnamese subset? | Note                                     |
|:--------------------|:-------------------|:-----------------------------------------|
| Inter               | ✓                  | Render đẹp với diacritic ằ ẵ ặ ẫ ậ      |
| DM Sans             | ✓                  | Nhỏ-cỡ-text vẫn rõ                       |
| Plus Jakarta Sans   | ✓                  | Heading đẹp, body cũng dùng được        |
| **Be Vietnam Pro**  | ✓✓ (native VN)    | Designed for Vietnamese — luôn nên dùng cho gov/finance B2B |
| Source Sans 3       | ✓                  | Body editorial OK                        |
| Playfair Display    | ✓                  | Italic OK; KHÔNG dùng cho body          |
| Space Grotesk       | ✓                  | Tech feel; tránh < 14 px                 |
| Manrope             | ✓                  | Friendly + clean                         |

**Tránh** (đã biết là không support đầy đủ Vietnamese subset):
- Italic-only display fonts (Bodoni Moda Italic, Lobster) — fallback ổn nhưng diacritic vỡ.
- Mono-only fonts (JetBrains Mono, Fira Code) cho body — chỉ dùng cho code block.
- Symbol fonts (Material Icons) cho text — duh.

**Smoke test** — paste vào browser console khi preview font:

```html
<p style="font-family: 'Be Vietnam Pro', sans-serif">
  Ứng dụng quản lý ngân sách OTB cho buyer phụ trách quần áo nữ
  trong hệ thống bán lẻ — Tết 2026 chuẩn bị từ tháng 10/2025.
</p>
```

Phải render rõ:
- `Ứ` (U + horn + acute) — không bị cắt phần horn.
- `ằ` (a + breve + grave) — không chồng diacritic.
- `ụ` (u + dot below) — dot below không trùng descender.
- `ẵ` (a + breve + tilde) — đầy đủ 2 dấu trên.

## 3. Type scale (Major Third 1.250 ratio recommended cho VN)

> Vietnamese diacritic top + bottom ăn nhiều vertical space hơn English ~ 25 %,
> nên ưu tiên line-height `1.5-1.6` cho body và `1.2-1.3` cho heading.

| Level         | Size desktop | Size mobile | Line height | Use                                      |
|:--------------|:-------------|:------------|:------------|:-----------------------------------------|
| Display       | 48-72 px     | 40-56 px    | 1.1 (LH = `1.1`) | Hero headline, marketing landing      |
| H1            | 32-40 px     | 28-32 px    | 1.2          | Page title                               |
| H2            | 24-28 px     | 22-24 px    | 1.3          | Section header                           |
| H3            | 20-22 px     | 18-20 px    | 1.35         | Sub-section                              |
| H4            | 18-20 px     | 17-18 px    | 1.4          | Card title                               |
| Body large    | 18 px        | 16 px       | 1.6          | Long-form reading                        |
| Body          | 16 px        | 15 px       | 1.5          | Default                                  |
| Body small    | 14 px        | 13 px       | 1.5          | Caption, table dense data                |
| Label         | 12-13 px     | 12 px       | 1.4          | Badges, form labels, footnotes           |
| Code          | 14 px        | 13 px       | 1.5 (mono)   | `<code>`, terminal output                |

**Ghi chú VN-specific**:
- Body size **mobile ≥ 15 px** — nhỏ hơn diacritic vỡ trên screen mật độ thấp.
- Line-height **1.5-1.6 cho body** (vs 1.4-1.5 cho English).
- Letter-spacing **0** cho body, `-0.01em..0` cho heading — KHÔNG bao giờ dương.

## 4. Loading strategy

```ts
// Next.js 14 — app router
import { Inter, Be_Vietnam_Pro } from 'next/font/google';

const sans = Inter({
  subsets: ['latin', 'latin-ext', 'vietnamese'],
  display: 'swap',                   // ← critical: tránh FOIT > 200 ms
  variable: '--font-sans',
  weight: ['400', '500', '600', '700'],
});

const heading = Be_Vietnam_Pro({
  subsets: ['latin', 'vietnamese'],
  display: 'swap',
  variable: '--font-heading',
  weight: ['600', '700'],            // ← chỉ load weight thật sự dùng
});

// layout.tsx
export default function RootLayout({ children }) {
  return (
    <html lang="vi" className={`${sans.variable} ${heading.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

**Performance budget**:
- Font payload **< 200 KB** total (ép weight subset).
- `display: 'swap'` BẮT BUỘC để tránh FOIT (Flash of Invisible Text).
- Self-host nếu CDN Google Fonts bị chặn (một số corp network VN block GFonts).
- Preload critical font: `<link rel="preload" as="font" href="..." crossorigin>`.

## 5. Fallback stack (Tailwind config)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'var(--font-sans)',           // Inter loaded
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
          'Apple Color Emoji',
          'Segoe UI Emoji',
        ],
        heading: [
          'var(--font-heading)',        // Be Vietnam Pro loaded
          'var(--font-sans)',           // graceful degrade nếu heading miss
          'system-ui',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'Courier New',
          'monospace',
        ],
      },
    },
  },
};
```

**Fallback verify**:
- Trên macOS không có Google Fonts → fallback tới `-apple-system` (San Francisco).
- Trên Windows VN → `Segoe UI` (Microsoft VN subset OK).
- Trên Linux server-rendered (preview) → DejaVu / Liberation (đủ VN diacritic).

## 6. Anti-patterns đã ghi nhận

- **AP-VNF-01**: Font 5+ weight load khiến CLS > 0.25 → giới hạn 2-3 weight.
- **AP-VNF-02**: Body line-height 1.4 trên VN UI → diacritic chạm baseline → ép `≥ 1.5`.
- **AP-VNF-03**: Italic body cho Vietnamese → diacritic mất hình → KHÔNG dùng italic body cho `lang="vi"`.
- **AP-VNF-04**: Letter-spacing dương cho body → tách diacritic khỏi base char → ép `0` hoặc âm.
- **AP-VNF-05**: Font-display block → FOIT > 3 s → ép `swap`.

## 7. See also

- [`34-style-tokens.md`](34-style-tokens.md) §1 — generic FP-01..FP-06 (6 entries).
- [`34-style-tokens.md`](34-style-tokens.md) §3 — Vietnamese typography rules VN-01..VN-12.
- [`37-color-psychology.md`](37-color-psychology.md) — pair font + palette cho complete stack.
- `methodology.FONT_PAIRINGS` — runtime catalog (6-entry generic).
