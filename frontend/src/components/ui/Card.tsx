import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  glass?: boolean;
}

export function Card({
  children,
  glass = true,
  className = "",
  ...props
}: CardProps) {
  return (
    <div
      className={[
        "rounded-2xl",
        glass ? "hs-glass" : "hs-card",
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </div>
  );
}
