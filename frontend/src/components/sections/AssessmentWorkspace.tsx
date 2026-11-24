import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  ApiError,
  createAssessment,
  getCsrfToken,
  getAppliedRecommendations,
  getAssessmentDetail,
  getAssessmentHistory,
  getAreas,
  getCities,
  getRecommendationRules,
  getWeather,
  type AppliedRecommendation,
  type Assessment,
  type Area,
  type City,
  type PaginatedResponse,
  type RecommendationRule,
  type WeatherResponse,
} from "../../services/api";
import { useAuth } from "../../auth/AuthContext";
import { Badge, Button, Card } from "../ui";

type LoadState<T> =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return error instanceof Error
    ? error.message
    : "The request could not be completed.";
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="mt-4 rounded-xl border border-red-300/20 bg-red-400/5 p-4"
    >
      <p className="text-sm leading-6 text-red-100">{message}</p>
      <Button
        variant="secondary"
        size="sm"
        className="mt-3"
        onClick={onRetry}
      >
        Retry
      </Button>
    </div>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <p role="status" className="mt-4 text-sm text-slate-400">
      {label}
    </p>
  );
}

function DataClassBadge({ dataClass }: { dataClass: string }) {
  const variant =
    dataClass === "illustrative"
      ? "orange"
      : dataClass === "unavailable"
        ? "neutral"
        : "cyan";
  return <Badge variant={variant}>Data class: {dataClass}</Badge>;
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card className="p-5 sm:p-6">
      <h3 className="hs-display text-xl font-semibold text-slate-100">{title}</h3>
      {description && (
        <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
      )}
      {children}
    </Card>
  );
}

