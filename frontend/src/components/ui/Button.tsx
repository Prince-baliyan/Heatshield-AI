import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "border border-fuchsia-300/30 bg-gradient-to-r from-ultraviolet via-neon-fuchsia to-thermal-orange text-white shadow-[0_12px_32px_rgba(168,85,247,0.24)]",
  secondary:
    "border border-cyan-300/20 bg-cyan-300/10 text-cyan-100",
  ghost:
    "border border-transparent bg-transparent text-slate-300",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "min-h-9 px-3 text-sm",
  md: "min-h-11 px-4 text-sm",
  lg: "min-h-12 px-5 text-base",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[
        "hs-interactive inline-flex items-center justify-center gap-2 rounded-xl font-semibold",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        variantStyles[variant],
        sizeStyles[size],
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
