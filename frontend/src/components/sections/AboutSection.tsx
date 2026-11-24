import { Badge, Card } from "../ui";

const projectPoints = [
  {
    title: "Local Context",
    description:
      "City-wide weather alerts describe broad conditions, while local planning needs to consider area-level heat exposure, vulnerability and protective-service information.",
    accent: "border-t-cyan-300/35",
  },
  {
    title: "Explainable Decisions",
    description:
      "HeatShield AI explores combining available inputs into an explainable decision-support prototype.",
    accent: "border-t-violet-300/35",
  },
  {
    title: "Data Transparency",
    description:
      "Outputs depend on source quality, geographic coverage and a provisional methodology that requires review before operational use.",
    accent: "border-t-amber-300/35",
  },
] as const;

export function AboutSection() {
  return (
    <section
      id="about"
      className="border-y border-white/5 bg-cyber-panel/40 py-16 sm:py-20"
    >
      <div className="hs-page">
        <div>
          <Badge variant="cyan">About the project</Badge>
          <h2 className="hs-display mt-5 text-3xl font-bold text-slate-50 sm:text-4xl">
            Local context, transparent decisions
          </h2>
        </div>
        <div className="mt-8 grid auto-rows-fr gap-4 md:grid-cols-3">
          {projectPoints.map((point) => (
            <Card
              key={point.title}
              className={`h-full border-t-2 p-5 sm:p-6 ${point.accent}`}
            >
              <h3 className="hs-display text-lg font-semibold text-slate-100">
                {point.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                {point.description}
              </p>
            </Card>
          ))}
        </div>
        <p className="mt-5 text-sm leading-6 text-slate-400">
          The project does not replace official alerts or expert judgment.
        </p>
      </div>
    </section>
  );
}
