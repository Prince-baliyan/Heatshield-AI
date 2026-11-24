# HeatShield AI — API Specification

**Base path:** `/api/v1/`
**Style:** REST JSON
**Status:** Authentication, assessment, city, area and authenticated inventory listing endpoints below are implemented.

## 1. General conventions

- JSON request/response bodies.
- UTF-8 encoding.
- Use standard HTTP status codes.
- IDs are opaque numeric identifiers in the initial proposal.
- Dates use ISO 8601 (`YYYY-MM-DD`); timestamps use ISO 8601 with timezone.
- Do not expose stack traces, database credentials, or internal secrets.

## 2. Endpoints

### Student authentication

Public registration creates only a non-staff, non-superuser Django user and
assigns it to the server-managed `Student` group. The API rejects unrecognized
request fields, including attempts to submit `is_staff`, `is_superuser`, or
`role`. Usernames and email addresses are checked case-insensitively for
duplicates. Passwords are validated with Django's configured validators and
stored through Django's password-hashing API.

All mutation requests below require a CSRF token, including anonymous
registration and login. First request `GET /api/v1/auth/csrf/`, then submit its
`csrfToken` in the `X-CSRFToken` header. Keep the cookie set by that response.
After login, use the new `csrfToken` returned by login for subsequent
mutations. Session-authenticated requests must send cookies.

#### Browser client integration

Use the configured API base URL and include cookies on every auth request (and
on later session-authenticated requests):

```ts
const csrfResponse = await fetch(`${API_BASE_URL}/auth/csrf/`, {
  credentials: "include",
});
const { csrfToken } = await csrfResponse.json();

const loginResponse = await fetch(`${API_BASE_URL}/auth/login/`, {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken,
  },
  body: JSON.stringify({ username, password }),
});
const { user, csrfToken: rotatedCsrfToken } = await loginResponse.json();
```

Use the rotated token for logout and any later unsafe requests. Registration
uses the same CSRF retrieval and cookie/header pattern with the registration
request fields. Logout is a `POST` with an empty JSON body and the current
`X-CSRFToken`; it clears the session. `GET /auth/me/` also uses
`credentials: "include"` and requires no CSRF header. The frontend client
includes cookies for API requests, uses the session endpoints for sign-in and
sign-out, and sends a CSRF token with session-authenticated assessment creation.
Passwords remain in component memory only for the duration of the form request;
they are not persisted in browser storage.

Handle `401` as an absent/expired session or rejected login credentials (login
uses a generic message); an anonymous `/auth/me/` request returns
`AUTHENTICATION_REQUIRED`. A `403` on a mutation indicates a missing/invalid
CSRF token or a permission denial, not an invitation to disable CSRF. After
login, a `403` must be surfaced as a CSRF/configuration or authorization error.
For cross-origin browser deployments, configure exact frontend origins in both
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, and use
`credentials: "include"`.

#### `GET /api/v1/auth/csrf/`

Sets the CSRF cookie and returns a token:
```json
{
  "csrfToken": "masked-csrf-token"
}
```

#### `POST /api/v1/auth/register/`

Request:
```json
{
  "username": "student01",
  "email": "student@example.test",
  "password": "a-strong-password",
  "confirm_password": "a-strong-password"
}
```

Success (`201 Created`) returns only safe profile fields:
```json
{
  "user": {
    "id": 1,
    "username": "student01",
    "email": "student@example.test",
    "role": "student"
  }
}
```

Invalid fields return `400` with `error.code: "INVALID_REQUEST"` and field
details. Concurrent account conflicts return `409` with
`error.code: "ACCOUNT_CONFLICT"`. Registration is limited to 10 attempts per
hour per client address.

#### `POST /api/v1/auth/login/`

Request:
```json
{
  "username": "student01",
  "password": "a-strong-password"
}
```

Success establishes a Django session (`200 OK`) and returns the safe user
profile plus a rotated CSRF token:
```json
{
  "user": {
    "id": 1,
    "username": "student01",
    "email": "student@example.test",
    "role": "student"
  },
  "csrfToken": "rotated-masked-csrf-token"
}
```

Invalid credentials return the same `401` message regardless of whether the
username or password was incorrect. Login is limited to 5 attempts per minute
per client address. Throttling is backed by Django's configured cache; use a
shared production cache when running multiple application workers.

#### `POST /api/v1/auth/logout/`

