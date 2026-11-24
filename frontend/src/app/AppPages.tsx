import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  getDataSources,
  getDatasets,
  getAllAssessments,
  getAreaList,
  getAssessments,
  getAssessmentDetail,
  getCities,
  getIndicatorObservations,
  compareAreas,
  type AppliedRecommendation,
  type Area,
  type AreaComparisonResponse,
  type Assessment,
  type DataSource,
  type Dataset,
  type IndicatorObservation,
  type PaginatedResponse,
} from "../services/api";
import { Badge, Button, Card } from "../components/ui";
import { formatRole, ProfileAvatar } from "./ProfileIdentity";
import { AssessmentAnalytics } from "./AssessmentAnalytics";
import {
  AdminDataSourcesPage,
  AdminDatasetsPage,
  AdminObservationsPage,
} from "./AdminDataManagement";
import {
  DataClassBadge,
  AssessmentStatusBadge,
  EmptyState,
  ErrorPanel,
  formatCategory,
  formatDate,
  formatNumber,
  formatPercent,
  LoadingPanel,
  PageHeading,
  PriorityBadge,
  Table,
} from "./AppUI";

function useResource<T>(load: () => Promise<T>, dependencies: unknown[] = []) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "error"; error: unknown }
    | { status: "ready"; data: T }
  >({ status: "loading" });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    load()
      .then((data) => {
        if (active) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (active) setState({ status: "error", error });
      });
    return () => {
      active = false;
    };
    // Load functions are supplied inline; dependencies define their inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, retry]);

  return { state, retry: () => setRetry((current) => current + 1) };
}

function SummaryCard({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="hs-display mt-3 break-words text-2xl font-bold leading-snug text-white sm:text-3xl">{value}</p>
      {note && <p className="mt-2 text-xs text-slate-500">{note}</p>}
    </Card>
  );
}

