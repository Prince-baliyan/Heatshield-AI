import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  ApiError,
  createAssessment,
  getAreas,
  getCities,
  getCsrfToken,
  getWeather,
  type Assessment,
  type Area,
  type City,
  type WeatherResponse,
} from "../services/api";
import { Badge, Button, Card } from "../components/ui";
import { AssessmentAnalytics } from "./AssessmentAnalytics";
import {
  EmptyState,
  ErrorPanel,
  formatDate,
  LoadingPanel,
  PageHeading,
} from "./AppUI";

const DEMO_SCENARIOS = [
  { id: "hot_dry", name: "Hot and dry" },
  { id: "hot_humid", name: "Hot and humid" },
  { id: "moderate", name: "Moderate conditions" },
  { id: "heavy_rainfall", name: "Heavy rainfall illustration" },
] as const;

type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; data: T };

function getErrorMessage(error: unknown) {
  return error instanceof ApiError || error instanceof Error
    ? error.message
    : "The request could not be completed.";
}

function ProviderMetricIcon({ name }: { name: "temperature" | "humidity" | "rainfall" | "source" | "time" | "class" }) {
  const icon = {
    temperature: <><path d="M14 14.76V5a2 2 0 0 0-4 0v9.76a4 4 0 1 0 4 0Z" /><path d="M12 9v8" /></>,
    humidity: <><path d="M12 3.5S5 11 5 15a7 7 0 0 0 14 0c0-4-7-11.5-7-11.5Z" /><path d="M9 16a3 3 0 0 0 3 3" /></>,
    rainfall: <><path d="M20 16.2A4.5 4.5 0 0 0 18 7.7a6 6 0 0 0-11.5 1.8A3.5 3.5 0 0 0 7 16.4" /><path d="m8 19 1-2m4 2 1-2m4 2 1-2" /></>,
    source: <><path d="M4 7h16M4 12h16M4 17h10" /><circle cx="18" cy="17" r="2" /></>,
    time: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    class: <><path d="M12 3 4.5 7v5c0 4.5 3.2 7.5 7.5 9 4.3-1.5 7.5-4.5 7.5-9V7L12 3Z" /><path d="m9 12 2 2 4-4" /></>,
  }[name];
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-4 w-4">{icon}</svg>;
}

