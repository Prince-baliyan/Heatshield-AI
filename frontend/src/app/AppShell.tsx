import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { Badge } from "../components/ui";
import { formatRole, ProfileAvatar } from "./ProfileIdentity";

const navigation = [
  { label: "Overview", path: "/app", icon: "◫" },
  { label: "New assessment", path: "/app/assessments/new", icon: "+" },
  { label: "Assessments", path: "/app/assessments", icon: "▤" },
  { label: "Recommendations", path: "/app/recommendations", icon: "✧" },
  { label: "Locations", path: "/app/locations", icon: "⌖" },
  { label: "Compare areas", path: "/app/compare", icon: "⇄" },
  { label: "Profile", path: "/app/profile", icon: "◎" },
];

const dataNavigation = [
  { label: "Data Sources", path: "/app/data-sources", icon: "◈" },
  { label: "Datasets", path: "/app/datasets", icon: "▦" },
  { label: "Indicator Observations", path: "/app/observations", icon: "∿" },
];

const pageTitles: Record<string, string> = {
  "/app": "Overview",
  "/app/assessments/new": "New assessment",
  "/app/assessments": "Assessment history",
  "/app/recommendations": "Applied recommendations",
  "/app/locations": "Locations",
  "/app/compare": "Area comparison",
  "/app/data-sources": "Data sources",
  "/app/datasets": "Datasets",
  "/app/observations": "Indicator observations",
  "/app/profile": "Profile",
};