function ActivityChart({ assessments }: { assessments: Assessment[] }) {
  const countsByMonth = new Map<string, number>();
  for (const assessment of assessments) {
    const date = new Date(assessment.run_at);
    if (Number.isNaN(date.getTime())) continue;
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    countsByMonth.set(key, (countsByMonth.get(key) ?? 0) + 1);
  }
  const points = [...countsByMonth.entries()]
    .sort(([first], [second]) => first.localeCompare(second))
    .slice(-6)
    .map(([key, count]) => {
      const [year, month] = key.split("-").map(Number);
      const date = new Date(year, month - 1, 1);
      return {
        key,
        label: date.toLocaleString(undefined, { month: "short", year: "2-digit" }),
        count,
      };
    });
  const maximum = Math.max(1, ...points.map((point) => point.count));
  if (points.length === 0) {
    return (
      <div className="mt-5">
        <EmptyState
          title="No assessment activity yet"
          detail="This chart appears after assessment records are returned by the backend."
        />
      </div>
    );
  }
  return (
    <div className="mt-5">
      <div className="flex h-40 items-end gap-2 overflow-x-auto border-b border-l border-white/10 px-2 sm:gap-3">
        {points.map((point) => (
          <div key={point.key} className="flex h-full min-w-14 flex-1 flex-col items-center justify-end gap-2">
            <span className="text-xs text-slate-400">{point.count}</span>
            <div
              title={`${point.count} assessments`}
              className="w-full max-w-12 rounded-t-md bg-gradient-to-t from-violet-500/60 to-cyan-300/80 transition-all"
              style={{ height: `${Math.max(point.count ? 8 : 3, (point.count / maximum) * 112)}px` }}
            />
            <span className="text-xs text-slate-500">{point.label}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        {points.length === 1
          ? "One month of persisted assessment activity is available."
          : `${points.length} months with persisted assessments are shown; empty months are omitted.`}
      </p>
    </div>
  );
}

function RiskDistribution({ assessments }: { assessments: Assessment[] }) {
  const scoredAssessments = assessments.filter(
    (assessment): assessment is Assessment & { risk_category: string } =>
      assessment.risk_category !== null,
  );
  const categories = [...new Set(scoredAssessments.map((item) => item.risk_category))].sort();
  if (categories.length === 0) {
    return (
      <EmptyState
        title="No scored categories yet"
        detail="Risk-category distribution appears when persisted assessments contain categories."
      />
    );
  }
  return (
    <div className="space-y-4">
      {categories.map((category) => {
        const count = scoredAssessments.filter((item) => item.risk_category === category).length;
        const ratio = (count / scoredAssessments.length) * 100;
        return (
          <div key={category}>
            <div className="mb-2 flex justify-between gap-3 text-sm">
              <span className="break-words text-slate-300">{formatCategory(category)}</span>
              <span className="text-slate-500">{count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-400 to-cyan-300"
                style={{ width: `${ratio}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AssessmentRows({ assessments }: { assessments: Assessment[] }) {
  return (
    <Table headers={["Assessment", "Location", "Score", "Category", "Data class", "Coverage", "Date"]}>
      {assessments.map((item) => (
        <tr key={item.id} className="text-slate-300">
          <td className="px-4 py-3">
            <a className="font-semibold text-cyan-200 hover:text-white" href={`/app/assessments/${item.id}`}>
              #{item.id}
            </a>
            <div className="mt-2"><AssessmentStatusBadge value={item.status} /></div>
          </td>
          <td className="px-4 py-3">{item.area.area_name}, {item.area.city_name}</td>
          <td className="px-4 py-3">{formatNumber(item.score)}</td>
          <td className="max-w-48 break-words px-4 py-3">
            {formatCategory(item.risk_category)}
            {item.category_is_provisional && (
              <span className="mt-2 block text-xs text-amber-200">Provisional</span>
            )}
          </td>
          <td className="px-4 py-3"><DataClassBadge value={item.data_class} /></td>
          <td className="px-4 py-3">{formatPercent(item.data_coverage)}</td>
          <td className="px-4 py-3">{formatDate(item.run_at)}</td>
        </tr>
      ))}
    </Table>
  );
}

export function DashboardOverview() {
  const assessmentsResource = useResource(() => getAllAssessments());
  const citiesResource = useResource(() => getCities());
  const areasResource = useResource(() => getAreaList());
  const sourcesResource = useResource(() => getDataSources(1, 1));
  const datasetsResource = useResource(() => getDatasets(1, 1));
  const observationsResource = useResource(() => getIndicatorObservations(1, 1));
  const resources = [
    assessmentsResource,
    citiesResource,
    areasResource,
    sourcesResource,
    datasetsResource,
    observationsResource,
  ] as const;
  const errorResource = resources.find((resource) => resource.state.status === "error");
  if (errorResource?.state.status === "error") {
    return (
      <>
        <PageHeading title="Overview" description="Live summary from configured HeatShield APIs." />
        <ErrorPanel
          error={errorResource.state.error}
          retry={() => {
            assessmentsResource.retry();
            citiesResource.retry();
            areasResource.retry();
            sourcesResource.retry();
            datasetsResource.retry();
            observationsResource.retry();
          }}
        />
      </>
    );
  }
  if (
    assessmentsResource.state.status !== "ready" ||
    citiesResource.state.status !== "ready" ||
    areasResource.state.status !== "ready" ||
    sourcesResource.state.status !== "ready" ||
    datasetsResource.state.status !== "ready" ||
    observationsResource.state.status !== "ready"
  ) {
    return <><PageHeading title="Overview" /><LoadingPanel /></>;
  }
  const assessments = assessmentsResource.state.data.results;
  const cities = citiesResource.state.data.results;
  const areas = areasResource.state.data.results;
  const latest = assessments[0];
  const recommendationRows = assessments
    .flatMap((assessment) =>
      assessment.recommendations.map((recommendation) => ({
        ...recommendation,
        assessment,
      })),
    )
    .slice(0, 4);

  return (
    <>
      <PageHeading
        title="Overview"
        description="A current snapshot of persisted assessments and configured locations."
        action={
          <a href="/app/assessments/new" className="inline-flex min-h-11 items-center rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 px-4 text-sm font-bold text-white">
            Create assessment
          </a>
        }
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryCard label="Total assessments" value={String(assessmentsResource.state.data.count)} note="Persisted API total" />
        <SummaryCard label="Latest score" value={latest?.score ?? "—"} note={latest ? `Assessment #${latest.id}` : "No assessments returned"} />
        <SummaryCard
          label="Latest category"
          value={formatCategory(latest?.risk_category ?? null)}
          note={latest
            ? latest.category_is_provisional
              ? "Provisional category"
              : latest.status.replaceAll("_", " ")
            : "No latest assessment"}
        />
        <SummaryCard label="Data coverage" value={formatPercent(latest?.data_coverage ?? null)} note="Latest assessment response" />
        <SummaryCard label="Available locations" value={String(areas.length)} note={`${cities.length} active cities · API catalog`} />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card className="p-5 sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-white">Assessment activity</h2>
              <p className="mt-1 text-xs text-slate-500">Monthly counts computed from returned assessment timestamps</p>
            </div>
            <Badge>Persisted records</Badge>
          </div>
          <ActivityChart assessments={assessments} />
        </Card>
        <Card className="p-5 sm:p-6">
          <h2 className="font-semibold text-white">Category distribution</h2>
          <p className="mt-1 text-xs text-slate-500">Provisional categories among assessments with a returned category</p>
          <div className="mt-5">
            <RiskDistribution assessments={assessments} />
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card className="p-5 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-semibold text-white">Recent assessments</h2>
            <a href="/app/assessments" className="text-sm text-cyan-200 hover:text-white">View history →</a>
          </div>
          {assessments.length ? (
            <AssessmentRows assessments={assessments.slice(0, 5)} />
          ) : (
            <EmptyState title="No assessments yet" detail="Create an assessment to populate this activity overview." />
          )}
        </Card>
        <Card className="p-5 sm:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <h2 className="font-semibold text-white">Latest recommendations</h2>
            <a href="/app/recommendations" className="text-sm text-cyan-200 hover:text-white">View all →</a>
          </div>
          {recommendationRows.length ? (
            <ul className="space-y-3">
              {recommendationRows.map((item) => (
                <li key={`${item.assessment.id}-${item.id}`} className="rounded-xl border border-white/8 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <a href={`/app/assessments/${item.assessment.id}`} className="font-medium text-slate-100 hover:text-cyan-100">
                      {item.title ?? item.rule_code ?? "Recommendation"}
                    </a>
                    <PriorityBadge value={item.priority} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">
                    {item.content_snapshot_available
                      ? item.recommendation_text ?? "Snapshot text is unavailable."
                      : "Historical content snapshot unavailable; current rule text is not substituted."}
                  </p>
                  <p className="mt-2 text-xs text-slate-600">Assessment #{item.assessment.id} · {item.rule_version_applied}</p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No applied recommendations" detail="Recommendations appear here only when returned on a persisted assessment." />
          )}
        </Card>
      </div>

      <Card className="mt-5 p-5 sm:p-6">
        <h2 className="font-semibold text-white">Data readiness</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <ReadinessItem label="Cities and areas" value={`${cities.length} cities · ${areas.length} areas`} ready={cities.length > 0 && areas.length > 0} />
          <ReadinessItem label="Assessment records" value={`${assessments.length} loaded of ${assessmentsResource.state.data.count}`} ready={assessmentsResource.state.data.count > 0} />
          <ReadinessItem
            label="Data sources"
            value={`${sourcesResource.state.data.count} configured`}
            ready={sourcesResource.state.data.count > 0}
          />
          <ReadinessItem
            label="Datasets and observations"
            value={`${datasetsResource.state.data.count} datasets · ${observationsResource.state.data.count} observations`}
            ready={datasetsResource.state.data.count > 0 && observationsResource.state.data.count > 0}
          />
        </div>
        <p className="mt-4 text-xs leading-5 text-slate-500">
          Counts are returned by authenticated, read-only inventory APIs. Illustrative records remain explicitly classified and do not represent verified measurements.
        </p>
      </Card>
    </>
  );
}

function ReadinessItem({ label, value, ready }: { label: string; value: string; ready: boolean }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.025] p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-200">{value}</p>
      <Badge className="mt-3" variant={ready ? "green" : "orange"}>
        {ready ? "Available" : "Unavailable"}
      </Badge>
    </div>
  );
}

export function AssessmentHistoryPage() {
  const [page, setPage] = useState(1);
  const resource = useResource(() => getAssessments(page), [page]);
  return (
    <>
      <PageHeading title="Assessment history" description="Browse persisted assessment runs and open their saved details." />
      {resource.state.status === "loading" ? (
        <LoadingPanel />
      ) : resource.state.status === "error" ? (
        <ErrorPanel error={resource.state.error} retry={resource.retry} />
      ) : resource.state.data.results.length === 0 ? (
        <EmptyState title="No assessments have been recorded" detail="Create an assessment to begin a persisted history." />
      ) : (
        <>
          <p className="mb-3 text-sm text-slate-500">
            {resource.state.data.count} total · page {page}
          </p>
          <AssessmentRows assessments={resource.state.data.results} />
          <div className="mt-5 flex justify-end gap-3">
            <Button variant="secondary" disabled={!resource.state.data.previous} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button>
            <Button variant="secondary" disabled={!resource.state.data.next} onClick={() => setPage((value) => value + 1)}>Next</Button>
          </div>
        </>
      )}
    </>
  );
}

export function AssessmentDetailPage({ id }: { id: string }) {
  const assessmentId = Number(id);
  const resource = useResource(
    () => Number.isInteger(assessmentId) && assessmentId > 0
      ? getAssessmentDetail(assessmentId)
      : Promise.reject(new Error("Assessment ID must be a positive integer.")),
    [id],
  );
  if (resource.state.status === "loading") return <LoadingPanel label="Loading persisted assessment…" />;
  if (resource.state.status === "error") return <><PageHeading title="Assessment details" /><ErrorPanel error={resource.state.error} retry={resource.retry} /></>;
  const assessment = resource.state.data;
  const source =
    assessment.configuration_snapshot.input_snapshot ||
    assessment.data_class === "illustrative"
      ? "demo"
      : "observations";
  return (
    <>
      <PageHeading
        title={`Assessment #${assessment.id}`}
        description={`${assessment.area.area_name}, ${assessment.area.city_name} · ${formatDate(assessment.run_at)}`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={`/api/v1/assessments/${assessment.id}/export/?format=csv`}
              download={`heatshield-assessment-${assessment.id}.csv`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/10"
            >
              <svg className="h-4 w-4 text-cyan-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </a>
            <a
              href={`/api/v1/assessments/${assessment.id}/export/?format=html`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-200 transition hover:bg-cyan-500/20"
            >
              <svg className="h-4 w-4 text-cyan-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              Print / PDF Report
            </a>
          </div>
        }
      />
      <AssessmentAnalytics assessment={assessment} source={source} />
    </>
  );
}

export function RecommendationsPage() {
  const resource = useResource(() => getAllAssessments());
  if (resource.state.status === "loading") return <LoadingPanel label="Loading applied recommendation snapshots…" />;
  if (resource.state.status === "error") return <><PageHeading title="Applied recommendations" /><ErrorPanel error={resource.state.error} retry={resource.retry} /></>;
  const recommendations: (AppliedRecommendation & { assessment: Assessment })[] =
    resource.state.data.results.flatMap((assessment) =>
      assessment.recommendations.map((item) => ({ ...item, assessment })),
    );
  return (
    <>
      <PageHeading title="Applied recommendations" description="Only recommendation snapshots returned by persisted assessments are shown here. Active rules are configuration, not applied recommendations." />
      <p className="mb-5 text-xs leading-5 text-slate-500">
        Recommendations are public-awareness guidance for this prototype, not medical advice or a substitute for official alerts.
      </p>
      {recommendations.length === 0 ? (
        <EmptyState title="No applied recommendations" detail="No recommendations were returned by the assessment API for the available assessment history." />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {recommendations.map((item) => (
            <Card key={`${item.assessment.id}-${item.id}`} className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-white">{item.title ?? item.rule_code ?? "Recommendation"}</h2>
                <PriorityBadge value={item.priority} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {item.content_snapshot_available
                  ? item.recommendation_text ?? "Snapshot text is unavailable."
                  : "Historical content snapshot unavailable; current rule text is not substituted."}
              </p>
              <p className="mt-3 text-xs leading-5 text-slate-500">Trigger: {item.trigger_explanation}</p>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-4 text-xs text-slate-500">
                <span>Assessment #{item.assessment.id} · {item.assessment.area.area_name}</span>
                <span>Rule version {item.rule_version_applied ?? "unavailable"}</span>
                <a className="text-cyan-200 hover:text-white" href={`/app/assessments/${item.assessment.id}`}>Open assessment →</a>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function formatCoordinates(lat: number | string | null | undefined, lon: number | string | null | undefined) {
  if (lat == null || lon == null) return null;
  const numLat = Number(lat);
  const numLon = Number(lon);
  if (!Number.isFinite(numLat) || !Number.isFinite(numLon)) return null;
  const latStr = `${Math.abs(numLat).toFixed(6)}° ${numLat >= 0 ? "N" : "S"}`;
  const lonStr = `${Math.abs(numLon).toFixed(6)}° ${numLon >= 0 ? "E" : "W"}`;
  return { latStr, lonStr, numLat, numLon, text: `${latStr}, ${lonStr}` };
}

function osmEmbedUrl(lat: number, lon: number) {
  const delta = 0.05;
  const bbox = `${(lon - delta).toFixed(6)},${(lat - delta).toFixed(6)},${(lon + delta).toFixed(6)},${(lat + delta).toFixed(6)}`;
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat.toFixed(6)},${lon.toFixed(6)}`;
}

function osmLink(lat: number, lon: number) {
  return `https://www.openstreetmap.org/?mlat=${lat.toFixed(6)}&mlon=${lon.toFixed(6)}#map=14/${lat.toFixed(4)}/${lon.toFixed(4)}`;
}

function LocationMapMarker({ area }: { area: Area }) {
  const [mapMode, setMapMode] = useState<"osm" | "radar">("osm");
  const coords = formatCoordinates(area.latitude, area.longitude);

  if (!coords) {
    return (
      <Card className="flex flex-col items-center justify-center p-8 text-center">
        <div className="rounded-full bg-amber-500/10 p-3 text-amber-400">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <p className="mt-3 font-semibold text-slate-200">No representative coordinate stored</p>
        <p className="mt-1 text-sm text-slate-400">
          This area has no verified latitude and longitude. Map markers and spatial queries remain disabled.
        </p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
            <h3 className="font-semibold text-slate-100">Representative Coordinate Marker</h3>
          </div>
          <p className="mt-1 font-mono text-xs text-cyan-300">
            {coords.text} ({coords.numLat.toFixed(6)}, {coords.numLon.toFixed(6)})
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMapMode("osm")}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
              mapMode === "osm"
                ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                : "bg-white/5 text-slate-400 hover:text-slate-200"
            }`}
          >
            Map View
          </button>
          <button
            type="button"
            onClick={() => setMapMode("radar")}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
              mapMode === "radar"
                ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                : "bg-white/5 text-slate-400 hover:text-slate-200"
            }`}
          >
            Grid Radar
          </button>
        </div>
      </div>

      <div className="mt-4">
        {mapMode === "osm" ? (
          <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-white/10 bg-slate-950 sm:aspect-[16/9]">
            <iframe
              title={`OpenStreetMap marker for ${area.area_name}`}
              src={osmEmbedUrl(coords.numLat, coords.numLon)}
              className="h-full w-full border-0"
              loading="lazy"
            />
          </div>
        ) : (
          <div className="relative flex aspect-video w-full flex-col items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 sm:aspect-[16/9]">
            <div className="absolute inset-0 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:24px_24px] opacity-25" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-48 w-48 rounded-full border border-cyan-500/20" />
              <div className="absolute h-32 w-32 rounded-full border border-cyan-500/30" />
              <div className="absolute h-16 w-16 rounded-full border border-cyan-500/40" />
              <div className="absolute h-full w-px bg-cyan-500/20" />
              <div className="absolute h-px w-full bg-cyan-500/20" />
            </div>
            <div className="relative z-10 flex flex-col items-center">
              <div className="relative">
                <span className="absolute -inset-2 animate-ping rounded-full bg-red-400/40" />
                <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-white shadow-lg shadow-red-500/50">
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              <span className="mt-2 rounded bg-slate-900/90 px-2 py-0.5 font-mono text-xs font-semibold text-cyan-300 border border-cyan-500/30">
                {coords.text}
              </span>
              <span className="mt-1 text-[11px] text-slate-400">
                {area.area_name} ({area.area_type})
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <a
          href={osmLink(coords.numLat, coords.numLon)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-cyan-300 hover:text-cyan-200 hover:underline"
        >
          View live marker on OpenStreetMap
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
        <span className="text-slate-500">
          Source: OpenStreetMap Nominatim (OSM ID 571773704)
        </span>
      </div>

      <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5">
        <div className="flex items-start gap-2.5">
          <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-xs leading-5 text-amber-200/90">
            <strong className="font-semibold text-amber-300">Point Marker Limitation: </strong>
            {area.geometry_limitation || "Only a representative city-level point is available. Municipal or ward polygons are not stored and are not shown."}
            <span className="mt-1 block text-amber-400/80 font-medium">
              Ward boundaries and polygons are never invented.
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export function LocationsPage() {
  const citiesResource = useResource(() => getCities());
  const areasResource = useResource(() => getAreaList());
  const [selectedAreaId, setSelectedAreaId] = useState<number | null>(null);

  if (citiesResource.state.status === "loading" || areasResource.state.status === "loading") {
    return (
      <>
        <PageHeading title="Locations & Map Readiness" />
        <LoadingPanel label="Loading city and area catalogues…" />
      </>
    );
  }

  const error =
    citiesResource.state.status === "error"
      ? citiesResource.state
      : areasResource.state.status === "error"
        ? areasResource.state
        : null;

  if (error?.status === "error") {
    return (
      <>
        <PageHeading title="Locations & Map Readiness" />
        <ErrorPanel
          error={error.error}
          retry={() => {
            citiesResource.retry();
            areasResource.retry();
          }}
        />
      </>
    );
  }

  if (citiesResource.state.status !== "ready" || areasResource.state.status !== "ready") {
    return (
      <>
        <PageHeading title="Locations & Map Readiness" />
        <LoadingPanel label="Loading city and area catalogues…" />
      </>
    );
  }

  const cities = citiesResource.state.data.results;
  const areas = areasResource.state.data.results;

  const currentSelectedArea =
    areas.find((area) => area.id === selectedAreaId) || areas[0] || null;

  const readyCount = areas.filter(
    (area) => area.assessment_ready || area.readiness_status === "READY",
  ).length;
  const coordsCount = areas.filter(
    (area) => area.latitude != null && area.longitude != null,
  ).length;

  return (
    <>
      <PageHeading
        title="Locations & Map Readiness"
        description="Supported locations, coordinate markers, and server-side data readiness diagnostics. HeatShield AI operates on verified representative points and never fabricates ward polygons."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <SummaryCard
          label="Configured Cities"
          value={String(cities.length)}
          note={cities.map((city) => city.name).join(", ") || "None"}
        />
        <SummaryCard
          label="Configured Areas"
          value={String(areas.length)}
          note="Supported analysis units"
        />
        <SummaryCard
          label="Assessment Ready"
          value={`${readyCount} / ${areas.length}`}
          note={readyCount > 0 ? "Criteria fully satisfied" : "Data gaps present"}
        />
        <SummaryCard
          label="Verified Coordinates"
          value={`${coordsCount} / ${areas.length}`}
          note="Nominatim point markers"
        />
      </div>

      {cities.length === 0 ? (
        <EmptyState
          title="No cities available"
          detail="No active cities were returned by the backend catalogue."
        />
      ) : (
        <div className="mt-8 space-y-8">
          {currentSelectedArea && (
            <div className="grid gap-6 lg:grid-cols-12">
              <div className="space-y-6 lg:col-span-5">
                <Card className="p-5 sm:p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        {currentSelectedArea.city.name}, {currentSelectedArea.city.state_name} ({currentSelectedArea.city.country_code})
                      </span>
                      <h2 className="hs-display mt-1 text-2xl font-bold text-white">
                        {currentSelectedArea.area_name}
                      </h2>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      <Badge variant="cyan">{currentSelectedArea.area_type.toUpperCase()}</Badge>
                      {currentSelectedArea.assessment_ready || currentSelectedArea.readiness_status === "READY" ? (
                        <Badge variant="green">ASSESSMENT READY</Badge>
                      ) : (
                        <Badge variant="orange">NOT READY</Badge>
                      )}
                    </div>
                  </div>

                  <div className="mt-6 space-y-4">
                    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Readiness Status</span>
                        <span
                          className={`font-semibold ${
                            currentSelectedArea.assessment_ready || currentSelectedArea.readiness_status === "READY"
                              ? "text-emerald-400"
                              : "text-amber-400"
                          }`}
                        >
                          {currentSelectedArea.readiness_status || "NOT_READY"}
                        </span>
                      </div>

                      <div className="mt-3 border-t border-white/5 pt-3">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                          Diagnostic Reasons:
                        </p>
                        {currentSelectedArea.readiness_reasons && currentSelectedArea.readiness_reasons.length > 0 ? (
                          <ul className="mt-2 space-y-1.5 text-xs text-amber-300">
                            {currentSelectedArea.readiness_reasons.map((reason, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="text-amber-400">•</span>
                                <span>{reason}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-2 text-xs text-emerald-300">
                            ✓ All readiness criteria satisfied: verified representative coordinate, approved data source, fresh observations, and period alignment verified.
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs space-y-2.5">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Freshness Status</span>
                        <span className="font-semibold text-slate-200">
                          {currentSelectedArea.freshness_status || "UNKNOWN"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Observation Age</span>
                        <span className="text-slate-300">
                          {currentSelectedArea.observation_age_days != null
                            ? `${currentSelectedArea.observation_age_days} day(s) (max allowed: ${currentSelectedArea.max_observation_age_days ?? 7})`
                            : "No observations"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Latest Period</span>
                        <span className="font-mono text-slate-300">
                          {currentSelectedArea.latest_observation_period?.start
                            ? `${currentSelectedArea.latest_observation_period.start} to ${currentSelectedArea.latest_observation_period.end}`
                            : "None"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Available Indicators</span>
                        <span className="text-cyan-300">
                          {currentSelectedArea.available_indicators?.join(", ") || "None"}
                        </span>
                      </div>
                      {currentSelectedArea.missing_indicators && currentSelectedArea.missing_indicators.length > 0 && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">Missing Indicators</span>
                          <span className="text-amber-400">
                            {currentSelectedArea.missing_indicators.join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </div>

              <div className="lg:col-span-7">
                <LocationMapMarker area={currentSelectedArea} />
              </div>
            </div>
          )}

          <Card className="p-5 sm:p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">All Configured Locations</h3>
            <Table headers={["City", "Area", "Type", "Coordinates", "Readiness", "Freshness", "Actions"]}>
              {cities.map((city) => {
                const cityAreas = areas.filter((area) => area.city_id === city.id);
                return cityAreas.map((area) => {
                  const isSelected = area.id === currentSelectedArea?.id;
                  const isReady = area.assessment_ready || area.readiness_status === "READY";
                  const coords = formatCoordinates(area.latitude, area.longitude);
                  return (
                    <tr
                      key={area.id}
                      className={`text-slate-300 transition-colors ${
                        isSelected ? "bg-cyan-500/10" : "hover:bg-white/[0.02]"
                      }`}
                    >
                      <td className="px-4 py-3 font-medium text-white">{city.name}</td>
                      <td className="px-4 py-3">{area.area_name}</td>
                      <td className="px-4 py-3">
                        <Badge variant="cyan">{area.area_type}</Badge>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-300">
                        {coords ? coords.text : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {isReady ? (
                          <Badge variant="green">READY</Badge>
                        ) : (
                          <Badge variant="orange">NOT READY</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span
                          className={
                            area.freshness_status === "FRESH"
                              ? "text-emerald-400 font-semibold"
                              : area.freshness_status === "STALE"
                                ? "text-amber-400 font-semibold"
                                : "text-slate-400"
                          }
                        >
                          {area.freshness_status || "MISSING"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => setSelectedAreaId(area.id)}
                          className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                            isSelected
                              ? "bg-cyan-500 text-slate-950 font-bold"
                              : "border border-white/10 text-cyan-300 hover:bg-white/5"
                          }`}
                        >
                          {isSelected ? "Viewing" : "View Map"}
                        </button>
                      </td>
                    </tr>
                  );
                });
              })}
            </Table>
          </Card>
        </div>
      )}
    </>
  );
}

export function AreaComparisonPage() {
  const areasResource = useResource(() => getAreaList());
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [comparisonState, setComparisonState] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "error"; message: string }
    | { status: "ready"; data: AreaComparisonResponse }
  >({ status: "idle" });

  const areas = areasResource.state.status === "ready" ? areasResource.state.data.results : [];

  const handleToggle = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === areas.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(areas.map((a) => a.id));
    }
  };

  const runComparison = async () => {
    if (selectedIds.length < 2) return;
    setComparisonState({ status: "loading" });
    try {
      const data = await compareAreas(selectedIds);
      setComparisonState({ status: "ready", data });
    } catch (err: unknown) {
      setComparisonState({
        status: "error",
        message: err instanceof Error ? err.message : "Comparison request failed.",
      });
    }
  };

  return (
    <>
      <PageHeading
        title="Area Comparison"
        description="Side-by-side multi-area vulnerability comparison and relative ranking. Built on transparent deterministic scoring without synthetic imputation."
      />

      {areasResource.state.status === "loading" ? (
        <LoadingPanel label="Loading areas catalog…" />
      ) : areasResource.state.status === "error" ? (
        <ErrorPanel error={areasResource.state.error} retry={areasResource.retry} />
      ) : areas.length < 2 ? (
        <Card className="p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-semibold text-white">Area Comparison Requires At Least Two Areas</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
            Currently, {areas.length} verified area ({areas[0]?.area_name ?? "None"}) is active in the catalog.
            Once additional verified cities or wards are configured in the database, multi-area relative comparisons will activate here.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <a href="/app/locations" className="rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-white/5">
              View Locations Catalog
            </a>
            <a href="/app/assessments/new" className="rounded-xl bg-cyan-500 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-400">
              Run Single Area Assessment
            </a>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          <Card className="p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="font-semibold text-white">Select Areas to Compare</h3>
                <p className="mt-1 text-xs text-slate-400">Choose two or more analysis units for side-by-side evaluation</p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={handleSelectAll}>
                  {selectedIds.length === areas.length ? "Deselect All" : "Select All"}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={selectedIds.length < 2 || comparisonState.status === "loading"}
                  onClick={runComparison}
                >
                  {comparisonState.status === "loading" ? "Comparing…" : `Compare ${selectedIds.length} Areas`}
                </Button>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {areas.map((area) => {
                const isChecked = selectedIds.includes(area.id);
                return (
                  <label
                    key={area.id}
                    className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl border p-3 transition-colors ${
                      isChecked
                        ? "border-cyan-500/50 bg-cyan-500/10 text-white"
                        : "border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/[0.04]"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleToggle(area.id)}
                        className="h-4 w-4 rounded border-white/20 bg-slate-900 text-cyan-500"
                      />
                      <div>
                        <span className="block text-sm font-medium">{area.area_name}</span>
                        <span className="text-xs text-slate-400">{area.city.name} ({area.area_type})</span>
                      </div>
                    </div>
                    {area.assessment_ready || area.readiness_status === "READY" ? (
                      <Badge variant="green">READY</Badge>
                    ) : (
                      <Badge variant="orange">NOT READY</Badge>
                    )}
                  </label>
                );
              })}
            </div>
          </Card>

          {comparisonState.status === "loading" && <LoadingPanel label="Computing multi-area comparative analysis…" />}

          {comparisonState.status === "error" && <ErrorPanel error={comparisonState.message} retry={runComparison} />}

          {comparisonState.status === "ready" && (
            <div className="space-y-6">
              {comparisonState.data.vulnerability_ranking.length > 0 && (
                <Card className="p-5 sm:p-6">
                  <h3 className="mb-4 font-semibold text-white">Relative Vulnerability Ranking</h3>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {comparisonState.data.vulnerability_ranking.map((item) => (
                      <div
                        key={item.area_id}
                        className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4"
                      >
                        <div className="flex items-center gap-3">
                          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/20 text-xs font-bold text-cyan-300">
                            #{item.rank}
                          </span>
                          <div>
                            <p className="font-semibold text-white">{item.area_name}</p>
                            <p className="text-xs text-slate-400">Score: {item.score ?? "—"}</p>
                          </div>
                        </div>
                        <Badge variant={item.score ? "orange" : "neutral"}>
                          {item.risk_category?.replace("_", " ") ?? "UNSCORED"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              <div className="grid gap-6 md:grid-cols-2">
                {comparisonState.data.results.map(({ area, latest_assessment }) => (
                  <Card key={area.id} className="p-5 sm:p-6">
                    <div className="flex items-start justify-between gap-3 border-b border-white/10 pb-4">
                      <div>
                        <h4 className="text-lg font-bold text-white">{area.area_name}</h4>
                        <p className="text-xs text-slate-400">{area.city.name}, {area.city.state_name}</p>
                      </div>
                      <Badge variant="cyan">{area.area_type.toUpperCase()}</Badge>
                    </div>

                    <div className="mt-4 space-y-3 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Readiness Status</span>
                        <span className={area.assessment_ready ? "font-semibold text-emerald-400" : "font-semibold text-amber-400"}>
                          {area.readiness_status || "NOT_READY"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Coordinates</span>
                        <span className="font-mono text-slate-300">
                          {area.latitude && area.longitude ? `${Number(area.latitude).toFixed(4)}, ${Number(area.longitude).toFixed(4)}` : "None"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Latest Vulnerability Score</span>
                        <span className="font-bold text-white">
                          {latest_assessment?.score ?? "No scored assessment"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Risk Category</span>
                        <span className="text-cyan-300">
                          {latest_assessment?.risk_category?.replace("_", " ") ?? "—"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Data Coverage</span>
                        <span className="text-slate-300">
                          {latest_assessment?.data_coverage ? `${latest_assessment.data_coverage}%` : "—"}
                        </span>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs text-slate-400">
                <strong className="text-slate-300">Comparative Policy Notice: </strong>
                {comparisonState.data.caveats}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

function PaginatedInventoryPage<T>({
  title,
  description,
  emptyTitle,
  emptyDetail,
  headers,
  load,
  renderRows,
}: {
  title: string;
  description: string;
  emptyTitle: string;
  emptyDetail: string;
  headers: string[];
  load: (page: number) => Promise<PaginatedResponse<T>>;
  renderRows: (items: T[]) => ReactNode;
}) {
  const [page, setPage] = useState(1);
  const resource = useResource(() => load(page), [page]);

  return (
    <>
      <PageHeading title={title} description={description} />
      {resource.state.status === "loading" ? (
        <LoadingPanel />
      ) : resource.state.status === "error" ? (
        <ErrorPanel error={resource.state.error} retry={resource.retry} />
      ) : resource.state.data.results.length === 0 ? (
        <EmptyState title={emptyTitle} detail={emptyDetail} />
      ) : (
        <>
          <p className="mb-3 text-sm text-slate-500">
            {resource.state.data.count} records · page {page}
          </p>
          <Table headers={headers}>{renderRows(resource.state.data.results)}</Table>
          <div className="mt-5 flex justify-end gap-3">
            <Button
              variant="secondary"
              disabled={!resource.state.data.previous}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={!resource.state.data.next}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </>
  );
}

export function DataSourcesPage() {
  const { state } = useAuth();
  if (state.status === "ready" && state.user && ["staff", "superuser"].includes(state.user.role)) {
    return <AdminDataSourcesPage />;
  }
  return (
    <PaginatedInventoryPage<DataSource>
      title="Data sources"
      description="Approved environmental data providers and the number of active datasets available from each."
      emptyTitle="No data sources are configured"
      emptyDetail="No source records were returned. A source must be registered before datasets can be associated with it."
      headers={["Source", "Owner", "Approval status", "Active datasets", "Created"]}
      load={(page) => getDataSources(page)}
      renderRows={(sources) => sources.map((source) => (
        <tr key={source.id} className="text-slate-300">
          <td className="px-4 py-3 font-medium text-white">{source.source_name}</td>
          <td className="px-4 py-3">{source.owner_name}</td>
          <td className="px-4 py-3">
            <Badge variant={source.approval_status.toLowerCase() === "approved" ? "green" : source.approval_status.toLowerCase() === "rejected" ? "red" : "orange"}>
              {source.approval_status.replaceAll("_", " ")}
            </Badge>
          </td>
          <td className="px-4 py-3">{source.dataset_count}</td>
          <td className="px-4 py-3">{formatDate(source.created_at)}</td>
        </tr>
      ))}
    />
  );
}

export function DatasetsPage() {
  const { state } = useAuth();
  if (state.status === "ready" && state.user && ["staff", "superuser"].includes(state.user.role)) {
    return <AdminDatasetsPage />;
  }
  return (
    <PaginatedInventoryPage<Dataset>
      title="Datasets"
      description="Read-only catalog of active datasets linked to approved sources. Illustrative datasets are not measured weather."
      emptyTitle="No datasets are configured"
      emptyDetail="No dataset records were returned. The dashboard does not invent sources, coverage or measurements."
      headers={["Dataset", "Source", "Data class", "Resolution", "Coverage", "State"]}
      load={(page) => getDatasets(page)}
      renderRows={(datasets) => datasets.map((dataset) => (
        <tr key={dataset.id} className="text-slate-300">
          <td className="px-4 py-3 font-medium text-white">
            {dataset.dataset_name}
            <p className="mt-1 text-xs text-slate-500">Retrieved {formatDate(dataset.retrieved_at)}</p>
          </td>
          <td className="px-4 py-3">{dataset.source_name}</td>
          <td className="px-4 py-3"><DataClassBadge value={dataset.data_class} /></td>
          <td className="px-4 py-3">{dataset.spatial_resolution}</td>
          <td className="px-4 py-3">
            {dataset.coverage_start ?? "Unspecified"} – {dataset.coverage_end ?? "unspecified"}
          </td>
          <td className="px-4 py-3">
            <Badge variant={dataset.is_active ? "green" : "neutral"}>
              {dataset.is_active ? "Active" : "Inactive"}
            </Badge>
          </td>
        </tr>
      ))}
    />
  );
}

export function ObservationsPage() {
  const { state } = useAuth();
  if (state.status === "ready" && state.user && ["staff", "superuser"].includes(state.user.role)) {
    return <AdminObservationsPage />;
  }
  return (
    <PaginatedInventoryPage<IndicatorObservation>
      title="Indicator observations"
      description="Stored observation records returned by approved, active datasets. Missing values are not treated as zero."
      emptyTitle="No verified observations are currently available."
      emptyDetail="No stored observation records were returned. Illustrative provider samples are displayed only in the assessment workflow and are not stored observations."
      headers={["Indicator", "Location", "Dataset", "Value", "Period", "Quality"]}
      load={(page) => getIndicatorObservations(page)}
      renderRows={(observations) => observations.map((observation) => (
        <tr key={observation.id} className="text-slate-300">
          <td className="px-4 py-3 font-medium text-white">
            {observation.indicator_code}
            <div className="mt-2"><DataClassBadge value={observation.data_class} /></div>
          </td>
          <td className="px-4 py-3">{observation.area_name}, {observation.city_name}</td>
          <td className="px-4 py-3">{observation.dataset_name}</td>
          <td className="px-4 py-3">
            {observation.raw_value_numeric ?? observation.raw_value_text ?? "Missing"}
            {observation.raw_unit ? ` ${observation.raw_unit}` : ""}
          </td>
          <td className="px-4 py-3">
            {observation.period_start} – {observation.period_end}
          </td>
          <td className="px-4 py-3">
            <Badge variant={observation.quality_status === "VALID" ? "green" : "orange"}>
              {observation.quality_status.replaceAll("_", " ")}
            </Badge>
          </td>
        </tr>
      ))}
    />
  );
}

export function ProfilePage() {
  const { state, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  if (state.status !== "ready" || !state.user) {
    return <LoadingPanel label="Loading authenticated profile…" />;
  }
  const user = state.user;

  async function signOut() {
    setSigningOut(true);
    setLogoutError(null);
    try {
      await logout();
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
    <>
      <PageHeading
        title="Profile"
        description="Your account identity and verified security details."
      />

      <Card className="relative isolate overflow-hidden p-6 sm:p-8 lg:p-10">
        <div
          aria-hidden="true"
          className="absolute -right-20 -top-32 -z-10 h-80 w-80 rounded-full bg-cyan-400/[0.08] blur-3xl"
        />
        <div
          aria-hidden="true"
          className="absolute -bottom-36 left-1/3 -z-10 h-72 w-72 rounded-full bg-violet-500/[0.08] blur-3xl"
        />
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:gap-8">
          <ProfileAvatar user={user} size="lg" />
          <div className="min-w-0 flex-1">
            <p className="hs-eyebrow">Account overview</p>
            <h2 className="hs-display mt-2 break-words text-3xl font-bold text-white sm:text-4xl">
              {user.username}
            </h2>
            <p className="mt-2 break-all text-sm text-slate-300 sm:text-base">
              {user.email || "Email not provided"}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Badge variant="cyan">{formatRole(user.role)}</Badge>
              <span className="text-xs text-slate-500">
                Identity confirmed by your current authenticated session
              </span>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-5 grid items-stretch gap-5 xl:grid-cols-2">
        <Card className="p-5 sm:p-7">
          <SectionTitle
            icon="identity"
            title="Account information"
            description="Profile fields returned by the authenticated session endpoint."
          />
          <dl className="mt-6 grid gap-3 sm:grid-cols-2">
            <ProfileInfo label="Username" value={user.username} />
            <ProfileInfo label="Email address" value={user.email || "Not provided"} />
            <ProfileInfo label="Account role" value={formatRole(user.role)} />
          </dl>
          <p className="mt-5 border-t border-white/8 pt-4 text-xs leading-5 text-slate-500">
            Account status and date joined are not provided by the current profile API.
          </p>
        </Card>

        <Card className="p-5 sm:p-7">
          <SectionTitle
            icon="security"
            title="Account security"
            description="Security details verified by the current backend integration."
          />
          <div className="mt-6 flex items-start gap-4 rounded-xl border border-emerald-300/10 bg-emerald-300/[0.035] p-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-300/10 text-emerald-200">
              <ProfilePageIcon name="lock" />
            </span>
            <div>
              <p className="font-semibold text-slate-100">Django session authentication</p>
              <p className="mt-1 text-sm leading-6 text-slate-400">
                Your signed-in identity is restored through the authenticated session endpoint.
                State-changing authentication and assessment requests use CSRF protection.
              </p>
            </div>
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Email verification, two-factor authentication, last-login details, and password management are not exposed by the current account API.
          </p>
        </Card>
      </div>

      <div className="mt-5 grid items-stretch gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <Card className="p-5 sm:p-7">
          <SectionTitle
            icon="activity"
            title="Account activity"
            description="Personal assessment totals require assessment ownership data."
          />
          <div className="mt-6 flex items-start gap-4 rounded-xl border border-white/8 bg-white/[0.025] p-4 sm:p-5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-300/10 text-violet-200">
              <ProfilePageIcon name="activity" />
            </span>
            <div>
              <p className="font-semibold text-slate-100">Personal activity is unavailable</p>
              <p className="mt-1 text-sm leading-6 text-slate-400">
                The assessment records API does not associate assessments with a user. To avoid presenting global records as your personal activity, assessment totals and recent activity are not shown here.
              </p>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col p-5 sm:p-7">
          <SectionTitle
            icon="actions"
            title="Account actions"
            description="Manage your current application session."
          />
          <div className="mt-6 grid gap-3">
            <a
              href="/app"
              className="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.06] px-4 text-sm font-semibold text-cyan-100 transition-colors hover:bg-cyan-300/10"
            >
              Return to dashboard
              <ProfilePageIcon name="arrow" />
            </a>
            <button
              type="button"
              disabled={signingOut}
              onClick={() => void signOut()}
              className="flex min-h-12 items-center justify-between gap-3 rounded-xl border border-red-300/15 bg-red-300/[0.035] px-4 text-left text-sm font-semibold text-red-100 transition-colors hover:bg-red-300/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {signingOut ? "Signing out…" : "Sign out"}
              <ProfilePageIcon name="signout" />
            </button>
          </div>
          {logoutError && (
            <p role="alert" className="mt-3 text-sm leading-5 text-red-200">
              {logoutError}
            </p>
          )}
        </Card>
      </div>
    </>
  );
}

function ProfileInfo({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-white/8 bg-white/[0.025] p-4">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-2 break-words text-sm font-semibold text-slate-200">{value}</dd>
    </div>
  );
}

function SectionTitle({
  icon,
  title,
  description,
}: {
  icon: "identity" | "security" | "activity" | "actions";
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/8 bg-white/[0.035] text-cyan-200">
        <ProfilePageIcon name={icon} />
      </span>
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        <p className="mt-1 text-sm leading-5 text-slate-500">{description}</p>
      </div>
    </div>
  );
}

function ProfilePageIcon({
  name,
}: {
  name: "identity" | "security" | "activity" | "actions" | "lock" | "arrow" | "signout";
}) {
  const icons = {
    identity: <><circle cx="12" cy="8" r="3" /><path d="M5.5 19a6.5 6.5 0 0 1 13 0" /></>,
    security: <><path d="M12 3 19 6v5c0 4.4-2.8 8.1-7 10-4.2-1.9-7-5.6-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></>,
    activity: <><path d="M3 12h4l2.2-6 4.1 12 2.2-6H21" /></>,
    actions: <><circle cx="12" cy="12" r="8" /><path d="M12 8v8M8 12h8" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3M12 14v3" /></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    signout: <><path d="M10 5H5v14h5" /><path d="M14 8l4 4-4 4M18 12H9" /></>,
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className="h-5 w-5">
      <g stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        {icons[name]}
      </g>
    </svg>
  );
}