function ProviderPreview({
  weather,
  source,
  scenario,
  onScenarioChange,
}: {
  weather: LoadState<WeatherResponse | null>;
  source: "demo" | "observations";
  scenario: string;
  onScenarioChange: (scenario: string) => void;
}) {
  const data = weather.status === "ready" ? weather.data : null;
  const scenarioName = DEMO_SCENARIOS.find((item) => item.id === scenario)?.name ?? "Illustrative scenario";
  const status = source === "observations"
    ? "Not used"
    : weather.status === "loading"
      ? "Loading"
      : weather.status === "error"
        ? "Unavailable"
        : "Illustrative";
  const observation = (code: string) => data?.observations.find((item) => item.indicator_code === code);
  const value = (code: string) => observation(code)?.value ?? "Unavailable";
  const unit = (code: string, fallback: string) => observation(code)?.unit ?? fallback;
  const metrics = [
    { label: "Air temperature", value: value("AIR_TEMPERATURE"), unit: unit("AIR_TEMPERATURE", "°C"), icon: "temperature" as const },
    { label: "Relative humidity", value: value("RELATIVE_HUMIDITY"), unit: unit("RELATIVE_HUMIDITY", "%"), icon: "humidity" as const },
    { label: "Rainfall", value: value("RAINFALL_24H"), unit: unit("RAINFALL_24H", "mm"), icon: "rainfall" as const },
  ];

  return (
    <details className="provider-preview mt-6 rounded-xl border border-white/[0.09] bg-white/[0.025]">
      <summary className="flex min-h-[4.25rem] cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300">
        <span className="min-w-0">
          <span className="block font-semibold text-slate-100">Provider data preview</span>
          <span className="mt-1 block truncate text-xs text-slate-500">
            {source === "observations" ? "Stored-observation mode · demo values are not used" : data?.source ?? scenarioName}
          </span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <Badge variant={source === "observations" ? "neutral" : status === "Unavailable" ? "orange" : "cyan"}>{status}</Badge>
          <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" className="provider-preview-chevron h-4 w-4 text-slate-400"><path d="m5 7.5 5 5 5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </span>
      </summary>
      <div className="space-y-4 border-t border-white/[0.07] p-4">
        {source === "observations" ? (
          <p className="text-sm leading-6 text-slate-400">
            This assessment will use stored observations only. No provider or demo values will be substituted.
          </p>
        ) : (
          <>
            <label className="block text-sm text-slate-300">
              Synthetic demo scenario
              <select
                value={scenario}
                onChange={(event) => onScenarioChange(event.target.value)}
                className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
              >
                {DEMO_SCENARIOS.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
            {weather.status === "loading" && <p role="status" className="text-sm text-slate-400">Loading selected scenario preview…</p>}
            {weather.status === "error" && <p role="alert" className="text-sm text-red-200">{getErrorMessage(weather.error)}</p>}
            {data && (
              <>
                <div className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
                  {metrics.map((metric) => (
                    <div key={metric.label} className="rounded-lg border border-white/[0.07] bg-slate-950/40 p-3">
                      <div className="flex items-center gap-2 text-cyan-200"><ProviderMetricIcon name={metric.icon} /><span className="text-xs text-slate-400">{metric.label}</span></div>
                      <p className="mt-2 text-lg font-semibold text-slate-100">
                        {metric.value === "Unavailable" ? "Unavailable" : `${metric.value} ${metric.unit}`}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <ProviderMetadata icon="source" label="Provider/source" value={data.source} />
                  <ProviderMetadata icon="time" label="Retrieved" value={data.retrieved_at ? formatDate(data.retrieved_at) : "Unavailable"} />
                  <ProviderMetadata icon="class" label="Data classification" value={data.data_class.replaceAll("_", " ")} />
                </div>
                <p className="text-xs leading-5 text-slate-400">Illustrative scenario values; not measured observations.</p>
              </>
            )}
          </>
        )}
      </div>
    </details>
  );
}

function ProviderMetadata({
  icon,
  label,
  value,
}: {
  icon: "source" | "time" | "class";
  label: string;
  value: string;
}) {
  return (
    <div className="flex min-w-0 items-start gap-2 rounded-lg border border-white/[0.06] px-3 py-2.5">
      <span className="mt-0.5 shrink-0 text-slate-500"><ProviderMetricIcon name={icon} /></span>
      <span className="min-w-0">
        <span className="block text-[11px] text-slate-500">{label}</span>
        <span className="mt-1 block break-words text-xs text-slate-300">{value}</span>
      </span>
    </div>
  );
}

export function AssessmentCreatePage() {
  const { state: auth } = useAuth();
  const [cities, setCities] = useState<LoadState<City[]>>({ status: "loading" });
  const [areas, setAreas] = useState<LoadState<Area[]>>({ status: "loading" });
  const [cityId, setCityId] = useState("");
  const [areaId, setAreaId] = useState("");
  const [weather, setWeather] = useState<LoadState<WeatherResponse | null>>({
    status: "loading",
  });
  const [source, setSource] = useState<"demo" | "observations">("demo");
  const [scenario, setScenario] = useState("moderate");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Assessment | null>(null);
  const [resultSource, setResultSource] = useState<"demo" | "observations">("demo");

  useEffect(() => {
    let active = true;
    getCities()
      .then((response) => {
        if (!active) return;
        setCities({ status: "ready", data: response.results });
        setCityId(response.results[0] ? String(response.results[0].id) : "");
      })
      .catch((requestError: unknown) => {
        if (active) setCities({ status: "error", error: requestError });
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!cityId) {
      setAreas({ status: "ready", data: [] });
      setAreaId("");
      return;
    }
    let active = true;
    setAreas({ status: "loading" });
    getAreas(Number(cityId))
      .then((response) => {
        if (!active) return;
        setAreas({ status: "ready", data: response.results });
        setAreaId(response.results[0] ? String(response.results[0].id) : "");
      })
      .catch((requestError: unknown) => {
        if (active) setAreas({ status: "error", error: requestError });
      });
    return () => {
      active = false;
    };
  }, [cityId]);

  useEffect(() => {
    if (source !== "demo" || cities.status !== "ready" || !cityId) {
      setWeather({ status: "ready", data: null });
      return;
    }
    const city = cities.data.find((item) => String(item.id) === cityId);
    if (!city) return;
    let active = true;
    setWeather({ status: "loading" });
    getWeather(city.name, scenario)
      .then((response) => {
        if (active) setWeather({ status: "ready", data: response });
      })
      .catch((requestError: unknown) => {
        if (active) setWeather({ status: "error", error: requestError });
      });
    return () => {
      active = false;
    };
  }, [cities, cityId, scenario, source]);

  const city = cities.status === "ready"
    ? cities.data.find((item) => String(item.id) === cityId)
    : undefined;
  const selectedArea = areas.status === "ready"
    ? areas.data.find((item) => String(item.id) === areaId)
    : undefined;
  const demoAllowed =
    city?.name.toLowerCase() === "meerut" && selectedArea?.area_type === "city";

  async function submitAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (auth.status !== "ready" || !auth.user) {
      setError("Your session is unavailable. Sign in again to create an assessment.");
      return;
    }
    if (!areaId) {
      setError("Select an available area.");
      return;
    }
    if (
      source === "demo" &&
      (weather.status !== "ready" ||
        weather.data?.scenario_id !== scenario)
    ) {
      setError("Wait for the selected illustrative scenario preview to finish loading.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { csrfToken } = await getCsrfToken();
      const assessment = await createAssessment(
        {
          area_id: Number(areaId),
          source,
          ...(source === "demo" ? { scenario } : {}),
        },
        csrfToken,
        crypto.randomUUID(),
      );
      setResult(assessment);
      setResultSource(source);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeading
        title="Create assessment"
        description="Review the configured provider response, then request an assessment from the backend. No result is estimated in the browser."
      />
      {cities.status === "loading" || areas.status === "loading" ? (
        <LoadingPanel label="Loading available cities and areas…" />
      ) : cities.status === "error" ? (
        <ErrorPanel error={cities.error} />
      ) : areas.status === "error" ? (
        <ErrorPanel error={areas.error} />
      ) : cities.data.length === 0 || areas.data.length === 0 ? (
        <EmptyState
          title="No assessment location is available"
          detail="The backend returned no active cities or analysis areas."
        />
      ) : (
        <div className="assessment-workspace-grid grid min-w-0 gap-5 xl:grid-cols-[minmax(19rem,0.8fr)_minmax(0,1.2fr)]">
          <Card className="assessment-form-panel min-w-0 p-5 sm:p-6">
            <h2 className="font-semibold text-white">1. Choose a location</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
              <label className="text-sm text-slate-300">
                City
                <select
                  value={cityId}
                  onChange={(event) => {
                    setCityId(event.target.value);
                    setResult(null);
                  }}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                >
                  {cities.data.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}, {item.state_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Area
                <select
                  value={areaId}
                  onChange={(event) => {
                    setAreaId(event.target.value);
                    setResult(null);
                  }}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                >
                  {areas.data.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.area_name} ({item.area_type})
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <ProviderPreview
              weather={weather}
              source={source}
              scenario={scenario}
              onScenarioChange={(nextScenario) => {
                setScenario(nextScenario);
                setResult(null);
              }}
            />
            <h2 className="mt-7 font-semibold text-white">3. Submit to the backend</h2>
            <form onSubmit={submitAssessment} className="mt-3 space-y-4">
              <label className="block text-sm text-slate-300">
                Assessment input source
                <select
                  value={source}
                  onChange={(event) => {
                    setSource(event.target.value === "demo" ? "demo" : "observations");
                    setResult(null);
                  }}
                  className="mt-2 min-h-11 w-full rounded-xl border border-white/10 bg-slate-950 px-3 text-slate-100"
                >
                  <option value="demo" disabled={!demoAllowed}>
                    Illustrative demo (Meerut city-level only)
                  </option>
                  <option value="observations">Stored observations</option>
                </select>
              </label>
              {error && <p role="alert" className="text-sm text-red-200">{error}</p>}
              <Button
                type="submit"
                disabled={
                  loading ||
                  !areaId ||
                  (source === "demo" &&
                    (!demoAllowed ||
                      weather.status !== "ready" ||
                      weather.data?.scenario_id !== scenario))
                }
              >
                {loading ? "Creating assessment…" : "Create assessment"}
              </Button>
            </form>
          </Card>
          <div
            className="assessment-result-scroll min-w-0"
            tabIndex={0}
            role="region"
            aria-label="Assessment result dashboard"
          >
            {loading ? (
              <LoadingPanel label="Creating and saving assessment…" />
            ) : result ? (
              <AssessmentAnalytics
                assessment={result}
                source={resultSource}
              />
            ) : (
              <EmptyState
                title="Assessment result will appear here"
                detail="The result panel is populated only from the assessment API response after submission."
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