Requires an authenticated session and `X-CSRFToken`. Returns `200` with
`{"detail": "Successfully logged out.", "csrfToken": "..."}` and destroys the
session. A subsequent current-user request returns `401`.

#### `GET /api/v1/auth/me/`

Requires an authenticated session. Returns the same safe profile shape under
`user`; anonymous requests return `401`. No password or password hash is
returned.

### `GET /api/v1/health/`

Returns public API and database connectivity status.

Success or degraded responses do not contain credentials or internal database details:
```json
{
  "service": "HeatShield AI API",
  "status": "ok",
  "database": "ok"
}
```

Database degradation returns HTTP `503` with `database: "error"`.

### `GET /api/v1/weather/`

Returns public weather-provider output for a location. The query parameter defaults
to `Meerut` when omitted. This endpoint does not create or persist observations or
assessments.

The configured demo provider explicitly labels data as illustrative:
```json
{
  "source": "HeatShield-AI Illustrative Demo Dataset",
  "data_class": "illustrative",
  "location": "Meerut",
  "spatial_resolution": "illustrative_city_level",
  "quality_status": "ILLUSTRATIVE_NOT_OBSERVED"
}
```

An unimplemented provider, including the currently unimplemented IMD provider,
returns HTTP `400` with an explanatory error; it must not return an assumed score
or observation.

### `GET /api/v1/cities/`

Returns configured cities using page-number pagination.

Example response:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Meerut",
      "state_name": "Uttar Pradesh",
      "country_code": "IN",
      "status": "ACTIVE"
    }
  ]
}
```

The default page size is 20; `page_size` may be set up to 100.

### `GET /api/v1/areas/`

Returns configured areas using page-number pagination. Optional `city_id` filters areas
by their parent city. An invalid `city_id` returns `400`; an unknown city ID with no
filter behavior is handled only by the city-specific endpoint below.

Example response:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "city_id": 1,
      "city": {
        "id": 1,
        "name": "Meerut",
        "state_name": "Uttar Pradesh",
        "country_code": "IN",
        "status": "ACTIVE"
      },
      "area_code": null,
      "area_name": "Meerut City",
      "area_type": "city",
      "latitude": "28.996330",
      "longitude": "77.706192",
      "assessment_ready": true,
      "is_assessment_ready": true,
      "readiness_status": "READY",
      "readiness_reasons": [],
      "available_indicators": ["AIR_TEMPERATURE", "RELATIVE_HUMIDITY"],
      "missing_indicators": [],
      "latest_observation_period": {
        "start": "2026-11-20",
        "end": "2026-11-20"
      },
      "observation_age_days": 4,
      "max_observation_age_days": 7,
      "freshness_status": "FRESH",
      "geometry_limitation": "Only a representative city-level point is available. Municipal or ward polygons are not stored and are not shown."
    }
  ]
}
```

Representative coordinates are documented populated-place points (e.g. OpenStreetMap Nominatim); polygons are not stored or invented.

### `GET /api/v1/areas/{area_id}/`

Returns a single area with its readiness status, reasons, and representative point coordinates. Returns `404` with code `AREA_NOT_FOUND` if the area does not exist.

### `GET /api/v1/cities/{city_id}/areas/`

Returns paginated areas belonging to an existing city. If the city exists but has no
areas, it returns an empty paginated result. An unknown city returns `404`.

