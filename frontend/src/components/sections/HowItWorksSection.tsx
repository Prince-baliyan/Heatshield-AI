import { Badge, Card } from "../ui";

const steps = [
  {
    number: "01",
    title: "Choose a configured area",
    description:
      "The prototype API lists configured cities and areas; this public page does not run an area-selection workflow.",
  },
  {
    number: "02",
    title: "Check source and coverage",
    description:
      "Review the source, data class, indicator quality and coverage. Missing inputs remain unavailable rather than being replaced with zero.",
  },
  {
    number: "03",
    title: "Assess only when inputs allow",
    description:
      "The backend reports an insufficient-data state when configured coverage requirements are not met; any score uses a provisional relative index.",
  },
  {
    number: "04",
    title: "Review explanations and suggestions",
    description:
      "Where configured, indicator explanations and versioned suggestions accompany an assessment for human review.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-16 sm:py-20">
      <div className="hs-page">
        <div>
          <p className="hs-eyebrow">Conceptual workflow</p>
          <h2 className="hs-display mt-4 text-3xl font-bold text-slate-50 sm:text-5xl">
            From local signals to informed action
          </h2>
          <p className="mt-5 text-sm leading-7 text-slate-400">
            This summarizes the prototype API flow, not an operational workflow
            on this public website. It does not replace official warnings or
            professional judgment.
          </p>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {steps.map((step, index) => (
            <Card key={step.number} glass={false} className="relative p-5 sm:p-6">
              {index < steps.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute right-[-1.1rem] top-10 hidden h-px w-8 bg-gradient-to-r from-violet-400/60 to-cyan-400/30 xl:block"
                />
              )}
              <Badge variant={index === 3 ? "cyan" : "purple"}>{step.number}</Badge>
              <h3 className="hs-display mt-6 text-lg font-semibold text-slate-100">
                {step.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                {step.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
