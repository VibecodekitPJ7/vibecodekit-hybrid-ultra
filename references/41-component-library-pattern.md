# 41 — Component-library pattern (hand-rolled, token-driven)

> **Status:** v0.24.0 (cycle 15 PR-D3). Applies to scaffolds `saas` and
> `dashboard` (Next.js stack).

## 1. Vấn đề

VibecodeKit ship 6 Next.js scaffold với Tailwind theme đã pre-wire
(cycle 15 PR-D1) + `design/tokens.{json,css}` ship sẵn (PR-D2). Nhưng
nếu dev clone scaffold xong và viết JSX kiểu "stylesheet 0":

```tsx
// ❌ anti-pattern: hard-code HEX, không dùng token
<button style={{ background: "#2563EB", color: "white" }}>Đăng ký</button>
```

thì token drift xảy ra ngay session đầu tiên. Mở methodology lên đổi
`CP-01` HEX là `tailwind.config.ts` cập nhật, nhưng inline style
`#2563EB` thì không. App vỡ rời ra thành 2 nguồn truth.

PR-D3 đóng gap này bằng cách ship **một thư viện component minimal**
(Button + Input + Card) tiêu thụ token đúng cách, để dev có ví dụ
sống mà copy từ đó thay vì viết tay.

## 2. Tại sao hand-roll thay vì `npx shadcn-ui init`

| Lý do | Hand-roll (PR-D3 chọn) | `shadcn-ui init` |
|:------|:----------------------:|:----------------:|
| Dependency chain | 0 install (chỉ cần `clsx`, `tailwind-merge` đã add) | 14+ Radix sub-packages |
| Token mapping | Trực tiếp `vck-trust` từ `tailwind.config.ts` | Phải edit `globals.css` `--primary` thủ công |
| Reasoning depth | LLM đọc 50-line component → hiểu | LLM đọc Radix abstraction → confusion |
| Diff diff | 4 file mới, ~150 LOC | 30+ file mới, vendored |
| Update path | Edit local là xong | `shadcn add <component>` từng cái |

Khi project scale lên Dialog/Tooltip/Popover (cần focus management,
portal), hãy chuyển sang Radix primitives hoặc shadcn full registry.
Pattern PR-D3 **không phải bản thay thế shadcn** — nó là **base layer
cho 80% trường hợp**, đủ để demo cách consume token đúng.

## 3. 3 component × 3 variant

### 3.1 Button (`components/ui/button.tsx`)

3 variants:

| Variant | Tokens consumed | Use case |
|:--------|:----------------|:---------|
| `primary` | `bg-vck-trust`, `text-white`, `hover:bg-vck-trust/90` | CTA chính (Đăng ký, Lưu, Submit) |
| `secondary` | `bg-vck-neutral/10`, `text-vck-neutral` | Action phụ (Hủy, Đóng) |
| `ghost` | `bg-transparent`, `text-vck-trust` | Toolbar / nav action |

3 sizes (`sm` / `md` / `lg`). Focus ring luôn dùng `focus-visible:ring-vck-trust`
nên token rename → focus broken (build-time signal, không phải prod bug).

### 3.2 Input (`components/ui/input.tsx`)

3 visual states:

| State | Tokens | Note |
|:------|:-------|:-----|
| `default` | `border-vck-neutral/30`, focus ring `vck-trust` | |
| `error` | `border-vck-warning`, focus ring `vck-warning` | `aria-invalid="true"` set tự động |
| `disabled` | `opacity-50`, `bg-vck-neutral/5` | `disabled` attribute drive |

CP-05 (warning) consistent với mọi error state khác trong app — bug
banner, toast, inline form error đều dùng cùng colour signal.

### 3.3 Card (`components/ui/card.tsx`)

3 variants + 3 subcomponent (`Card`, `CardTitle`, `CardBody`):