Example response:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 101,
      "city_id": 1,
      "city": {
        "id": 1,
        "name": "Meerut",
        "state_name": "Uttar Pradesh",
        "country_code": "IN",
        "status": "ACTIVE"
      },
      "area_code": null,
      "area_name": "Meerut City",
      "area_type": "city",
      "latitude": null,
      "longitude": null
    }
  ]
}
```

Coordinates and names above are schema examples only, not real demo locations or verified measurements.

### Read-only data inventory

The following inventory endpoints require an authenticated Django session and
return page-number paginated results (default 20 records, maximum 100). They
are read-only. Responses omit internal or unneeded metadata such as source
URLs and licence text, dataset file hashes and transformation notes, and
observation notes.

- `GET /api/v1/data-sources/` returns source name, owner, approval status and
  creation timestamp.
- `GET /api/v1/datasets/` returns dataset name, source name, data class,
  spatial resolution, publication/coverage dates, retrieval timestamp and
  active status.
- `GET /api/v1/observations/` returns indicator, area/city, dataset, data
  class, measurement period, value/unit and quality status. Missing values
  remain null; numeric zero is preserved.

An empty result indicates no records are configured; the API does not seed or
generate inventory records.

### `POST /api/v1/assessments/`

Creates and persists a new assessment run. Each request creates a new run; previous runs are retained.
Authentication is required.

Request using the illustrative provider:
```json
{
  "area_id": 1,
  "source": "demo"
}
```

Request using the latest active stored observations:
```json
{
  "area_id": 1,
  "source": "observations"
}
```

`source` defaults to `observations`. The `demo` source is restricted to a city-level Meerut area, requires the configured provider to identify its data as both illustrative and city-level, and always returns an assessment marked `data_class: "illustrative"`. The server does not accept a client-supplied score. Observation assessments with no usable inputs persist and return `data_class: "unavailable"`.

Stored assessments select the latest observation per configured indicator from
active datasets with approved sources, excluding illustrative datasets. The
selected temperature and humidity periods must have identical start and end
dates; otherwise the run is `INSUFFICIENT_DATA`, with the period mismatch
persisted in its warnings. Observations older than `MAX_OBSERVATION_AGE_DAYS`
(default 7 days, measured from `period_end` to the current local date), future
periods, and incomplete periods do not contribute. Historical records can be
assessed by configuring an appropriate maximum age, but results remain tied to
their actual historical period.

Assessment creation supports an optional `Idempotency-Key` header. Keys are scoped to the authenticated user, compared case-insensitively, and must contain 1-128 URL-safe characters (`A-Z`, `a-z`, `0-9`, `.`, `_`, `~`, `:`, or `-`). The server fingerprints the validated request fields (`area_id` and `source`, including the default). A retry with the same key and payload returns the original assessment with `200` and `Idempotency-Replayed: true`; reusing the key with a different validated payload returns `409`. Run creation and key recording are atomic, and concurrent requests with the same user/key cannot create duplicate runs. Requests without the header retain the existing behavior and create a new run each time.

The response is the persisted assessment representation:
```json
{
  "id": 123,
  "area": {
    "id": 1,
    "area_name": "Meerut city level",
    "area_type": "city",
    "city_name": "Meerut"
  },
  "status": "SCORED",
  "score_type": "relative_heat_vulnerability_index",
  "score": "58.00",
  "risk_category": "illustrative_moderate",
  "category_is_provisional": true,
  "data_coverage": "100.00",
  "data_class": "illustrative",
  "method_version": "weighted-relative-index-v1",
  "configuration_version": "cfg-<configuration fingerprint>",
  "configuration_snapshot": {
    "configuration_version": "cfg-<configuration fingerprint>",
    "method_version": "weighted-relative-index-v1",
    "indicators": [],
    "minimum_coverage": "100.00",
    "category_thresholds": {},
    "normalization": "(value - lower_bound) / (upper_bound - lower_bound)",
    "rounding": "ROUND_HALF_UP"
  },
  "run_at": "2026-11-22T00:00:00Z",
  "indicators": [],
  "recommendations": [],
  "warnings": [
    "Illustrative demo inputs; this is not an observed weather assessment."
  ]
}
```

The example score is illustrative only, not a live result. The implemented provisional bounds, weights, category cut-offs, quality rules, and coverage requirement are documented in `RISK_SCORING.md`. A successful request with insufficient data still creates a run and returns `201` with `status: "INSUFFICIENT_DATA"`, `score: null`, and `risk_category: null`.

### `GET /api/v1/assessments/`

Returns assessment history using DRF page-number pagination. Optional `area_id` filters the results. The default page size is 20; `page_size` may be set up to 100. The response includes `count`, `next`, `previous`, and `results`.

### `GET /api/v1/assessments/{assessment_id}/`

Returns an assessment, its indicator breakdown, and recommendations.

### `GET /api/v1/areas/{area_id}/assessments/`

Returns assessment history for one area using the same page-number pagination (default 20, maximum 100).

### `GET /api/v1/areas/{area_id}/assessment/`

Returns the latest assessment for one area; returns `404` when the area or assessment does not exist.

### `GET /api/v1/assessments/{assessment_id}/recommendations/`

Returns recommendations for one assessment, including the rule code, title, text, priority, applied version, and trigger explanation captured when the recommendation was created. Historical records created before snapshots were introduced have `content_snapshot_available: false` and null snapshot content; the current mutable rule is not substituted.

### `GET /api/v1/areas/compare/`

Compares multiple configured areas by ID. Accepts comma-separated `area_ids` or multiple `area_id` parameters (e.g. `?area_ids=1,2`). Requires at least two distinct valid area IDs. Returns area metadata, representative coordinates, readiness status, latest assessment summary (scoped to the authenticated user), and relative vulnerability ranking.

### `GET /api/v1/assessments/{assessment_id}/export/`

Exports an assessment report in CSV or printable HTML format. Requires authentication and user ownership of the assessment. Query parameter `format`:
- `csv` (default): returns a downloadable CSV file (`text/csv`) with assessment metadata, indicator breakdown, recommendations, and limitations.
- `html` (or `pdf`): returns a printable HTML report (`text/html`) with print styling (`@media print`) suitable for browser PDF export.

### `GET /api/v1/assessments/recommendation-rules/`

Returns active recommendation rules. The repeatable backend setup command
`python manage.py setup_recommendation_rules` creates the demonstration rule set
without changing rules already present.

## 3. Error response shape

Use a consistent structure:
```json
{
  "error": {
    "code": "INSUFFICIENT_DATA",
    "message": "There is not enough validated data to calculate this assessment."
  }
}
```

Expected statuses:
- `200` — an assessment creation request replayed the stored result for the same idempotency key and payload.
- `400` — invalid query or request.
- `409` — an idempotency key was reused with a different validated payload.
- `404` — city or area not found.
- `401` — unauthenticated assessment write.
- `422` — requested assessment source or configuration is unavailable.
- `503` — database error while handling an assessment API request.
- `500` — unexpected server error; internal details are not returned.
- `201` — a run was created, including when its status is `INSUFFICIENT_DATA`.

## 4. Query and validation rules

- City and area listing endpoints above are implemented and public read-only APIs.
- Data inventory list endpoints are implemented, read-only and require an
  authenticated session.
- `area_id` must exist.
- Demo assessment requires a city-level Meerut area.
- Do not accept client-submitted scores as authoritative.
- The backend calculates or retrieves scores from validated server-side inputs.
- If required indicators are missing, return `insufficient_data`; do not substitute zero.
- Include source/data-class warnings in the response.
- Observation writes accept only supported indicator/unit pairs, require numeric values for scoring indicators, enforce active datasets with approved sources and compatible city/ward resolution, and reject duplicate natural keys (`area`, `dataset`, `indicator`, start date, end date).
- Stored observations must belong to active datasets and approved sources. The latest record per configured indicator is selected; periods must match exactly, and stale, future, incomplete, non-`VALID`, or illustrative dataset records cannot contribute. `LOW_CONFIDENCE` illustrative inputs remain limited to the separate demo provider path.

## 5. CORS and security

- Restrict allowed origins to configured frontend origins.
- Browser clients must send cookies (`credentials: "include"` for cross-origin
  fetches) and send `X-CSRFToken` for registration, login, logout, and
  session-authenticated assessment creation.
- Configure exact frontend origins in both `CORS_ALLOWED_ORIGINS` and
  `CSRF_TRUSTED_ORIGINS`; credentialed CORS must never use wildcard origins.
- Secure session/CSRF cookies default on when `DJANGO_DEBUG=False`. Use HTTPS
  in production and configure `DJANGO_SECURE_SSL_REDIRECT`, HSTS,
  `SameSite`, and trusted proxy behavior for the deployment.
- Login and registration throttles use the Django cache. A shared cache is
  required for consistent limits across multiple workers.
- Assessment creation requires authentication; assessment reads are available without authentication.
- The assessment model has no owner/user relationship, so assessment history and detail are intentionally public in the current MVP. It must not be used to store or expose sensitive individual data.
- City, area, health and weather-provider read endpoints are public.
- Data source, dataset and indicator-observation inventory endpoints require
  an authenticated session and expose only explicitly selected metadata.
- Basic and session authentication require deployment over HTTPS. Configure secure cookies and HSTS through the documented environment settings before production use.
- Keep API secrets server-side.
- Validate all path and query parameters.
- City, area and inventory list endpoints use page-number pagination, even for the small demo catalogue.

## 6. Endpoints deferred

Not implemented:
- `POST /api/v1/areas/` — admin area creation.
- `POST /api/v1/data-imports/` — direct raw upload import.

## 7. Contract change rule

If response fields change, update this file first, then backend serializers/views, frontend API client/types, and API tests. Do not independently invent field names in frontend and backend.
