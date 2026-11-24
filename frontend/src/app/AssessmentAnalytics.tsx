import { Badge, Card } from "../components/ui";
import type {
  Assessment,
  AssessmentIndicator,
  WeatherResponse,
} from "../services/api";
import {
  AssessmentStatusBadge,
  DataClassBadge,
  EmptyState,
  formatCategory,
  formatDate,
  formatNumber,
  formatPercent,
  PriorityBadge,
} from "./AppUI";

type AssessmentSource = "demo" | "observations";

interface ConfigurationIndicator {
  code: string;
  label: string;
  unit: string;
}

function configurationIndicators(assessment: Assessment): ConfigurationIndicator[] {
  const rawIndicators = assessment.configuration_snapshot.indicators;
  if (!Array.isArray(rawIndicators)) return [];
  return rawIndicators.flatMap((item) => {
    if (typeof item !== "object" || item === null) return [];
    const record = item as Record<string, unknown>;
    if (
      typeof record.code !== "string" ||
      typeof record.label !== "string" ||
      typeof record.unit !== "string"
    ) {
      return [];
    }
    return [{ code: record.code, label: record.label, unit: record.unit }];
  });
}

function indicatorLabel(code: string, configuration: ConfigurationIndicator[]) {
  return (
    configuration.find((indicator) => indicator.code === code)?.label ??
    code.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  );
}

function indicatorUnit(code: string, configuration: ConfigurationIndicator[]) {
  const unit = configuration.find((indicator) => indicator.code === code)?.unit;
  if (unit === "degree_celsius") return "°C";
  if (unit === "percent") return "%";
  if (unit === "mm") return "mm";
  return unit ?? "";
}

function indicatorValue(indicator: AssessmentIndicator | undefined) {
  if (!indicator) return "Unavailable";
  const value = indicator.input_value_numeric ?? indicator.input_value_text;
  if (value === null || value === undefined || value === "") return "Unavailable";
  return indicator.input_value_numeric === null
    ? value
    : formatNumber(indicator.input_value_numeric);
}

function readableStatus(value: string) {
  return value.replaceAll("_", " ").toLowerCase();
}

function MetricIcon({ kind }: { kind: "temperature" | "humidity" | "rainfall" }) {
  const paths = {
    temperature: (
      <>
        <path d="M14 14.76V5a2 2 0 0 0-4 0v9.76a4 4 0 1 0 4 0Z" />
        <path d="M12 9v8" />
      </>
    ),
    humidity: (
      <>
        <path d="M12 3.5S5 11 5 15a7 7 0 0 0 14 0c0-4-7-11.5-7-11.5Z" />
        <path d="M9 16a3 3 0 0 0 3 3" />
      </>
    ),
    rainfall: (
      <>
        <path d="M20 16.2A4.5 4.5 0 0 0 18 7.7a6 6 0 0 0-11.5 1.8A3.5 3.5 0 0 0 7 16.4" />
        <path d="m8 19 1-2m4 2 1-2m4 2 1-2" />
      </>
    ),
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-5 w-5">
      {paths[kind]}
    </svg>
  );
}

function MetricCard({
  label,
  value,
  unit,
  source,
  kind,
}: {
  label: string;
  value: string;
  unit: string;
  source: string;
  kind: "temperature" | "humidity" | "rainfall";
}) {
  return (
    <Card className="h-full p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-cyan-200/10 bg-cyan-300/[0.07] text-cyan-200">
          <MetricIcon kind={kind} />
        </div>
      </div>
      <p className="mt-5 text-sm text-slate-400">{label}</p>
      <p className="hs-display mt-1 flex min-h-10 items-baseline gap-1.5 text-2xl font-bold text-white sm:text-3xl">
        {value}
        {value !== "Unavailable" && unit && <span className="text-sm font-medium text-slate-400">{unit}</span>}
      </p>
      <p className="mt-3 truncate text-xs text-slate-500" title={source}>{source}</p>
    </Card>
  );
}

function getProviderSnapshot(assessment: Assessment): WeatherResponse | null {
  const snapshot = assessment.configuration_snapshot.input_snapshot;
  if (!snapshot) return null;
  return {
    source: snapshot.provider ?? "Provider source unavailable",
    data_class: snapshot.data_class ?? "unavailable",
    location: snapshot.location ?? assessment.area.city_name,
    spatial_resolution: snapshot.spatial_resolution ?? "unavailable",
    retrieved_at: snapshot.retrieved_at ?? undefined,
    scenario_id: snapshot.scenario_id ?? undefined,
    scenario_name: snapshot.scenario_name ?? undefined,
    observations: snapshot.observations,
    quality_status: snapshot.quality_status ?? "unavailable",
  };
}