function RecommendationList({
  recommendations,
}: {
  recommendations: AppliedRecommendation[];
}) {
  if (recommendations.length === 0) {
    return (
      <p className="mt-4 text-sm text-slate-400">
        No recommendations were applied to this assessment.
      </p>
    );
  }

  return (
    <ul className="mt-4 space-y-3">
      {recommendations.map((recommendation) => (
        <li
          key={recommendation.id}
          className="rounded-xl border border-white/8 bg-white/[0.025] p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-slate-100">
              {recommendation.title ?? recommendation.rule_code ?? "Applied recommendation"}
            </p>
            {recommendation.priority && (
              <Badge
                variant={
                  recommendation.priority === "high"
                    ? "red"
                    : recommendation.priority === "medium"
                      ? "orange"
                      : recommendation.priority === "low"
                        ? "cyan"
                        : "neutral"
                }
              >
                {recommendation.priority}
              </Badge>
            )}
            {recommendation.rule_version_applied && (
              <Badge variant="neutral">
                Version {recommendation.rule_version_applied}
              </Badge>
            )}
          </div>
          {recommendation.content_snapshot_available ? (
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {recommendation.recommendation_text ??
                "Snapshot text is unavailable."}
            </p>
          ) : (
            <p className="mt-2 text-sm leading-6 text-amber-200">
              Historical content snapshot unavailable; current rule text is not
              substituted.
            </p>
          )}
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Trigger: {recommendation.trigger_explanation}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function AssessmentWorkspace() {
  const { state: authState } = useAuth();
  const [cities, setCities] = useState<LoadState<City[]>>({ status: "loading" });
  const [citiesRetry, setCitiesRetry] = useState(0);
  const [selectedCityId, setSelectedCityId] = useState("");
  const [areas, setAreas] = useState<LoadState<Area[]>>({ status: "idle" });
  const [areasRetry, setAreasRetry] = useState(0);
  const [selectedAreaId, setSelectedAreaId] = useState("");
  const [weather, setWeather] = useState<LoadState<WeatherResponse>>({
    status: "idle",
  });
  const [weatherRetry, setWeatherRetry] = useState(0);
  const [rules, setRules] = useState<LoadState<RecommendationRule[]>>({
    status: "loading",
  });
  const [rulesRetry, setRulesRetry] = useState(0);
  const [history, setHistory] = useState<
    LoadState<PaginatedResponse<Assessment>>
  >({ status: "idle" });
  const [historyPage, setHistoryPage] = useState(1);
  const [historyRetry, setHistoryRetry] = useState(0);
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<
    number | null
  >(null);
  const [assessmentRetry, setAssessmentRetry] = useState(0);
  const [assessmentDetail, setAssessmentDetail] =
    useState<LoadState<Assessment>>({ status: "idle" });
  const [appliedRecommendations, setAppliedRecommendations] = useState<
    LoadState<AppliedRecommendation[]>
  >({ status: "idle" });
  const [source, setSource] = useState<"observations" | "demo">(
    "observations",
  );
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createIdempotencyKey, setCreateIdempotencyKey] = useState<
    string | null
  >(null);

  useEffect(() => {
    let active = true;
    setCities({ status: "loading" });
    getCities()
      .then((response) => {
        if (!active) return;
        setCities({ status: "success", data: response.results });
        setSelectedCityId((currentId) =>
          response.results.some((city) => String(city.id) === currentId)
            ? currentId
            : response.results[0]
              ? String(response.results[0].id)
              : "",
        );
      })
      .catch((error: unknown) => {
        if (active) setCities({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [citiesRetry]);

  useEffect(() => {
    if (!selectedCityId) {
      setAreas({ status: "success", data: [] });
      setSelectedAreaId("");
      return;
    }

    let active = true;
    setAreas({ status: "loading" });
    setSelectedAreaId("");
    getAreas(Number(selectedCityId))
      .then((response) => {
        if (!active) return;
        setAreas({ status: "success", data: response.results });
        setSelectedAreaId(response.results[0] ? String(response.results[0].id) : "");
      })
      .catch((error: unknown) => {
        if (active) setAreas({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [selectedCityId, areasRetry]);

  useEffect(() => {
    if (cities.status !== "success") return;
    const city = cities.data.find((item) => String(item.id) === selectedCityId);
    if (!city) {
      setWeather({ status: "idle" });
      return;
    }

    let active = true;
    setWeather({ status: "loading" });
    getWeather(city.name)
      .then((response) => {
        if (active) setWeather({ status: "success", data: response });
      })
      .catch((error: unknown) => {
        if (active) setWeather({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [cities, selectedCityId, weatherRetry]);

  useEffect(() => {
    let active = true;
    setRules({ status: "loading" });
    getRecommendationRules()
      .then((response) => {
        if (active) setRules({ status: "success", data: response.results });
      })
      .catch((error: unknown) => {
        if (active) setRules({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [rulesRetry]);

  useEffect(() => {
    if (!selectedAreaId) {
      setHistory({ status: "idle" });
      return;
    }

    let active = true;
    setHistory({ status: "loading" });
    getAssessmentHistory(Number(selectedAreaId), historyPage)
      .then((response) => {
        if (active) setHistory({ status: "success", data: response });
      })
      .catch((error: unknown) => {
        if (active) setHistory({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [selectedAreaId, historyPage, historyRetry]);

  useEffect(() => {
    if (selectedAssessmentId === null) {
      setAssessmentDetail({ status: "idle" });
      setAppliedRecommendations({ status: "idle" });
      return;
    }

    let active = true;
    setAssessmentDetail({ status: "loading" });
    setAppliedRecommendations({ status: "loading" });
    getAssessmentDetail(selectedAssessmentId)
      .then((detail) => {
        if (active) setAssessmentDetail({ status: "success", data: detail });
      })
      .catch((error: unknown) => {
        if (active) {
          setAssessmentDetail({ status: "error", message: getErrorMessage(error) });
        }
      });
    getAppliedRecommendations(selectedAssessmentId)
      .then((response) => {
        if (active) {
          setAppliedRecommendations({
            status: "success",
            data: response.results,
          });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setAppliedRecommendations({
            status: "error",
            message: getErrorMessage(error),
          });
        }
      });
    return () => {
      active = false;
    };
  }, [selectedAssessmentId, assessmentRetry]);

  const selectedArea =
    areas.status === "success"
      ? areas.data.find((area) => String(area.id) === selectedAreaId)
      : undefined;
  const selectedCity =
    cities.status === "success"
      ? cities.data.find((city) => String(city.id) === selectedCityId)
      : undefined;
  const demoAvailable =
    selectedArea?.area_type === "city" &&
    selectedCity?.name.toLowerCase() === "meerut";

  async function handleCreateAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authState.status !== "ready" || !authState.user) {
      setCreateError("Sign in before creating an assessment.");
      return;
    }
    if (!selectedAreaId) {
      setCreateError("Select an area before creating an assessment.");
      return;
    }

    setCreating(true);
    setCreateError(null);
    const idempotencyKey = createIdempotencyKey ?? crypto.randomUUID();
    setCreateIdempotencyKey(idempotencyKey);
    try {
      const { csrfToken } = await getCsrfToken();
      const created = await createAssessment(
        { area_id: Number(selectedAreaId), source },
        csrfToken,
        idempotencyKey,
      );
      setSelectedAssessmentId(created.id);
      setHistoryPage(1);
      setHistoryRetry((value) => value + 1);
      setCreateIdempotencyKey(null);
    } catch (error) {
      setCreateError(getErrorMessage(error));
    } finally {
      setCreating(false);
    }
  }

  return (
    <section id="live-data" className="border-y border-white/5 py-16 sm:py-20">
      <div className="hs-page">
        <div className="max-w-3xl">
          <p className="hs-eyebrow">Connected backend</p>
          <h2 className="hs-display mt-4 text-3xl font-bold text-slate-50 sm:text-5xl">
            Explore configured data and assessments
          </h2>
          <p className="mt-5 leading-7 text-slate-400">
            Values and availability below come from the configured backend. The
            demo weather provider is illustrative, not an observed or verified
            real-world measurement. Assessment scores are provisional and are
            shown with the backend&apos;s data class and warnings.
          </p>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-2">
          <SectionCard
            title="Configured location"
            description="Cities and areas are loaded from the backend catalogue; missing coordinates remain unspecified."
          >
            {cities.status === "loading" && (
              <LoadingState label="Loading configured cities…" />
            )}
            {cities.status === "error" && (
              <ErrorState
                message={cities.message}
                onRetry={() => setCitiesRetry((value) => value + 1)}
              />
            )}
            {cities.status === "success" && cities.data.length === 0 && (
              <p className="mt-4 text-sm text-slate-400">
                No active cities are configured.
              </p>
            )}
            {cities.status === "success" && cities.data.length > 0 && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-slate-300">
                  City
                  <select
                    value={selectedCityId}
                    onChange={(event) => {
                      setSelectedCityId(event.target.value);
                      setCreateIdempotencyKey(null);
                    }}
                    className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                  >
                    {cities.data.map((city) => (
                      <option key={city.id} value={city.id}>
                        {city.name}, {city.state_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-300">
                  Area
                  <select
                    value={selectedAreaId}
                    onChange={(event) => {
                      setSelectedAreaId(event.target.value);
                      setHistoryPage(1);
                      setSelectedAssessmentId(null);
                      setCreateIdempotencyKey(null);
                    }}
                    disabled={areas.status !== "success" || areas.data.length === 0}
                    className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100 disabled:opacity-60"
                  >
                    {areas.status === "success" && areas.data.length === 0 && (
                      <option value="">No areas configured</option>
                    )}
                    {areas.status === "success" &&
                      areas.data.map((area) => (
                        <option key={area.id} value={area.id}>
                          {area.area_name} ({area.area_type})
                        </option>
                      ))}
                  </select>
                </label>
                {areas.status === "loading" && (
                  <div className="sm:col-span-2">
                    <LoadingState label="Loading configured areas…" />
                  </div>
                )}
                {areas.status === "error" && (
                  <div className="sm:col-span-2">
                    <ErrorState
                      message={areas.message}
                      onRetry={() => setAreasRetry((value) => value + 1)}
                    />
                  </div>
                )}
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Weather provider response"
            description="Provider output is shown with its source, class, spatial resolution and quality status."
          >
            {weather.status === "idle" && (
              <p className="mt-4 text-sm text-slate-400">
                Select a configured city to request its provider response.
              </p>
            )}
            {weather.status === "loading" && (
              <LoadingState label="Requesting provider data…" />
            )}
            {weather.status === "error" && (
              <ErrorState
                message={weather.message}
                onRetry={() => setWeatherRetry((value) => value + 1)}
              />
            )}
            {weather.status === "success" && (
              <div className="mt-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <DataClassBadge dataClass={weather.data.data_class} />
                  <Badge variant="neutral">
                    {weather.data.quality_status}
                  </Badge>
                </div>
                {weather.data.data_class === "illustrative" && (
                  <p className="rounded-xl border border-orange-300/20 bg-orange-400/5 p-3 text-sm font-semibold leading-6 text-orange-100">
                    Illustrative demo data — not observed weather and not
                    verified real-world conditions.
                  </p>
                )}
                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-slate-500">Source</dt>
                    <dd className="mt-1 text-slate-200">{weather.data.source}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Location / resolution</dt>
                    <dd className="mt-1 text-slate-200">
                      {weather.data.location} · {weather.data.spatial_resolution}
                    </dd>
                  </div>
                  {weather.data.retrieved_at && (
                    <div className="sm:col-span-2">
                      <dt className="text-slate-500">Provider retrieval time</dt>
                      <dd className="mt-1 text-slate-200">
                        {weather.data.retrieved_at}
                      </dd>
                    </div>
                  )}
                </dl>
                {weather.data.observations.length > 0 ? (
                  <ul className="divide-y divide-white/8 rounded-xl border border-white/8">
                    {weather.data.observations.map((observation, index) => (
                      <li
                        key={`${observation.indicator_code}-${index}`}
                        className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5 text-sm"
                      >
                        <span className="text-slate-300">
                          {observation.indicator_code}
                        </span>
                        <span className="font-semibold text-slate-100">
                          {observation.value ?? "Unavailable"}{" "}
                          {observation.unit ?? ""}
                        </span>
                        <span className="w-full text-xs text-slate-500">
                          Period: {observation.measurement_period ?? "unspecified"}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">
                    The provider returned no observations.
                  </p>
                )}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <SectionCard
            title="Create assessment"
            description="Assessment creation uses your authenticated Django session and a CSRF-protected request."
          >
            {authState.status === "loading" && (
              <LoadingState label="Checking your sign-in session…" />
            )}
            {authState.status === "error" && (
              <p role="alert" className="mt-4 text-sm leading-6 text-red-200">
                {authState.message}
              </p>
            )}
            {authState.status === "ready" && !authState.user && (
              <div className="mt-4 space-y-3">
                <p className="text-sm leading-6 text-slate-300">
                  Sign in to your account to create an assessment. Assessment
                  history and public data remain available without signing in.
                </p>
                <a
                  href="/login?next=%2F%23live-data"
                  className="inline-flex min-h-11 items-center rounded-xl bg-gradient-to-r from-ultraviolet via-neon-fuchsia to-thermal-orange px-4 text-sm font-bold text-white"
                >
                  Sign in to create an assessment
                </a>
              </div>
            )}
            {authState.status === "ready" && authState.user && (
              <form onSubmit={handleCreateAssessment} className="mt-4 space-y-4">
                <p className="text-sm text-slate-400">
                  Signed in as{" "}
                  <span className="font-semibold text-slate-200">
                    {authState.user.username}
                  </span>
                </p>
              <label className="block text-sm font-medium text-slate-300">
                Assessment source
                <select
                  value={source}
                  onChange={(event) => {
                    setSource(
                      event.target.value === "demo"
                        ? "demo"
                        : "observations",
                    );
                    setCreateIdempotencyKey(null);
                  }}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                >
                  <option value="observations">Stored observations</option>
                  <option value="demo" disabled={!demoAvailable}>
                    Illustrative demo — Meerut city-level only
                  </option>
                </select>
              </label>
              {source === "demo" && (
                <p className="text-xs leading-5 text-orange-200">
                  Demo assessments are illustrative, city-level only and not
                  observed heat-risk measurements. The backend validates this
                  restriction independently.
                </p>
              )}
              {createError && (
                <p role="alert" className="text-sm leading-6 text-red-200">
                  {createError}
                </p>
              )}
              <Button
                type="submit"
                disabled={
                  creating ||
                  !selectedAreaId ||
                  (source === "demo" && !demoAvailable)
                }
              >
                {creating ? "Creating assessment…" : "Create assessment"}
              </Button>
              </form>
            )}
          </SectionCard>

          <SectionCard
            title="Assessment history"
            description="Read-only history is public in this MVP. Select a run to load its persisted detail and applied recommendation snapshots."
          >
            {history.status === "idle" && (
              <p className="mt-4 text-sm text-slate-400">
                Select an area to load its assessment history.
              </p>
            )}
            {history.status === "loading" && (
              <LoadingState label="Loading assessment history…" />
            )}
            {history.status === "error" && (
              <ErrorState
                message={history.message}
                onRetry={() => setHistoryRetry((value) => value + 1)}
              />
            )}
            {history.status === "success" &&
              (history.data.results.length === 0 ? (
                <p className="mt-4 text-sm text-slate-400">
                  No assessments are recorded for this area.
                </p>
              ) : (
                <>
                  <p className="mt-4 text-xs text-slate-500">
                    {history.data.count} assessment
                    {history.data.count === 1 ? "" : "s"} · page {historyPage}
                  </p>
                  <ul className="mt-3 space-y-2">
                    {history.data.results.map((assessment) => (
                      <li key={assessment.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedAssessmentId(assessment.id)}
                          aria-pressed={selectedAssessmentId === assessment.id}
                          className="flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.025] p-3 text-left hover:border-cyan-300/20"
                        >
                          <span>
                            <span className="block font-semibold text-slate-100">
                              Assessment #{assessment.id} · {assessment.status}
                            </span>
                            <span className="mt-1 block text-xs text-slate-500">
                              {assessment.run_at}
                            </span>
                          </span>
                          <DataClassBadge dataClass={assessment.data_class} />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 flex justify-between gap-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={!history.data.previous}
                      onClick={() => setHistoryPage((page) => Math.max(1, page - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={!history.data.next}
                      onClick={() => setHistoryPage((page) => page + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </>
              ))}
          </SectionCard>
        </div>

        {selectedAssessmentId !== null && (
          <div className="mt-4">
            <SectionCard title={`Assessment detail #${selectedAssessmentId}`}>
              {assessmentDetail.status === "loading" && (
                <LoadingState label="Loading persisted assessment detail…" />
              )}
              {assessmentDetail.status === "error" && (
                <ErrorState
                  message={assessmentDetail.message}
                  onRetry={() => setAssessmentRetry((value) => value + 1)}
                />
              )}
              {assessmentDetail.status === "success" && (
                <div className="mt-4 space-y-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <DataClassBadge
                      dataClass={assessmentDetail.data.data_class}
                    />
                    <Badge variant="neutral">
                      {assessmentDetail.data.status}
                    </Badge>
                    {assessmentDetail.data.category_is_provisional && (
                      <Badge variant="orange">Provisional category</Badge>
                    )}
                  </div>
                  {assessmentDetail.data.data_class === "illustrative" && (
                    <p className="rounded-xl border border-orange-300/20 bg-orange-400/5 p-3 text-sm font-semibold leading-6 text-orange-100">
                      Illustrative assessment — not a verified real-world
                      observation or validated scientific risk score.
                    </p>
                  )}
                  {assessmentDetail.data.data_class === "unavailable" && (
                    <p className="rounded-xl border border-white/10 bg-white/[0.025] p-3 text-sm leading-6 text-slate-300">
                      Assessment inputs are unavailable. No score has been
                      substituted for missing data.
                    </p>
                  )}
                  <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <dt className="text-xs text-slate-500">Area</dt>
                      <dd className="mt-1 text-sm text-slate-200">
                        {assessmentDetail.data.area.area_name},{" "}
                        {assessmentDetail.data.area.city_name}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Score</dt>
                      <dd className="mt-1 text-sm text-slate-200">
                        {assessmentDetail.data.score ?? "Not available"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Risk category</dt>
                      <dd className="mt-1 text-sm text-slate-200">
                        {assessmentDetail.data.risk_category ?? "Not available"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-slate-500">Data coverage</dt>
                      <dd className="mt-1 text-sm text-slate-200">
                        {assessmentDetail.data.data_coverage}%
                      </dd>
                    </div>
                  </dl>
                  <p className="text-xs leading-5 text-slate-500">
                    Method {assessmentDetail.data.method_version} · Configuration{" "}
                    {assessmentDetail.data.configuration_version} · Run{" "}
                    {assessmentDetail.data.run_at}
                  </p>
                  <div>
                    <h4 className="font-semibold text-slate-100">Indicators</h4>
                    {assessmentDetail.data.indicators.length === 0 ? (
                      <p className="mt-2 text-sm text-slate-400">
                        No indicators were available for this run.
                      </p>
                    ) : (
                      <ul className="mt-2 divide-y divide-white/8 rounded-xl border border-white/8">
                        {assessmentDetail.data.indicators.map((indicator) => (
                          <li
                            key={indicator.indicator_code}
                            className="grid gap-1 px-3 py-3 text-sm sm:grid-cols-[1fr_auto]"
                          >
                            <span className="font-medium text-slate-200">
                              {indicator.indicator_code}
                            </span>
                            <span className="text-slate-300">
                              {indicator.input_value_numeric ??
                                indicator.input_value_text ??
                                "Unavailable"}{" "}
                              · {indicator.quality_status}
                            </span>
                            <span className="text-xs leading-5 text-slate-500 sm:col-span-2">
                              {indicator.explanation}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  {assessmentDetail.data.warnings.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-slate-100">
                        Limitations and warnings
                      </h4>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-100">
                        {assessmentDetail.data.warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              <div className="mt-6 border-t border-white/8 pt-5">
                <h4 className="font-semibold text-slate-100">
                  Applied recommendations
                </h4>
                {appliedRecommendations.status === "loading" && (
                  <LoadingState label="Loading applied recommendation snapshots…" />
                )}
                {appliedRecommendations.status === "error" && (
                  <ErrorState
                    message={appliedRecommendations.message}
                    onRetry={() => setAssessmentRetry((value) => value + 1)}
                  />
                )}
                {appliedRecommendations.status === "success" && (
                  <RecommendationList
                    recommendations={appliedRecommendations.data}
                  />
                )}
              </div>
            </SectionCard>
          </div>
        )}

        <div className="mt-4">
          <SectionCard
            title="Active recommendation rules"
            description="Rules are fetched from the backend and are not represented as applied to an assessment unless returned by that assessment's recommendations endpoint."
          >
            {rules.status === "loading" && (
              <LoadingState label="Loading active recommendation rules…" />
            )}
            {rules.status === "error" && (
              <ErrorState
                message={rules.message}
                onRetry={() => setRulesRetry((value) => value + 1)}
              />
            )}
            {rules.status === "success" &&
              (rules.data.length === 0 ? (
                <p className="mt-4 text-sm text-slate-400">
                  No active recommendation rules are configured.
                </p>
              ) : (
                <ul className="mt-4 grid gap-3 md:grid-cols-2">
                  {rules.data.map((rule) => (
                    <li
                      key={rule.id}
                      className="rounded-xl border border-white/8 bg-white/[0.025] p-4"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-slate-100">
                          {rule.title}
                        </p>
                        <Badge variant="neutral">{rule.priority}</Badge>
                        <Badge variant="neutral">v{rule.version}</Badge>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-300">
                        {rule.recommendation_text}
                      </p>
                    </li>
                  ))}
                </ul>
              ))}
          </SectionCard>
        </div>
      </div>
    </section>
  );
}
