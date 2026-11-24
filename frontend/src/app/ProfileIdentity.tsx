import type { AuthUser } from "../services/api";

export function getUserInitials(user: Pick<AuthUser, "username" | "email">) {
  const identity = user.username.trim() || user.email.trim();
  const parts = identity.split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  if (parts.length > 1) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return identity.slice(0, 2).toUpperCase();
}

export function formatRole(role: string) {
  return role
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ProfileAvatar({
  user,
  size = "md",
}: {
  user: Pick<AuthUser, "username" | "email">;
  size?: "md" | "lg";
}) {
  const large = size === "lg";
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full border border-cyan-200/20 bg-gradient-to-br from-violet-400/25 via-indigo-400/20 to-cyan-300/20 font-semibold tracking-wide text-cyan-50 shadow-[0_8px_24px_rgba(34,211,238,0.12)] ${
        large ? "h-24 w-24 text-2xl ring-4 ring-cyan-200/5" : "h-10 w-10 text-sm"
      }`}
    >
      {getUserInitials(user)}
    </span>
  );
}
