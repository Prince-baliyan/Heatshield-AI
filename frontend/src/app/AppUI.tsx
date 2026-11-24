import type { ReactNode } from "react";
import { ApiError } from "../services/api";
import { Badge, Button, Card } from "../components/ui";

export function PageHeading({
  eyebrow = "HeatShield application",
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
      <div>
        <p className="hs-eyebrow">{eyebrow}</p>
        <h1 className="hs-display mt-2 text-3xl font-bold text-slate-50 sm:text-4xl">
          {title}
        </h1>
        {description && (
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400 sm:text-base">
            {description}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

export function LoadingPanel({ label = "Loading live data…" }: { label?: string }) {
  return (
    <Card className="space-y-4 p-6" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className="h-3 w-40 animate-pulse rounded bg-white/10" />
      <div className="h-3 w-3/4 animate-pulse rounded bg-white/[0.07]" />
      <div className="h-3 w-1/2 animate-pulse rounded bg-white/[0.05]" />
    </Card>
  );
}

export function ErrorPanel({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  const message =
    error instanceof ApiError || error instanceof Error
      ? error.message
      : "The request could not be completed.";
  return (
    <Card className="border-red-300/20 p-6">
      <p role="alert" className="text-sm leading-6 text-red-100">
        {message}
      </p>
      {retry && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={retry}
        >
          Retry
        </Button>
      )}
    </Card>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-5 py-10 text-center">
      <p className="font-semibold text-slate-200">{title}</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">
        {detail}
      </p>
    </div>
  );
}

export function DataClassBadge({ value }: { value: string }) {
  const variant =
    value === "illustrative"
      ? "orange"
      : value === "unavailable"
        ? "neutral"
        : value === "observed"
          ? "green"
          : "cyan";
  const label =
    value === "illustrative"
      ? "ILLUSTRATIVE DEMO"
      : value.replaceAll("_", " ");
  return <Badge variant={variant}>{label}</Badge>;
}

export function AssessmentStatusBadge({ value }: { value: string }) {
  const variant =
    value === "SCORED"
      ? "green"
      : value === "INSUFFICIENT_DATA"
        ? "orange"
        : value === "REVIEW_REQUIRED"
          ? "purple"
          : "neutral";
  return <Badge variant={variant}>{value.replaceAll("_", " ")}</Badge>;
}

export function PriorityBadge({ value }: { value: string | null }) {
  const variant =
    value === "high"
      ? "red"
      : value === "medium"
        ? "orange"
        : value === "low"
          ? "cyan"
          : "neutral";
  return <Badge variant={variant}>{value ?? "Priority unavailable"}</Badge>;
}

export function formatNumber(value: string | null) {
  if (value === null) return "—";
  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(
        numericValue,
      )
    : value;
}

export function formatPercent(value: string | null) {
  const formatted = formatNumber(value);
  return formatted === "—" ? formatted : `${formatted}%`;
}

export function formatCategory(value: string | null) {
  return value
    ? value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    : "—";
}

export function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function Table({
  headers,
  children,
}: {
  headers: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-white/8">
      <table className="w-full min-w-[680px] border-collapse text-left text-sm">
        <thead className="bg-white/[0.035] text-xs uppercase tracking-wide text-slate-400">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-4 py-3 font-semibold">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/8">{children}</tbody>
      </table>
    </div>
  );
}
