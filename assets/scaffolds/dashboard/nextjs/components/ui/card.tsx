import * as React from "react";

import { cn } from "@/lib/cn";

/**
 * Card — minimal hand-rolled, shadcn-style component.
 *
 * 3 variants (default / elevated / bordered) drawn from the `vck-*`
 * design tokens.  The component composes through `CardTitle` +
 * `CardBody` so headlines always pick up `font-heading` (FP-01) while
 * body copy stays on `font-body`.
 */
type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "elevated" | "bordered";
};

export function Card({
  variant = "default",
  className,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-white p-6 font-body",
        variant === "default" && "bg-vck-neutral/5",
        variant === "elevated" && "shadow-md ring-1 ring-vck-neutral/10",
        variant === "bordered" && "border-2 border-vck-trust/40",
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-lg font-heading text-vck-trust leading-vn-heading",
        className,
      )}
      {...props}
    />
  );
}

export function CardBody({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "mt-2 text-base text-vck-neutral leading-vn-body",
        className,
      )}
      {...props}
    />
  );
}
