const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/+$/, "");

export interface HealthResponse {
  service: string;
  status: "ok" | "degraded";
  database: "ok" | "error";
}

export interface City {
  id: number;
  name: string;
  state_name: string;
  country_code: string;
  status: string;
}

export interface Area {
  id: number;
  city_id: number;
  city: City;
  area_code: string | null;
  area_name: string;
  area_type: string;
  latitude: number | null;
  longitude: number | null;
  assessment_ready?: boolean;
  is_assessment_ready?: boolean;
  readiness_status?: "READY" | "NOT_READY" | string;
  readiness_reasons?: string[];
  available_indicators?: string[];
  missing_indicators?: string[];
  latest_observation_period?: {
    start: string | null;
    end: string | null;
  } | null;
  observation_age_days?: number | null;
  max_observation_age_days?: number;
  freshness_status?: "FRESH" | "STALE" | "MISSING" | string;
  geometry_limitation?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface WeatherObservation {
  indicator_code: string;
  value: number | string | null;
  unit: string | null;
  measurement_period?: string | null;
}

export interface WeatherResponse {
  source: string;
  data_class: string;
  location: string;
  spatial_resolution: string;
  retrieved_at?: string;
  scenario_id?: string;
  scenario_name?: string;
  observations: WeatherObservation[];
  quality_status: string;
}

export interface AssessmentInputSnapshot {
  provider: string | null;
  data_class: string | null;
  location: string | null;
  spatial_resolution: string | null;
  retrieved_at: string | null;
  quality_status: string | null;
  scenario_id: string | null;
  scenario_name: string | null;
  observations: WeatherObservation[];
}

export interface AssessmentArea {
  id: number;
  area_name: string;
  area_type: string;
  city_name: string;
}

export interface AssessmentIndicator {
  indicator_code: string;
  input_value_numeric: string | null;
  input_value_text: string | null;
  normalized_value: string | null;
  weight_used: string | null;
  contribution: string | null;
  quality_status: string;
  explanation: string;
}

export interface AppliedRecommendation {
  id: number;
  rule_code: string | null;
  title: string | null;
  priority: string | null;
  recommendation_text: string | null;
  rule_version_applied: string | null;
  trigger_explanation: string;
  created_at: string;
  content_snapshot_available: boolean;
}

export interface Assessment {
  id: number;
  area: AssessmentArea;
  status: string;
  score_type: string;
  score: string | null;
  risk_category: string | null;
  category_is_provisional: boolean;
  data_coverage: string | null;
  data_class: string;
  method_version: string;
  configuration_version: string;
  configuration_snapshot: Record<string, unknown> & {
    input_snapshot?: AssessmentInputSnapshot;
  };
  run_at: string;
  indicators: AssessmentIndicator[];
  recommendations: AppliedRecommendation[];
  warnings: string[];
}

export interface DataSource {
  id: number;
  source_name: string;
  owner_name: string;
  approval_status: string;
  created_at: string;
  dataset_count: number;
}

export interface AdminDataSource extends DataSource {
  official_url: string | null;
  licence_terms: string | null;
}

export interface Dataset {
  id: number;
  dataset_name: string;
  source_name: string;
  data_class: string;
  spatial_resolution: string;
  published_at: string | null;
  coverage_start: string | null;
  coverage_end: string | null;
  retrieved_at: string;
  is_active: boolean;
}

export interface AdminDataset extends Dataset {
  source: number;
  source_approval_status: string;
  file_hash: string | null;
  transformation_notes: string | null;
}

export interface IndicatorObservation {
  id: number;
  area_name: string;
  city_name: string;
  dataset_name: string;
  data_class: string;
  indicator_code: string;
  period_start: string;
  period_end: string;
  raw_value_numeric: string | null;
  raw_value_text: string | null;
  raw_unit: string | null;
  quality_status: string;
}

export interface AdminIndicatorObservation extends IndicatorObservation {
  area: number;
  dataset: number;
  notes: string | null;
}

export interface InventoryFilters {
  search?: string;
  approval_status?: string;
  source_id?: number;
  data_class?: string;
  is_active?: boolean;
  area_id?: number;
  indicator_code?: string;
  dataset_id?: number;
  quality_status?: string;
  period_start?: string;
  period_end?: string;
}

export interface DataSourceWrite {
  source_name: string;
  owner_name: string;
  official_url: string | null;
  licence_terms: string | null;
  approval_status: "PENDING" | "APPROVED" | "REJECTED";
}

export interface DatasetWrite {
  source: number;
  dataset_name: string;
  data_class: "observed" | "derived" | "illustrative";
  spatial_resolution: string;
  published_at: string | null;
  coverage_start: string | null;
  coverage_end: string | null;
  retrieved_at: string;
  file_hash: string | null;
  transformation_notes: string | null;
  is_active: boolean;
}

export interface ObservationWrite {
  area: number;
  dataset: number;
  indicator_code: string;
  period_start: string;
  period_end: string;
  raw_value_numeric: string | null;
  raw_value_text: string | null;
  raw_unit: string | null;
  quality_status: string;
  notes: string | null;
}

export interface RecommendationRule {
  id: number;
  rule_code: string;
  title: string;
  condition_config: Record<string, unknown>;
  recommendation_text: string;
  priority: string;
  version: string;
}

export interface AppliedRecommendationsResponse {
  assessment_id: number;
  results: AppliedRecommendation[];
}

export interface AssessmentRequest {
  area_id: number;
  source: "observations" | "demo";
  scenario?: string;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: string;
}

interface CsrfResponse {
  csrfToken: string;
}

interface AuthResponse {
  user: AuthUser;
  csrfToken: string;
}

interface RegistrationResponse {
  user: AuthUser;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly code: string | null = null,
    readonly details: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function errorMessage(payload: unknown): string | null {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return isRecord(payload) && typeof payload.error === "string"
      ? payload.error
      : null;
  }
  return typeof payload.error.message === "string"
    ? payload.error.message
    : null;
}

function errorCode(payload: unknown): string | null {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return null;
  }
  return typeof payload.error.code === "string" ? payload.error.code : null;
}

