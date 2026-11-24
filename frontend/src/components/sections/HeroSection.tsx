import { Badge, Button, Card } from "../ui";

function HeatIntelligenceVisual() {
  return (
    <Card
      className="relative isolate min-h-[390px] overflow-hidden p-5 sm:min-h-[440px]"
      aria-label="Illustrative urban heat intelligence visualization"
    >
      <Badge variant="purple" className="absolute left-5 top-5 z-10">
        Illustrative visualization
      </Badge>

      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-80"
        style={{
          background:
            "radial-gradient(circle at 55% 48%, rgba(255,113,57,0.28), transparent 13%), radial-gradient(circle at 50% 52%, rgba(168,85,247,0.24), transparent 32%), linear-gradient(145deg, rgba(34,211,238,0.05), transparent)",
        }}
      />

      <svg
        aria-hidden="true"
        viewBox="0 0 520 420"
        className="absolute inset-x-3 bottom-3 h-[82%] w-[calc(100%-24px)]"
        fill="none"
      >
        <defs>
          <linearGradient id="city-grid" x1="70" y1="330" x2="430" y2="80">
            <stop stopColor="#22D3EE" stopOpacity="0.5" />
            <stop offset="0.5" stopColor="#A855F7" stopOpacity="0.55" />
            <stop offset="1" stopColor="#FF7139" stopOpacity="0.75" />
          </linearGradient>
          <radialGradient id="heat-core">
            <stop stopColor="#FF7139" stopOpacity="0.8" />
            <stop offset="0.55" stopColor="#EC4899" stopOpacity="0.24" />
            <stop offset="1" stopColor="#A855F7" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g stroke="url(#city-grid)" strokeWidth="1">
          <path d="M48 340 260 240l212 100M48 290l212-100 212 100M48 240l212-100 212 100M48 190l212-100 212 100" opacity="0.22" />
          <path d="m90 360 120-226M180 390l92-276M280 390l4-276M380 360l-78-226" opacity="0.18" />
        </g>
        <ellipse cx="260" cy="225" rx="128" ry="128" fill="url(#heat-core)" />
        <circle cx="260" cy="225" r="86" stroke="#C4B5FD" strokeOpacity="0.36" strokeWidth="1" />
        <circle cx="260" cy="225" r="56" stroke="#22D3EE" strokeOpacity="0.42" strokeWidth="1" />
        <circle cx="260" cy="225" r="8" fill="#FF7139" />
        <g fill="#020617" stroke="#A855F7" strokeWidth="1">
          <path d="M155 272v-58l28-14v58z" />
          <path d="M192 296v-75l34-16v75z" />
          <path d="M238 316v-94l38-18v94z" />
          <path d="M288 300v-77l34-16v77z" />
          <path d="M332 278v-58l29-14v58z" />
        </g>
        <g fill="#22D3EE">
          <circle cx="169" cy="225" r="2.5" />
          <circle cx="209" cy="210" r="2.5" />
          <circle cx="257" cy="210" r="2.5" />
          <circle cx="305" cy="215" r="2.5" />
          <circle cx="346" cy="220" r="2.5" />
        </g>
      </svg>

      <div className="absolute bottom-5 left-5 right-5 z-10 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="hs-glass rounded-xl p-3">
          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Framework</p>
          <p className="mt-1 text-sm font-semibold text-slate-200">Evidence-aware</p>
        </div>
        <div className="hs-glass rounded-xl p-3">
          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Data state</p>
          <p className="mt-1 text-sm font-semibold text-slate-200">Unavailable</p>
        </div>
        <div className="hs-glass hidden rounded-xl p-3 sm:block">
          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">View mode</p>
          <p className="mt-1 text-sm font-semibold text-slate-200">Conceptual</p>
        </div>
      </div>
    </Card>
  );
}

export function HeroSection() {
  function scrollToSection(sectionId: string) {
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    document.getElementById(sectionId)?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
    });
  }

  return (
    <section id="overview" className="relative overflow-hidden py-16 sm:py-20 lg:py-24">
      <div
        aria-hidden="true"
        className="absolute left-[-12rem] top-8 h-80 w-80 rounded-full bg-violet-600/10 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="absolute right-[-10rem] top-16 h-72 w-72 rounded-full bg-fuchsia-500/8 blur-3xl"
      />

      <div className="hs-page relative grid items-center gap-10 lg:grid-cols-[1.08fr_0.92fr]">
        <div>
          <Badge variant="purple" className="mb-6">
            Urban climate intelligence
          </Badge>
          <h1 className="hs-display max-w-4xl text-4xl font-bold leading-[1.02] text-slate-50 sm:text-6xl lg:text-[72px]">
            Understand Urban Heat.{" "}
            <span className="hs-gradient-text">Protect What Matters.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg sm:leading-8">
            HeatShield AI is a decision-support prototype exploring how
            available heat-related indicators can support transparent,
            area-level planning. Its data coverage is limited, and its
            provisional assessment method is not a validated heat-risk
            prediction or an official warning service.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              onClick={() => {
                scrollToSection("capabilities");
              }}
            >
              View capabilities
              <span aria-hidden="true">→</span>
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => {
                scrollToSection("how-it-works");
              }}
            >
              Discover How It Works
            </Button>
          </div>
        </div>
        <HeatIntelligenceVisual />
      </div>
    </section>
  );
}