| Variant | Tokens |
|:--------|:-------|
| `default` | `bg-vck-neutral/5` (subtle background) |
| `elevated` | `shadow-md ring-1 ring-vck-neutral/10` |
| `bordered` | `border-2 border-vck-trust/40` |

`CardTitle` luôn dùng `font-heading` (FP-01 → Plus Jakarta Sans), `CardBody`
luôn `font-body` (Inter) + `leading-vn-body` (1.6 cho an toàn dấu tiếng Việt).

## 4. cn() helper (`lib/cn.ts`)

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

`clsx` join truthy args; `tailwind-merge` resolve conflict utility (e.g.
caller pass `className="px-8"` đè default `px-5`). Đây là canonical
helper trong shadcn ecosystem — pattern này stable từ shadcn v0.4 đến nay.

## 5. Token consumption pattern

Bias mạnh sang **Tailwind class** (`bg-vck-trust`) vì:
- Build-time tree-shake (CSS only kept nếu dùng).
- IDE autocomplete (Tailwind IntelliSense).
- Token rename → typescript build failure ngay (rename `vck-trust` mà
  quên đổi class → JIT compile bỏ class, focus ring biến mất).

Khi nào dùng CSS var (`var(--vck-trust)`) thay vì Tailwind class:
- Inline SVG `stroke` / `fill` không có Tailwind utility ngon.
- Third-party component (Recharts, Mantine) accept CSS var prop.
- Dynamic theming (PR-D4 dark mode dùng `@media (prefers-color-scheme: dark)`
  flip CSS var, Tailwind class chỉ flip khi `dark:` prefix có).

## 6. Anti-patterns (vi phạm checklist `/vck-design-review`)

| Anti-pattern | Ví dụ | Fix |
|:-------------|:------|:----|
| Hard-code HEX | `style={{ background: "#2563EB" }}` | `className="bg-vck-trust"` |
| Một component một palette riêng | `border-blue-500` (Tailwind builtin) | `border-vck-trust` (token) |
| Skip `cn()` | `className={`base ${cond ? "x" : ""}`}` | `className={cn("base", cond && "x")}` |
| Inline `<style>` | `<button style={...}>` | Tailwind utility class |
| Bỏ `font-heading`/`font-body` | `<h1 className="text-2xl">` | `<h1 className="text-2xl font-heading">` |

Probe `95_shadcn_samples_ship` verify mọi component shipped tham chiếu
ít nhất 1 `vck-*` token + import `cn()` từ `@/lib/cn` để chặn drift về
hard-code HEX trong scaffold sample.

## 7. Extension path

Nếu cần thêm component (`Dialog`, `Tooltip`, `Popover`, `Combobox`, ...)
mà PR-D3 không ship:

1. **Thử Radix primitives** trước (`@radix-ui/react-dialog` v.v.) — pattern
   đã solved focus management, portal, escape key.
2. Wrap Radix bằng cn-style component giống `Button.tsx` để đẩy token
   mapping vào (`bg-vck-trust` cho overlay, etc.).
3. Nếu cần > 5 component dạng này, switch hẳn sang `npx shadcn-ui init`
   — lúc đó shadcn registry value > minimal hand-roll cost.

PR-D3 ship base 3 component vì phép đo: 80% MVP page chỉ cần Button +
Input + Card, hai cái còn lại (Dialog, Combobox) thuộc nhóm "có lúc cần".

## 8. Reference

- PR-D1 (cycle 15 design-apply): pre-wire Tailwind theme.
- PR-D2 (cycle 15 design-apply): ship `design/tokens.{json,css}`.
- PR-D4 (cycle 15 design-apply): dark mode CSS var flip.
- [`references/34-style-tokens.md`](34-style-tokens.md) — token grammar.
- [`references/37-color-psychology.md`](37-color-psychology.md) — CP-01..CP-06.
- [`references/38-font-pairing.md`](38-font-pairing.md) — FP-01..FP-05.
- Probe `95_shadcn_samples_ship` (`scripts/vibecodekit/conformance/probes_governance.py`).
