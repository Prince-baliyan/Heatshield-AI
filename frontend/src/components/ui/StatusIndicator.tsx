import type { HTMLAttributes } from "react";

type StatusTone = "success" | "warning" | "danger" | "neutral";

interface StatusIndicatorProps extends HTMLAttributes<HTMLSpanElement> {
  label: string;
  tone?: StatusTone;
  pulse?: boolean;
}

const toneStyles: Record<StatusTone, string> = {
  success: "bg-safe-green",
  warning: "bg-thermal-orange",
  danger: "bg-thermal-red",
  neutral: "bg-slate-400",
};

const toneGlowStyles: Record<StatusTone, string> = {
  success: "hs-status-success",
  warning: "hs-status-warning",
  danger: "hs-status-danger",
  neutral: "hs-status-neutral",
};

export function StatusIndicator({
  label,
  tone = "neutral",
  pulse = false,
  className = "",
  ...props
}: StatusIndicatorProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-2 text-xs font-semibold text-slate-300",
        className,
      ].join(" ")}
      {...props}
    >
      <span
        aria-hidden="true"
        className={[
          "h-2 w-2 rounded-full",
          toneStyles[tone],
          toneGlowStyles[tone],
          pulse ? "motion-safe:animate-pulse" : "",
        ].join(" ")}
      />
      {label}
    </span>
  );
}