function ScoreProgress({ score }: { score: string | null }) {
  if (score === null) return null;
  const numericScore = Number(score);
  if (!Number.isFinite(numericScore) || numericScore < 0 || numericScore > 100) return null;
  return (
    <div
      className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10"
      role="img"
      aria-label={`Provisional score scale: ${formatNumber(score)} of 100`}
    >
      <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-blue-400" style={{ width: `${numericScore}%` }} />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  note,
  score,
}: {
  label: string;
  value: string;
  note?: string;
  score?: string | null;
}) {
  return (
    <Card className="min-w-0 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 break-words text-lg font-semibold text-slate-100">{value}</p>
      {score !== undefined && <ScoreProgress score={score} />}
      {note && <p className="mt-2 text-xs leading-5 text-slate-500">{note}</p>}
    </Card>
  );
}

function EnvironmentalIndicatorChart({
  assessment,
  configuration,
}: {
  assessment: Assessment;
  configuration: ConfigurationIndicator[];
}) {
  const indicators = assessment.indicators.filter(
    (indicator) => indicator.normalized_value !== null,
  );
  return (
    <Card className="p-5 sm:p-6">
      <div>
        <h3 className="font-semibold text-white">Environmental indicator comparison</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Current assessment snapshot · backend-normalized values; physical units are not compared.
        </p>
      </div>
      {indicators.length === 0 ? (
        <div className="mt-4"><EmptyState title="No normalized indicators available" detail="The backend returned no normalized indicator values for this assessment." /></div>
      ) : (
        <div className="mt-5 space-y-5">
          {indicators.map((indicator) => {
            const value = Number(indicator.normalized_value);
            const width = Number.isFinite(value) ? Math.min(100, Math.max(0, value * 100)) : 0;
            return (
              <div key={indicator.indicator_code}>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="text-slate-200">{indicatorLabel(indicator.indicator_code, configuration)}</span>
                  <span className="font-mono text-cyan-100">{formatNumber(indicator.normalized_value)}</span>
                </div>
                <div
                  className="h-2.5 overflow-hidden rounded-full bg-white/[0.07]"
                  role="img"
                  aria-label={`${indicatorLabel(indicator.indicator_code, configuration)} normalized value ${formatNumber(indicator.normalized_value)}`}
                  title={`Normalized value: ${indicator.normalized_value}`}
                >
                  {Number.isFinite(value) && (
                    <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-300" style={{ width: `${width}%` }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function IndicatorContributionChart({
  assessment,
  configuration,
}: {
  assessment: Assessment;
  configuration: ConfigurationIndicator[];
}) {
  const contributions = assessment.indicators.flatMap((indicator) => {
    if (indicator.contribution === null) return [];
    const value = Number(indicator.contribution);
    return Number.isFinite(value) ? [{ indicator, value }] : [];
  });
  const maximum = Math.max(0, ...contributions.map(({ value }) => Math.abs(value)));
  return (
    <Card className="p-5 sm:p-6">
      <div>
        <h3 className="font-semibold text-white">Indicator contributions</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Contribution values and quality status returned in this assessment snapshot.
        </p>
      </div>
      {contributions.length === 0 ? (
        <div className="mt-4"><EmptyState title="No contributions available" detail="No indicator contribution values were returned for this assessment." /></div>
      ) : (
        <div className="mt-5 space-y-4">
          {contributions.map(({ indicator, value }) => {
            const width = maximum === 0 ? 0 : (Math.abs(value) / maximum) * 100;
            return (
              <div key={indicator.indicator_code}>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm text-slate-200">{indicatorLabel(indicator.indicator_code, configuration)}</span>
                  <span className="font-mono text-sm text-cyan-100" title={`Backend contribution: ${indicator.contribution}`}>
                    {formatNumber(indicator.contribution)}
                  </span>
                </div>
                <div
                  className="h-2 overflow-hidden rounded-full bg-white/[0.07]"
                  role="img"
                  aria-label={`${indicatorLabel(indicator.indicator_code, configuration)} contribution ${formatNumber(indicator.contribution)}`}
                >
                  <div className="h-full rounded-full bg-cyan-300/80" style={{ width: `${width}%` }} />
                </div>
                <p className="mt-1.5 text-xs text-slate-500">{readableStatus(indicator.quality_status)}</p>
              </div>
            );
          })}
        </div>
      )}
      <p className="mt-4 text-xs text-slate-500">Bars show relative magnitude among the contributions returned here; labels retain backend values.</p>
    </Card>
  );
}

function IndicatorDetails({
  assessment,
  configuration,
  provider,
  source,
}: {
  assessment: Assessment;
  configuration: ConfigurationIndicator[];
  provider: WeatherResponse | null;
  source: AssessmentSource;
}) {
  const providerRainfall =
    source === "demo" && assessment.data_class === "illustrative"
      ? provider?.observations.find((item) => item.indicator_code === "RAINFALL_24H")
      : undefined;
  return (
    <Card className="p-5 sm:p-6">
      <h3 className="font-semibold text-white">Indicator details</h3>
      <p className="mt-1 text-xs leading-5 text-slate-500">Values shown here are returned by the assessment snapshot or, for illustrative rainfall, its configured demo provider.</p>
      {assessment.indicators.length === 0 && !providerRainfall ? (
        <div className="mt-4"><EmptyState title="No indicator details available" detail="The backend returned no indicator snapshots for this assessment." /></div>
      ) : (
        <div className="mt-4 space-y-2">
          {assessment.indicators.map((indicator) => {
            const label = indicatorLabel(indicator.indicator_code, configuration);
            const value = indicatorValue(indicator);
            const unit = indicatorUnit(indicator.indicator_code, configuration);
            return (
              <details key={indicator.indicator_code} className="group rounded-xl border border-white/[0.08] bg-white/[0.02]">
                <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
                  <span className="font-medium text-slate-200">{label}</span>
                  <span className="flex items-center gap-3 text-sm text-slate-300">
                    <span>{value}{value !== "Unavailable" && unit ? ` ${unit}` : ""}</span>
                    <span aria-hidden="true" className="text-slate-500 transition-transform group-open:rotate-180">⌄</span>
                  </span>
                </summary>
                <div className="grid gap-3 border-t border-white/[0.06] px-4 py-4 text-sm sm:grid-cols-2">
                  <DetailField label="Normalized value" value={indicator.normalized_value === null ? "Unavailable" : formatNumber(indicator.normalized_value)} />
                  <DetailField label="Contribution" value={indicator.contribution === null ? "Unavailable" : formatNumber(indicator.contribution)} />
                  <DetailField label="Quality status" value={readableStatus(indicator.quality_status)} />
                  <DetailField
                    label="Data source"
                    value={source === "demo" && assessment.data_class === "illustrative" ? provider?.source ?? "Provider source unavailable" : "Stored assessment input; source details are not included in this response"}
                  />
                  <DetailField label="Data class" value={assessment.data_class.replaceAll("_", " ")} />
                  <DetailField label="Observation period" value={source === "demo" && assessment.data_class === "illustrative" ? provider?.observations.find((item) => item.indicator_code === indicator.indicator_code)?.measurement_period ?? "Unavailable" : "Unavailable in assessment response"} />
                  {indicator.explanation && <div className="sm:col-span-2"><DetailField label="Explanation" value={indicator.explanation} /></div>}
                </div>
              </details>
            );
          })}
          {providerRainfall && (
            <details className="group rounded-xl border border-white/[0.08] bg-white/[0.02]">
              <summary className="flex min-h-14 cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
                <span className="font-medium text-slate-200">24-hour rainfall <span className="ml-2 text-xs text-slate-500">provider-only · not scored</span></span>
                <span className="text-sm text-slate-300">{providerRainfall.value ?? "Unavailable"}{providerRainfall.value !== null && providerRainfall.unit ? ` ${providerRainfall.unit}` : ""}</span>
              </summary>
              <div className="grid gap-3 border-t border-white/[0.06] px-4 py-4 text-sm sm:grid-cols-2">
                <DetailField label="Data source" value={provider?.source ?? "Unavailable"} />
                <DetailField label="Data class" value={provider?.data_class ?? "Unavailable"} />
                <DetailField label="Quality status" value={provider?.quality_status ?? "Unavailable"} />
                <DetailField label="Observation period" value={providerRainfall.measurement_period ?? "Unavailable"} />
              </div>
            </details>
          )}
        </div>
      )}
    </Card>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-words text-slate-300">{value}</p>
    </div>
  );
}

function RecommendationCards({ assessment }: { assessment: Assessment }) {
  return (
    <Card className="p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="font-semibold text-white">Applied recommendations</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">Recommendations attached to this saved assessment only.</p>
        </div>
        <span className="text-xs text-slate-500">Assessment #{assessment.id}</span>
      </div>
      <p className="mt-3 rounded-lg border border-cyan-200/10 bg-cyan-300/[0.04] p-3 text-xs leading-5 text-slate-400">
        Recommendations provide general public-awareness guidance and are not a substitute for official alerts or professional advice.
      </p>
      {assessment.recommendations.length === 0 ? (
        <div className="mt-4"><EmptyState title="No recommendations applied" detail="The backend returned no recommendations for this assessment." /></div>
      ) : (
        <ul className="mt-4 space-y-3">
          {assessment.recommendations.map((recommendation) => (
            <li key={recommendation.id} className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="font-semibold text-slate-100">{recommendation.title ?? recommendation.rule_code ?? "Recommendation"}</h4>
                <PriorityBadge value={recommendation.priority} />
                <Badge>Version {recommendation.rule_version_applied ?? "Unavailable"}</Badge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {recommendation.content_snapshot_available
                  ? recommendation.recommendation_text ?? "Snapshot text unavailable."
                  : "Historical content snapshot unavailable; current rule text is not substituted."}
              </p>
              <p className="mt-3 border-t border-white/[0.06] pt-3 text-xs leading-5 text-slate-400">
                <span className="font-medium text-slate-300">Why this appeared: </span>{recommendation.trigger_explanation}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function AssessmentMetadata({
  assessment,
  provider,
}: {
  assessment: Assessment;
  provider: WeatherResponse | null;
}) {
  return (
    <details className="rounded-2xl border border-white/[0.08] bg-white/[0.02]">
      <summary className="cursor-pointer px-5 py-4 font-semibold text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
        Assessment details
      </summary>
      <div className="grid gap-4 border-t border-white/[0.06] px-5 py-4 sm:grid-cols-2 lg:grid-cols-3">
        <DetailField label="Assessment ID" value={String(assessment.id)} />
        <DetailField label="Location" value={`${assessment.area.area_name}, ${assessment.area.city_name}`} />
        <DetailField label="Assessment timestamp" value={formatDate(assessment.run_at)} />
        <DetailField label="Method version" value={assessment.method_version} />
        <DetailField label="Configuration version" value={assessment.configuration_version} />
        <DetailField label="Data class" value={assessment.data_class.replaceAll("_", " ")} />
        <DetailField label="Data coverage" value={formatPercent(assessment.data_coverage)} />
        <DetailField label="Provider retrieval timestamp" value={provider?.retrieved_at ? formatDate(provider.retrieved_at) : "Unavailable"} />
        {provider?.scenario_name && <DetailField label="Demo scenario" value={provider.scenario_name} />}
      </div>
    </details>
  );
}

export function AssessmentAnalytics({
  assessment,
  source,
}: {
  assessment: Assessment;
  source: AssessmentSource;
}) {
  const configuration = configurationIndicators(assessment);
  const savedProvider = getProviderSnapshot(assessment);
  const demoProvider = source === "demo" && assessment.data_class === "illustrative" ? savedProvider : null;
  const byCode = new Map(assessment.indicators.map((indicator) => [indicator.indicator_code, indicator]));
  const metricSource = demoProvider?.source ?? (source === "observations" ? "Stored assessment input" : "Assessment response");
  const metricClass = assessment.data_class;
  const temperature = byCode.get("AIR_TEMPERATURE");
  const humidity = byCode.get("RELATIVE_HUMIDITY");
  const rainfall = demoProvider?.observations.find((item) => item.indicator_code === "RAINFALL_24H");
  const scoreAvailable = assessment.status === "SCORED" && assessment.score !== null;

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200/70">Saved assessment · #{assessment.id}</p>
            <h2 className="hs-display mt-2 text-2xl font-bold text-white sm:text-3xl">{assessment.area.area_name}</h2>
            <p className="mt-1 text-sm text-slate-400">{assessment.area.city_name} · {formatDate(assessment.run_at)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <AssessmentStatusBadge value={assessment.status} />
            {assessment.data_class === "illustrative" ? (
              <Badge variant="orange">ILLUSTRATIVE DATA</Badge>
            ) : (
              <DataClassBadge value={assessment.data_class} />
            )}
            {assessment.risk_category && <Badge variant={assessment.category_is_provisional ? "orange" : "cyan"}>{formatCategory(assessment.risk_category)}</Badge>}
          </div>
        </div>
        {assessment.data_class === "illustrative" && (
          <p className="mt-4 rounded-lg border border-white/[0.07] bg-white/[0.025] px-3 py-2.5 text-xs leading-5 text-slate-300">
            Synthetic demonstration data — not a measured weather observation.
          </p>
        )}
        {assessment.status === "INSUFFICIENT_DATA" && (
          <p className="mt-4 rounded-lg border border-amber-200/15 bg-amber-200/[0.04] px-3 py-2.5 text-sm leading-5 text-amber-100">
            Score unavailable because required data coverage was not met. Missing data is not evidence of low risk.
          </p>
        )}
      </Card>

      <section aria-label="Environmental indicators">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold text-slate-100">Environmental indicators</h3>
          <span className="text-xs text-slate-500">{metricClass.replaceAll("_", " ")} data · snapshot values, not live measurements</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          <MetricCard label="Air temperature" kind="temperature" value={indicatorValue(temperature)} unit={indicatorUnit("AIR_TEMPERATURE", configuration)} source={metricSource} />
          <MetricCard label="Relative humidity" kind="humidity" value={indicatorValue(humidity)} unit={indicatorUnit("RELATIVE_HUMIDITY", configuration)} source={metricSource} />
          <MetricCard
            label="Rainfall (24 hours)"
            kind="rainfall"
            value={rainfall?.value === null || rainfall?.value === undefined ? "Unavailable" : typeof rainfall.value === "number" ? formatNumber(String(rainfall.value)) : rainfall.value}
            unit={rainfall?.unit ?? ""}
            source={rainfall ? `${demoProvider?.source ?? "Provider"} · not scored` : "Not included in this assessment response"}
          />
        </div>
      </section>

      <section aria-label="Assessment summary">
        <h3 className="mb-3 font-semibold text-slate-100">Assessment summary</h3>
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-4">
          <SummaryCard
            label="Assessment score"
            value={scoreAvailable ? formatNumber(assessment.score) : "Score unavailable"}
            note={scoreAvailable ? "Provisional 0–100 relative index; not scientifically validated." : assessment.status === "INSUFFICIENT_DATA" ? "Missing data does not indicate low risk." : undefined}
            score={scoreAvailable ? assessment.score : null}
          />
          <SummaryCard label="Risk category" value={assessment.risk_category ? formatCategory(assessment.risk_category) : "Unavailable"} note={assessment.category_is_provisional ? "Provisional category" : undefined} />
          <SummaryCard label="Data coverage" value={formatPercent(assessment.data_coverage)} />
          <SummaryCard label="Assessment status" value={formatCategory(assessment.status)} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2" aria-label="Indicator charts">
        <EnvironmentalIndicatorChart assessment={assessment} configuration={configuration} />
        <IndicatorContributionChart assessment={assessment} configuration={configuration} />
      </section>

      <IndicatorDetails assessment={assessment} configuration={configuration} provider={demoProvider} source={source} />
      <RecommendationCards assessment={assessment} />
      {assessment.warnings.filter((warning) =>
        !/illustrative demo inputs|scoring bounds, weights, minimum coverage, and categories are provisional/i.test(warning),
      ).length > 0 && (
        <Card className="p-5">
          <h3 className="font-semibold text-slate-100">Limitations and warnings</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-amber-100">
            {assessment.warnings
              .filter((warning) =>
                !/illustrative demo inputs|scoring bounds, weights, minimum coverage, and categories are provisional/i.test(warning),
              )
              .map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </Card>
      )}
      <AssessmentMetadata assessment={assessment} provider={demoProvider} />
      <a
        href={`/app/assessments/${assessment.id}`}
        className="inline-flex min-h-11 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-4 text-sm font-semibold text-cyan-100 transition-colors hover:bg-cyan-300/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
      >
        Open saved assessment
      </a>
    </div>
  );
}