function errorDetails(payload: unknown): unknown {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return isRecord(payload) ? payload : null;
  }
  return payload.error.details ?? null;
}

function httpErrorMessage(status: number, message: string | null): string {
  switch (status) {
    case 401:
      return "Authentication is required or the supplied credentials were rejected. Check your backend username and password.";
    case 403:
      return "The backend denied this request. Check account permissions and, if using a session, CSRF configuration.";
    case 404:
      return message ?? "The requested resource was not found.";
    case 422:
      return message
        ? `This assessment source or configuration is unavailable: ${message}`
        : "This assessment source or configuration is unavailable.";
    case 503:
      return message
        ? `The backend service is temporarily unavailable: ${message}`
        : "The backend service is temporarily unavailable. Please retry.";
    default:
      return message ?? `The backend returned HTTP ${status}.`;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      "Network request failed. Check that the backend is running, VITE_API_BASE_URL is correct, and the frontend origin is allowed by backend CORS.",
      null,
      "NETWORK_ERROR",
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    if (!response.ok) {
      throw new ApiError(
        httpErrorMessage(response.status, null),
        response.status,
      );
    }
    throw new ApiError(
      "The backend returned an invalid JSON response.",
      response.status,
      "INVALID_RESPONSE",
    );
  }

  if (!response.ok) {
    throw new ApiError(
      httpErrorMessage(response.status, errorMessage(payload)),
      response.status,
      errorCode(payload),
      errorDetails(payload),
    );
  }

  return payload as T;
}

function pageQuery(page: number, pageSize: number): string {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return `?${params.toString()}`;
}

