import * as React from "react";

import { cn } from "@/lib/cn";

/**
 * Input — minimal hand-rolled, shadcn-style component.
 *
 * 3 visual states (default / error / disabled) all driven through the
 * `vck-*` design tokens.  `error` borrows `vck-warning` (CP-05) for the
 * border + focus ring so colour semantics stay consistent across forms,
 * tables, and toast notifications.
 */
type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  state?: "default" | "error";
};

export function Input({
  state = "default",
  className,
  disabled,
  ...props
}: InputProps) {
  return (
    <input
      disabled={disabled}
      aria-invalid={state === "error" ? "true" : undefined}
      className={cn(
        "block w-full rounded-md border bg-white px-3 py-2 text-base font-body",
        "placeholder:text-vck-neutral/60",
        "focus-visible:outline-none focus-visible:ring-2",
        state === "default" &&
          "border-vck-neutral/30 focus-visible:ring-vck-trust focus-visible:border-vck-trust",
        state === "error" &&
          "border-vck-warning focus-visible:ring-vck-warning text-vck-warning",
        disabled && "opacity-50 cursor-not-allowed bg-vck-neutral/5",
        className,
      )}
      {...props}
    />
  );
}