export function AppShell({
  path,
  children,
}: {
  path: string;
  children: ReactNode;
}) {
  const { state, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const accountTriggerRef = useRef<HTMLButtonElement>(null);
  const user = state.status === "ready" ? state.user : null;
  const isAdmin = user !== null && ["staff", "superuser"].includes(user.role);
  const title =
    path.startsWith("/app/assessments/") &&
    path !== "/app/assessments/new"
      ? "Assessment details"
      : pageTitles[path] ?? "HeatShield application";

  useEffect(() => {
    if (!accountMenuOpen) return;

    function handlePointerDown(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !accountMenuRef.current?.contains(event.target)
      ) {
        setAccountMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setAccountMenuOpen(false);
        accountTriggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [accountMenuOpen]);

  async function signOut() {
    setLogoutError(null);
    setSigningOut(true);
    try {
      await logout();
      setAccountMenuOpen(false);
      window.location.replace("/");
    } catch (error) {
      setLogoutError(
        error instanceof Error ? error.message : "Could not sign out.",
      );
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-cyber-night text-slate-100 lg:grid lg:grid-cols-[260px_minmax(0,1fr)]">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/70 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-white/8 bg-[#070b18] transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <a href="/app" className="flex h-[76px] items-center gap-3 border-b border-white/8 px-6">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-violet-500/25 to-cyan-400/10 text-lg text-cyan-200">
            ◈
          </span>
          <span>
            <span className="block font-bold text-white">
              HeatShield<span className="text-cyan-300">-AI</span>
            </span>
            <span className="mt-0.5 block text-[10px] tracking-[0.18em] text-slate-500">
              INTELLIGENCE PLATFORM
            </span>
          </span>
        </a>
        <nav aria-label="Application navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-5">
          {[
            { heading: "Workspace", items: navigation },
            { heading: isAdmin ? "Data Management" : "Data Catalog", items: dataNavigation },
          ].map((section) => (
            <section key={section.heading} className="mb-5">
              <p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">
                {section.heading}
              </p>
              {section.items.map((item) => {
                const active =
                  item.path === "/app"
                    ? path === item.path
                    : item.path === "/app/assessments"
                      ? path === item.path ||
                        (path.startsWith(item.path + "/") &&
                          path !== "/app/assessments/new")
                      : path === item.path;
                return (
                  <a
                    key={item.path}
                    href={item.path}
                    onClick={() => setSidebarOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors ${
                      active
                        ? "bg-cyan-300/10 text-cyan-100 ring-1 ring-cyan-300/15"
                        : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100"
                    }`}
                  >
                    <span aria-hidden="true" className="w-5 text-center text-base">
                      {item.icon}
                    </span>
                    {item.label}
                  </a>
                );
              })}
            </section>
          ))}
        </nav>
        <div className="border-t border-white/8 p-4">
          <div className="mb-3 flex items-center gap-3 rounded-xl bg-white/[0.035] p-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-violet-400/15 font-semibold text-violet-100">
              {user?.username.slice(0, 1).toUpperCase() ?? "U"}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold text-slate-200">
                {user?.username ?? "Signed in"}
              </span>
              <span className="block truncate text-xs text-slate-500">
                {user?.role ?? ""}
              </span>
            </span>
          </div>
          <button
            type="button"
            onClick={signOut}
            className="min-h-10 w-full rounded-xl px-3 text-left text-sm font-medium text-slate-400 transition-colors hover:bg-red-400/10 hover:text-red-100"
          >
            Sign out
          </button>
          {logoutError && (
            <p role="alert" className="mt-2 text-xs leading-5 text-red-200">
              {logoutError}
            </p>
          )}
        </div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex min-h-[76px] items-center justify-between border-b border-white/8 bg-cyber-night/90 px-4 backdrop-blur-xl sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 text-slate-300 lg:hidden"
              aria-label="Open navigation"
            >
              ☰
            </button>
            <div>
              <p className="text-xs text-slate-500">
                Application <span className="px-1">/</span>{" "}
                <span className="text-slate-300">{title}</span>
              </p>
              <h1 className="mt-1 text-sm font-semibold text-slate-100 sm:text-base">
                {title}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <div ref={accountMenuRef} className="relative">
                <button
                  ref={accountTriggerRef}
                  type="button"
                  aria-label={`Account menu for ${user.username}`}
                  aria-expanded={accountMenuOpen}
                  aria-controls="account-menu"
                  onClick={() => {
                    setLogoutError(null);
                    setAccountMenuOpen((open) => !open);
                  }}
                  className="group flex min-h-11 max-w-[min(16rem,calc(100vw-6rem))] items-center gap-2 rounded-xl border border-transparent px-2 py-1.5 text-left transition-colors hover:border-white/10 hover:bg-white/[0.04] focus-visible:border-cyan-200/30 sm:gap-3 sm:px-3"
                >
                  <ProfileAvatar user={user} />
                  <span className="hidden min-w-0 text-left sm:block">
                    <span className="block truncate text-sm font-semibold text-slate-100">
                      {user.username}
                    </span>
                    <span className="hidden truncate text-xs text-slate-500 lg:block">
                      {formatRole(user.role)}
                    </span>
                  </span>
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 20 20"
                    fill="none"
                    className={`hidden h-4 w-4 shrink-0 text-slate-500 transition-transform sm:block ${
                      accountMenuOpen ? "rotate-180" : ""
                    }`}
                  >
                    <path d="m5 7.5 5 5 5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {accountMenuOpen && (
                  <div
                    id="account-menu"
                    className="absolute right-0 top-[calc(100%+0.75rem)] z-50 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-2xl border border-white/10 bg-[#0b1222] shadow-[0_24px_70px_rgba(0,0,0,0.55)]"
                  >
                    <div className="flex items-center gap-3 border-b border-white/8 p-4">
                      <ProfileAvatar user={user} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-white">{user.username}</p>
                        <p className="truncate text-xs text-slate-400">{user.email || "Email not provided"}</p>
                        <Badge variant="cyan" className="mt-2">{formatRole(user.role)}</Badge>
                      </div>
                    </div>
                    <nav aria-label="Account navigation" className="p-2">
                      <a
                        href="/app/profile"
                        aria-current={path === "/app/profile" ? "page" : undefined}
                        onClick={() => setAccountMenuOpen(false)}
                        className="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm text-slate-300 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:bg-white/[0.05]"
                      >
                        <AccountMenuIcon name="profile" />
                        My Profile
                      </a>
                      <a
                        href="/app"
                        onClick={() => setAccountMenuOpen(false)}
                        className="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm text-slate-300 transition-colors hover:bg-white/[0.05] hover:text-white focus-visible:bg-white/[0.05]"
                      >
                        <AccountMenuIcon name="dashboard" />
                        Dashboard
                      </a>
                    </nav>
                    <div className="border-t border-white/8 p-2">
                      <button
                        type="button"
                        disabled={signingOut}
                        onClick={() => void signOut()}
                        className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm text-slate-300 transition-colors hover:bg-red-400/10 hover:text-red-100 focus-visible:bg-red-400/10 disabled:opacity-60"
                      >
                        <AccountMenuIcon name="signout" />
                        {signingOut ? "Signing out…" : "Sign out"}
                      </button>
                      {logoutError && (
                        <p role="alert" className="px-3 pb-2 text-xs leading-5 text-red-200">
                          {logoutError}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 sm:py-9 lg:px-10">
          {children}
        </main>
      </div>
    </div>
  );
}

function AccountMenuIcon({ name }: { name: "profile" | "dashboard" | "signout" }) {
  const paths = {
    profile: <><circle cx="12" cy="8" r="3" /><path d="M5.5 19a6.5 6.5 0 0 1 13 0" /></>,
    dashboard: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    signout: <><path d="M10 5H5v14h5" /><path d="M14 8l4 4-4 4M18 12H9" /></>,
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-[18px] w-[18px] text-slate-500">
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        {paths[name]}
      </g>
    </svg>
  );
}