async function getAllPages<T>(path: string): Promise<PaginatedResponse<T>> {
  const firstPage = await request<PaginatedResponse<T>>(
    `${path}${pageQuery(1, 100)}`,
  );
  const results = [...firstPage.results];
  let page = 1;
  let currentPage = firstPage;

  while (currentPage.next) {
    page += 1;
    currentPage = await request<PaginatedResponse<T>>(
      `${path}${pageQuery(page, 100)}`,
    );
    results.push(...currentPage.results);
  }

  return { ...firstPage, next: null, previous: null, results };
}

export function checkBackendHealth(): Promise<HealthResponse> {
  return request("/health/");
}

export function getCsrfToken(): Promise<CsrfResponse> {
  return request("/auth/csrf/");
}

export function login(
  username: string,
  password: string,
  csrfToken: string,
): Promise<AuthResponse> {
  return request("/auth/login/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ username, password }),
  });
}

export async function register(
  username: string,
  email: string,
  password: string,
  confirmPassword: string,
): Promise<RegistrationResponse> {
  const { csrfToken } = await getCsrfToken();
  return request("/auth/register/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      username,
      email,
      password,
      confirm_password: confirmPassword,
    }),
  });
}

export function getCurrentUser(): Promise<{ user: AuthUser }> {
  return request("/auth/me/");
}

export async function logout(csrfToken?: string): Promise<{ detail: string }> {
  const token = csrfToken ?? (await getCsrfToken()).csrfToken;
  return request("/auth/logout/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": token,
    },
    body: "{}",
  });
}

export function getCities(): Promise<PaginatedResponse<City>> {
  return getAllPages("/cities/");
}

export function getAreas(cityId: number): Promise<PaginatedResponse<Area>> {
  return getAllPages(`/cities/${cityId}/areas/`);
}

export function getArea(areaId: number): Promise<Area> {
  return request<Area>(`/areas/${areaId}/`);
}

export interface AreaComparisonResult {
  area: Area;
  latest_assessment: Assessment | null;
}

export interface AreaComparisonResponse {
  comparison_count: number;
  results: AreaComparisonResult[];
  vulnerability_ranking: {
    rank: number;
    area_id: number;
    area_name: string;
    score: string | null;
    risk_category: string | null;
  }[];
  caveats: string;
}

export function compareAreas(areaIds: number[]): Promise<AreaComparisonResponse> {
  const ids = areaIds.join(",");
  return request<AreaComparisonResponse>(`/areas/compare/?area_ids=${ids}`);
}

export function getWeather(
  location: string,
  scenario = "standard",
): Promise<WeatherResponse> {
  const params = new URLSearchParams({ location, scenario });
  return request(`/weather/?${params.toString()}`);
}

export function createAssessment(
  assessment: AssessmentRequest,
  csrfToken: string,
  idempotencyKey?: string,
): Promise<Assessment> {
  return request("/assessments/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    body: JSON.stringify(assessment),
  });
}

export function getAssessmentHistory(
  areaId: number,
  page = 1,
): Promise<PaginatedResponse<Assessment>> {
  const params = new URLSearchParams({
    area_id: String(areaId),
    page: String(page),
    page_size: "20",
  });
  return request(`/assessments/?${params.toString()}`);
}

export function getAssessments(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<Assessment>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  return request(`/assessments/?${params.toString()}`);
}

export function getAllAssessments(): Promise<PaginatedResponse<Assessment>> {
  return getAllPages("/assessments/");
}

export function getAssessmentDetail(
  assessmentId: number,
): Promise<Assessment> {
  return request(`/assessments/${assessmentId}/`);
}

export function getRecommendationRules(): Promise<{
  results: RecommendationRule[];
}> {
  return request("/assessments/recommendation-rules/");
}

export function getAppliedRecommendations(
  assessmentId: number,
): Promise<AppliedRecommendationsResponse> {
  return request(`/assessments/${assessmentId}/recommendations/`);
}

