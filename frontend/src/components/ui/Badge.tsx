import type { HTMLAttributes, ReactNode } from "react";

type BadgeVariant = "purple" | "cyan" | "orange" | "red" | "green" | "neutral";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  purple: "border-violet-300/20 bg-violet-400/10 text-violet-200",
  cyan: "border-cyan-300/20 bg-cyan-400/10 text-cyan-200",
  orange: "border-orange-300/20 bg-orange-400/10 text-orange-200",
  red: "border-red-300/20 bg-red-400/10 text-red-200",
  green: "border-emerald-300/20 bg-emerald-400/10 text-emerald-200",
  neutral: "border-slate-300/15 bg-slate-400/10 text-slate-300",
};

export function Badge({
  children,
  variant = "neutral",
  className = "",
  ...props
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold",
        variantStyles[variant],
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </span>
  );
}
