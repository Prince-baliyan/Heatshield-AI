import { Badge, Card } from "../ui";

interface Capability {
  number: string;
  title: string;
  description: string;
  accent: "purple" | "cyan" | "orange";
  icon: "intelligence" | "area" | "indicator" | "response";
}

const capabilities: Capability[] = [
  {
    number: "01",
    title: "Configured locations",
    description:
      "The backend can list configured cities and areas. Catalogue presence does not establish that verified measurements or complete geographic coverage are available.",
    accent: "purple",
    icon: "intelligence",
  },
  {
    number: "02",
    title: "Provenance-aware data",
    description:
      "Provider responses expose source and data-class information. The configured demo weather provider is illustrative, not observed weather.",
    accent: "cyan",
    icon: "area",
  },
  {
    number: "03",
    title: "Provisional assessments",
    description:
      "The prototype can create explainable relative-index assessments with indicator details and coverage states. Its current scoring bounds, weights and categories are provisional, not scientifically validated.",
    accent: "orange",
    icon: "indicator",
  },
  {
    number: "04",
    title: "Human-reviewed suggestions",
    description:
      "Configured, versioned recommendation rules can be attached to assessments. They are suggestions for human review, not validated or automatic interventions.",
    accent: "orange",
    icon: "response",
  },
];

const iconPaths: Record<Capability["icon"], string> = {
  intelligence: "M12 3 20 7v5c0 5.2-3.1 9.2-8 11.6C7.1 21.2 4 17.2 4 12V7l8-4Zm0 4v11m-5-7h10",
  area: "M4 20V8l8-4 8 4v12M8 20v-7h8v7M3 20h18",
  indicator: "M4 18V6m0 12h16M7 15l3-3 3 2 4-6",
  response: "M5 12h14m-6-6 6 6-6 6M7 5H3v14h4",
};

const accentStyles: Record<Capability["accent"], string> = {
  purple: "border-violet-300/15 bg-violet-400/8 text-violet-200",
  cyan: "border-cyan-300/15 bg-cyan-400/8 text-cyan-200",
  orange: "border-orange-300/15 bg-orange-400/8 text-orange-200",
};

export function CapabilitiesSection() {
  return (
    <section id="capabilities" className="border-y border-white/5 py-16 sm:py-20">
      <div className="hs-page">
        <div className="max-w-2xl">
          <p className="hs-eyebrow">Platform capabilities</p>
          <h2 className="hs-display mt-4 text-3xl font-bold leading-tight text-slate-50 sm:text-5xl">
            Prototype capabilities, with clear limits
          </h2>
          <p className="mt-5 leading-7 text-slate-400">
            These describe implemented backend workflows, not a claim of
            verified real-world coverage or operational heat guidance. Data
            availability and assessment outputs depend on configured sources
            and the limitations disclosed for each run.
          </p>
        </div>

        <div className="mt-8 grid auto-rows-fr gap-4 sm:mt-10 sm:grid-cols-2">
          {capabilities.map((capability) => (
            <Card
              key={capability.number}
              className="hs-interactive group flex h-full flex-col p-5 sm:p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <span
                  className={[
                    "grid h-11 w-11 place-items-center rounded-xl border",
                    accentStyles[capability.accent],
                  ].join(" ")}
                >
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none">
                    <path d={iconPaths[capability.icon]} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <Badge variant="neutral">{capability.number}</Badge>
              </div>
              <h3 className="hs-display mt-6 text-xl font-semibold text-slate-100">
                {capability.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                {capability.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