export function getAreaList(): Promise<PaginatedResponse<Area>> {
  return getAllPages("/areas/");
}

export function getDataSources(
  page = 1,
  pageSize = 20,
  filters: InventoryFilters = {},
): Promise<PaginatedResponse<DataSource>> {
  return request(`/data-sources/${inventoryQuery(page, pageSize, filters)}`);
}

export function getDatasets(
  page = 1,
  pageSize = 20,
  filters: InventoryFilters = {},
): Promise<PaginatedResponse<Dataset>> {
  return request(`/datasets/${inventoryQuery(page, pageSize, filters)}`);
}

export function getIndicatorObservations(
  page = 1,
  pageSize = 20,
  filters: InventoryFilters = {},
): Promise<PaginatedResponse<IndicatorObservation>> {
  return request(`/observations/${inventoryQuery(page, pageSize, filters)}`);
}

function inventoryQuery(
  page: number,
  pageSize: number,
  filters: InventoryFilters,
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  return `?${params.toString()}`;
}

export function getAdminDataSources(
  page = 1,
  filters: InventoryFilters = {},
  pageSize = 20,
) {
  return request<PaginatedResponse<AdminDataSource>>(
    `/admin/data-sources/${inventoryQuery(page, pageSize, filters)}`,
  );
}

export function getAdminDatasets(
  page = 1,
  filters: InventoryFilters = {},
  pageSize = 20,
) {
  return request<PaginatedResponse<AdminDataset>>(
    `/admin/datasets/${inventoryQuery(page, pageSize, filters)}`,
  );
}

export function getAdminObservations(
  page = 1,
  filters: InventoryFilters = {},
) {
  return request<PaginatedResponse<AdminIndicatorObservation>>(
    `/admin/observations/${inventoryQuery(page, 20, filters)}`,
  );
}

export function getAdminAreas() {
  return getAllPages<Area>("/admin/areas/");
}

export async function getAllAdminDataSources(filters: InventoryFilters = {}) {
  return getAllAdminPages<AdminDataSource>("/admin/data-sources/", filters);
}

export async function getAllAdminDatasets(filters: InventoryFilters = {}) {
  return getAllAdminPages<AdminDataset>("/admin/datasets/", filters);
}

async function getAllAdminPages<T>(
  path: string,
  filters: InventoryFilters,
): Promise<PaginatedResponse<T>> {
  const firstUrl = `${path}${inventoryQuery(1, 100, filters)}`;
  const firstPage = await request<PaginatedResponse<T>>(firstUrl);
  const results = [...firstPage.results];
  let page = 1;
  let currentPage = firstPage;
  while (currentPage.next) {
    page += 1;
    currentPage = await request<PaginatedResponse<T>>(
      `${path}${inventoryQuery(page, 100, filters)}`,
    );
    results.push(...currentPage.results);
  }
  return { ...firstPage, next: null, previous: null, results };
}

async function adminWrite<T>(
  path: string,
  method: "POST" | "PATCH",
  payload: unknown,
): Promise<T> {
  const { csrfToken } = await getCsrfToken();
  return request<T>(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(payload),
  });
}

export function saveAdminDataSource(
  payload: DataSourceWrite,
  id?: number,
) {
  return adminWrite<AdminDataSource>(
    id ? `/admin/data-sources/${id}/` : "/admin/data-sources/",
    id ? "PATCH" : "POST",
    payload,
  );
}

export function saveAdminDataset(payload: DatasetWrite, id?: number) {
  return adminWrite<AdminDataset>(
    id ? `/admin/datasets/${id}/` : "/admin/datasets/",
    id ? "PATCH" : "POST",
    payload,
  );
}

export function saveAdminObservation(
  payload: ObservationWrite,
  id?: number,
) {
  return adminWrite<AdminIndicatorObservation>(
    id ? `/admin/observations/${id}/` : "/admin/observations/",
    id ? "PATCH" : "POST",
    payload,
  );
}
