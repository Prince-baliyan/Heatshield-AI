import { Badge, Card } from "../ui";

const principles = [
  {
    title: "Sources must be verified",
    description: "Environmental datasets require source, unit, geography, licence and quality review.",
  },
  {
    title: "Missing is not zero",
    description: "Unavailable observations remain unavailable and must not be substituted with fabricated values.",
  },
  {
    title: "Methodology stays transparent",
    description: "Normalization, coverage, thresholds and limitations must be documented and reproducible.",
  },
  {
    title: "Visuals are clearly labelled",
    description: "Conceptual and illustrative views must never be presented as real-time or measured observations.",
  },
];

export function MethodologySection() {
  return (
    <section
      id="methodology"
      className="border-t border-white/5 bg-cyber-panel/20 py-16 sm:py-20 lg:py-24"
    >
      <div className="hs-page">
        <div>
          <Badge variant="cyan">Data transparency</Badge>
          <h2 className="hs-display mt-5 text-3xl font-bold text-slate-50 sm:text-5xl">
            Evidence before intelligence
          </h2>
          <p className="mt-5 max-w-xl leading-7 text-slate-400">
            HeatShield AI is designed around traceable inputs and explicit
            limitations. No IMD integration, live sensor network, scientifically
            validated heat-risk model or verified ward-level dataset is currently
            claimed. The prototype index and its categories remain provisional.
          </p>
        </div>

        <div className="mt-8 grid auto-rows-fr gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {principles.map((principle, index) => (
            <Card
              key={principle.title}
              glass={false}
              className="flex h-full flex-col p-5 sm:p-6"
            >
              <span className="text-xs font-bold tracking-[0.14em] text-slate-500">
                0{index + 1}
              </span>
              <h3 className="mt-3 font-semibold text-slate-100">
                {principle.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                {principle.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
