const footerNavigation = [
  { label: "Overview", href: "/#overview" },
  { label: "Capabilities", href: "/#capabilities" },
  { label: "How It Works", href: "/#how-it-works" },
  { label: "Data & Methodology", href: "/#methodology" },
];

export function Footer() {
  return (
    <footer className="border-t border-white/8 bg-cyber-panel/70">
      <div className="hs-page pt-10 sm:pt-12">
        <div className="grid gap-9 border-b border-white/8 pb-9 lg:grid-cols-[1.15fr_0.75fr_1fr] lg:gap-10">
          <div className="max-w-sm">
            <p className="hs-display text-xl font-bold text-slate-100">
              HeatShield<span className="text-violet-300">-AI</span>
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              A conceptual urban heat intelligence platform focused on
              transparent, evidence-aware climate decision support.
            </p>
          </div>

          <nav
            aria-label="Footer navigation"
            className="flex flex-col items-start"
          >
            <p className="hs-eyebrow mb-3">Quick navigation</p>
            <div className="flex flex-col items-start">
              {footerNavigation.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="inline-flex min-h-11 items-center rounded-md text-sm font-medium text-slate-400 transition-colors hover:text-slate-100"
                >
                  {item.label}
                </a>
              ))}
            </div>
          </nav>

          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-300">
              Data transparency
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Environmental sources and methodologies must be verified before
              operational use. Illustrative visuals are not observations.
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              <a href="/login" className="text-cyan-200 hover:text-white">
                Sign in
              </a>{" "}
              to create assessments, or{" "}
              <a href="/register" className="text-cyan-200 hover:text-white">
                create an account
              </a>
              .
            </p>
          </div>
        </div>

        <div className="flex min-h-16 items-center py-4">
          <p className="text-xs text-slate-500">
            © {new Date().getFullYear()} ByteForce · HeatShield AI
          </p>
        </div>
      </div>
    </footer>
  );
}
