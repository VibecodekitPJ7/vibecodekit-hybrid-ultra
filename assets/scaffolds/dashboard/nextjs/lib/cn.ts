import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Conditional class-name helper used by `components/ui/*`.
 *
 * Combines `clsx` (truthy-arg join) with `tailwind-merge` (last-wins for
 * conflicting Tailwind utilities, e.g. `px-4` vs `px-6`).  This is the
 * canonical shadcn-style helper — the components/ui exports below import
 * it via `@/lib/cn` so the path stays aligned with the path-alias in
 * `tsconfig.json`.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
