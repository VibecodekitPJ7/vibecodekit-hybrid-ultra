import * as React from "react";

import { cn } from "@/lib/cn";

/**
 * Button — minimal hand-rolled, shadcn-style component.
 *
 * Variants and sizes consume the `vck-*` Tailwind tokens shipped in
 * `tailwind.config.ts` (cycle 15 PR-D1).  Token drift therefore caught
 * at build time: rename `vck-trust` → `bg-blue-600` and the focus ring
 * stops applying.
 *
 * 3 variants × 3 sizes:
 *   primary   / secondary / ghost
 *   sm        / md (default) / lg
 */
type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-body transition",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vck-trust",
        size === "sm" && "px-3 py-1.5 text-sm",
        size === "md" && "px-5 py-2.5 text-base",
        size === "lg" && "px-7 py-3.5 text-lg",
        variant === "primary" && "bg-vck-trust text-white hover:bg-vck-trust/90",
        variant === "secondary" &&
          "bg-vck-neutral/10 text-vck-neutral hover:bg-vck-neutral/20",
        variant === "ghost" &&
          "bg-transparent text-vck-trust hover:bg-vck-trust/10",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  );
}
