import { useEffect, useId, useState } from "react";
import { useAuth } from "../../auth/AuthContext";

const navigation = [
  { label: "Overview", href: "/#overview" },
  { label: "Capabilities", href: "/#capabilities" },
  { label: "How It Works", href: "/#how-it-works" },
  { label: "Data & Methodology", href: "/#methodology" },
];

function ShieldMark() {
  const gradientId = `shield-gradient-${useId().replaceAll(":", "")}`;

  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 40 40"
      className="h-9 w-9"
      fill="none"
    >
      <defs>
        <linearGradient
          id={gradientId}
          x1="8"
          y1="4"
          x2="32"
          y2="36"
        >
          <stop stopColor="#A855F7" />
          <stop offset="0.55" stopColor="#EC4899" />
          <stop offset="1" stopColor="#FF7139" />
        </linearGradient>
      </defs>
      <path
        d="M20 3.5 32.5 8v9.2c0 8.7-5.1 15.3-12.5 19.3C12.6 32.5 7.5 25.9 7.5 17.2V8L20 3.5Z"
        fill="rgba(168,85,247,0.14)"
        stroke={`url(#${gradientId})`}
        strokeWidth="1.8"
      />
      <path
        d="M20 10.5c-3.5 4.3-5.3 8-5.3 11.1a5.3 5.3 0 0 0 10.6 0c0-3.1-1.8-6.8-5.3-11.1Z"
        fill="#FF7139"
        fillOpacity="0.9"
      />
      <circle cx="20" cy="21.7" r="1.8" fill="#020617" />
    </svg>
  );
}

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const { state, logout } = useAuth();
  const user = state.status === "ready" ? state.user : null;

  async function handleLogout() {
    setLogoutError(null);
    try {
      await logout();
      window.location.replace("/");
    } catch (error) {
      setLogoutError(
        error instanceof Error ? error.message : "Could not sign out.",
      );
    }
  }

  useEffect(() => {
    const desktopQuery = window.matchMedia("(min-width: 1024px)");

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    function closeAtDesktop(event: MediaQueryListEvent) {
      if (event.matches) {
        setMenuOpen(false);
      }
    }

    window.addEventListener("keydown", closeOnEscape);
    desktopQuery.addEventListener("change", closeAtDesktop);

    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      desktopQuery.removeEventListener("change", closeAtDesktop);
    };
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-white/8 bg-cyber-night/85 backdrop-blur-xl">
      <nav
        aria-label="Primary navigation"
        className="hs-page flex min-h-[72px] items-center justify-between gap-4"
      >
        <a
          href="/#overview"
          className="inline-flex items-center gap-2 rounded-lg"
          onClick={() => setMenuOpen(false)}
          aria-label="HeatShield AI overview"
        >
          <ShieldMark />
          <span>
            <span className="block hs-display text-base font-bold leading-none text-slate-50 sm:text-lg">
              HeatShield<span className="text-violet-300">-AI</span>
            </span>
            <span className="mt-1 block text-[9px] font-bold tracking-[0.18em] text-slate-500">
              INTELLIGENCE PLATFORM
            </span>
          </span>
        </a>

        <div className="hidden items-center gap-7 lg:flex">
          {navigation.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md text-sm font-medium text-slate-300 transition-colors hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          {user ? (
            <>
              <span className="text-sm text-slate-300">{user.username}</span>
              <a
                href="/app"
                className="rounded-md text-sm font-medium text-cyan-200 transition-colors hover:text-white"
              >
                Open dashboard
              </a>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-md text-sm font-medium text-slate-300 transition-colors hover:text-white"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <a
                href="/login?next=%2Fapp"
                className="rounded-md text-sm font-medium text-slate-300 transition-colors hover:text-white"
              >
                Login
              </a>
              <a
                href="/register"
                className="hs-interactive inline-flex min-h-11 items-center rounded-xl border border-fuchsia-300/30 bg-gradient-to-r from-ultraviolet via-neon-fuchsia to-thermal-orange px-4 text-sm font-bold text-white shadow-[0_12px_32px_rgba(168,85,247,0.18)]"
              >
                Get Started
              </a>
            </>
          )}
        </div>

        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMenuOpen((open) => !open)}
          className="hs-interactive grid h-11 w-11 place-items-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-200 lg:hidden"
        >
          <span className="sr-only">{menuOpen ? "Close menu" : "Open menu"}</span>
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
            {menuOpen ? (
              <path
                d="M6 6l12 12M18 6 6 18"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            ) : (
              <path
                d="M4 7h16M4 12h16M4 17h16"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            )}
          </svg>
        </button>
      </nav>

      <div
        id="mobile-navigation"
        hidden={!menuOpen}
        className="border-t border-white/8 bg-cyber-night px-4 py-4 lg:hidden"
      >
        <div className="mx-auto flex max-w-7xl flex-col gap-2">
          {navigation.map((item) => (
            <a
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className="rounded-xl px-4 py-3 text-sm font-semibold text-slate-200 hover:bg-white/[0.05]"
            >
              {item.label}
            </a>
          ))}
          {user ? (
            <>
              <span className="px-4 py-2 text-sm text-slate-400">
                Signed in as {user.username}
              </span>
              <a
                href="/app"
                onClick={() => setMenuOpen(false)}
                className="mt-2 inline-flex min-h-11 items-center rounded-xl px-4 text-sm font-semibold text-cyan-200 hover:bg-white/[0.05]"
              >
                Open dashboard
              </a>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  void handleLogout();
                }}
                className="mt-2 inline-flex min-h-11 items-center rounded-xl px-4 text-left text-sm font-semibold text-slate-200 hover:bg-white/[0.05]"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <a
                href="/login?next=%2Fapp"
                onClick={() => setMenuOpen(false)}
                className="mt-2 inline-flex min-h-11 items-center rounded-xl px-4 text-sm font-semibold text-slate-200 hover:bg-white/[0.05]"
              >
                Login
              </a>
              <a
                href="/register"
                onClick={() => setMenuOpen(false)}
                className="mt-2 inline-flex min-h-11 items-center justify-center rounded-xl bg-gradient-to-r from-ultraviolet via-neon-fuchsia to-thermal-orange px-4 text-sm font-bold text-white"
              >
                Get Started
              </a>
            </>
          )}
        </div>
      </div>
      {logoutError && (
        <p role="alert" className="hs-page pb-3 text-right text-sm text-red-200">
          {logoutError}
        </p>
      )}
    </header>
  );
}
