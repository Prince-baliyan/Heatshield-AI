# Data Dictionary

**Status:** Candidate schema and indicator catalogue — validate before implementation.
**Rule:** A field in this dictionary is not evidence that a real dataset exists. Units, ranges, and directionality must be checked against the actual source.

## 1. Conventions

- Use stable `snake_case` names.
- Store dates/times with explicit timezone handling; use UTC for ingestion timestamps.
- Preserve original source values and units in raw records.
- Store normalized values separately from raw values.
- Use `NULL` for unknown, unavailable, or not applicable values. Never convert missing values to zero.
- Every observation should be traceable to a `dataset_id` and source provenance.
- Record spatial unit type and identifier; do not assume ward boundaries align across datasets.
- Use explicit quality/status fields rather than encoding quality in the numeric value.
- Use `area_type="city"` for city-wide analysis units and `area_type="ward"` only for verified wards. Never attach city-level observations to a ward area.
- Geometry remains deferred for the MVP; it is not represented by ordinary text or MySQL spatial types until its format and coordinate reference system are approved.

## 2. Core data entities

| Entity | Candidate fields | Purpose |
|---|---|---|
| City | `id`, `name` (required), `state_name` (required), `country_code` (required), `status` (required), `created_at` (required) | Configurable city registry |
| Area | `id`, `city_id` (required), `area_code` (optional), `area_name` (required), `area_type` (`city` or verified `ward`), `latitude` (optional), `longitude` (optional), geometry (deferred), `created_at` (required) | Analysis unit with optional representative coordinates; geometry is not stored until its format and CRS are approved |
| Data source | `id`, `source_name` (required), `owner_name` (required), `official_url` (optional), `licence_terms` (optional), `approval_status` (required), `created_at` (required) | Source identity, ownership, licence, and access approval evidence |
| Dataset | `id`, `source_id` (required), `dataset_name` (required), `data_class` (required), `spatial_resolution` (required), `published_at` (optional), `coverage_start` (optional), `coverage_end` (optional), `retrieved_at` (required), `file_hash` (optional), `transformation_notes` (optional), `is_active` (required) | Dataset metadata and provenance |
| Indicator observation | `id`, `area_id` (required), `dataset_id` (required), `indicator_code` (required), `period_start` (required), `period_end` (required), `raw_value_numeric` (optional), `raw_value_text` (optional), `raw_unit` (optional), `quality_status` (required), `notes` (optional) | Original observed input for an area and time period |
| Assessment run | `id`, `area_id` (required), `method_version` (required), `configuration_version` (required), `configuration_snapshot` (optional for legacy runs; stored for new runs), `score` (optional), `risk_category` (optional), `data_coverage` (optional), `data_class` (`observed`, `derived`, `illustrative`, `mixed`, or `unavailable`), `status` (required), `run_at` (required) | Reproducible assessment execution for one area; unavailable means no eligible inputs were used |
| Assessment indicator | `id`, `assessment_run_id` (required), `indicator_code` (required), `input_value_numeric` (optional), `input_value_text` (optional), `normalized_value` (optional), `weight_used` (optional), `contribution` (optional), `quality_status` (required), `explanation` (required when used) | Explainable score breakdown for one assessment run |
| Recommendation rule | `id`, `rule_code` (required), `title` (required), `condition_config` (required), `recommendation_text` (required), `priority` (required), `version` (required), `is_active` (required) | Curated, versioned decision-support rules |
| Assessment recommendation | `id`, `assessment_run_id` (required), `recommendation_rule_id` (required), `rule_version_applied` (required), `rule_snapshot` (optional for legacy rows; stored for new rows), `trigger_explanation` (optional), `created_at` (required) | Records which recommendation rules were triggered and preserves their applied content |
| Assessment idempotency record | `id`, `user_id` (required), `key` (required, max 128), `request_fingerprint` (required SHA-256), `assessment_run_id` (required, one-to-one) | Binds an authenticated user's retry key and validated request payload to the resulting assessment |

These are logical entities. Final columns, constraints, geometry type, and indexes are to be decided in the database design and implementation phases.

### Provisional assessment configuration implemented for the MVP

The current deterministic configuration supports `AIR_TEMPERATURE` in `degree_celsius` with provisional bounds 25–45 and weight 0.70, and `RELATIVE_HUMIDITY` in `percent` with provisional bounds 30–90 and weight 0.30. In the stored observation pipeline, `AIR_TEMPERATURE` maps to Open-Meteo `temperature_2m_mean` (daily 24-hour mean temperature). Crucially, the 25–45 °C bounds have not been scientifically validated for daily mean temperature; winter observations below 25 °C are rejected as invalid, safely producing `INSUFFICIENT_DATA`. Both use direct normalization `(value - lower_bound) / (upper_bound - lower_bound)`. Out-of-bound inputs are marked invalid, not clipped. A score requires 100% of configured weight; otherwise status is `INSUFFICIENT_DATA` and score/category remain null. These bounds, weights, minimum coverage, and categories are demonstration assumptions, not scientifically validated thresholds. See `RISK_SCORING.md`.

Each new assessment stores the exact provisional scoring configuration as JSON; older assessment rows may have a null snapshot. New assessment recommendations store the rule code, title, recommendation text, priority, and version as applied. Older recommendation rows remain without snapshots and must not be presented using the current mutable rule content. When no eligible inputs are used, persist `data_class="unavailable"`.

Idempotency keys are scoped to the authenticated user, normalized case-insensitively, and limited to 1-128 URL-safe characters. The request fingerprint covers the validated `area_id` and `source` fields, including the default source.

For recommendation rules, `condition_config` must be a non-empty object with one `all` or `any` array. Conditions contain exactly `field`, `operator`, and `value`. Supported fields are `score`, `data_coverage`, `risk_category`, `data_class`, `status`, and `indicators.<UPPERCASE_CODE>.normalized_value` / `.quality_status`. Supported operators are `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, and `in`. Invalid active rules are skipped with a server log warning; rule JSON is never evaluated as Python code.

## 3. Candidate indicator catalogue

All entries below are `CANDIDATE / TO_VALIDATE`. Include an indicator in the MVP only if a real source, definition, geography, unit, and direction are verified.

| Code | Candidate indicator | Meaning / definition required | Unit | Expected direction for vulnerability | Validation notes |
|---|---|---|---|---|---|
| `HEAT_EXPOSURE` | Heat exposure proxy | Must specify whether this is air temperature, land-surface temperature, heat-day count, or another measure; these are not interchangeable | Source-defined | Usually higher = greater exposure | Do not label satellite land-surface temperature as air temperature |
| `VEGETATION` | Vegetation / green cover proxy | Define metric, class, season, resolution, and calculation method | Source-defined, e.g. index or % | Lower vegetation may indicate higher vulnerability | Verify seasonal effects and cloud/no-data handling |
| `BUILT_DENSITY` | Built-up intensity proxy | Define built-up fraction, building density, impervious surface, or other exact measure | Source-defined | Potentially higher = greater exposure | Do not conflate built-up density with population density |
| `POPULATION_DENSITY` | Population density | Population divided by a defined area, with source vintage and denominator stated | persons/km², if supported | Potentially higher = greater exposure | Census geography and boundary alignment must be checked |
| `SOCIAL_SENSITIVITY` | Social sensitivity proxy | Only use a defensible, documented variable with a clear definition | Source-defined | Depends on variable | Do not infer personal vulnerability from unsupported demographic assumptions |
| `PUBLIC_FACILITY_ACCESS` | Access to selected public services | Define facility types, distance/network method, and completeness of facility inventory | metres / minutes / index | Lower access may indicate lower response capacity | Missing facility records do not prove facilities are absent |
| `WATER_ACCESS_PROXY` | Water access proxy | Exact source and definition required; distinguish household access from mapped water points | Source-defined | Lower access may increase sensitivity | Do not use an unverified proxy as a direct household fact |

Do not automatically include every candidate. A smaller set of well-supported indicators is preferable to a larger set of weak proxies.

## 4. Required observation fields

| Field | Type (logical) | Required? | Notes |
|---|---|---:|---|
| `area_id` | Identifier | Yes | Must refer to a registered analysis unit |
| `dataset_id` | Identifier | Yes | Must refer to a verified dataset record |
| `indicator_code` | String / enum | Yes | Must exist in the approved indicator catalogue |
| `period_start`, `period_end` | Date/time | Conditional | Required for time-based measures; document snapshot measures |
| `raw_value` | Numeric or typed value | Conditional | Null when unavailable; do not invent |
| `raw_unit` | String | Conditional | Preserve source unit |
| `normalized_value` | Decimal | Conditional | Only generated by a versioned method |
| `quality_status` | Enum | Yes | See statuses below |
| `quality_note` | Text | No | Explain exclusions, uncertainty, or transformations |

## 5. Quality statuses

- `VALID`: passed defined validation checks.
- `MISSING`: expected value is unavailable.
- `INVALID`: value failed validation or is malformed.
- `STALE`: value exists but is older than the approved freshness limit.
- `LOW_CONFIDENCE`: usable only with a documented caveat.
- `NOT_APPLICABLE`: indicator does not apply to this analysis unit.
- `PENDING_REVIEW`: imported but not yet approved.

The freshness limit must be set per indicator based on its actual update cycle. Do not apply one arbitrary age limit to all datasets.

## 6. Missing-data semantics

| Situation | Representation | Scoring behaviour |
|---|---|---|
| Source has no record for an area | `NULL` + `MISSING` | Exclude from available-indicator calculation; apply coverage rule |
| Source explicitly reports zero | Numeric `0` + `VALID` after validation | Treat as a real zero only if zero is meaningful for that measure |
| Source value is malformed / impossible | Preserve raw record where appropriate; mark `INVALID` | Exclude pending correction |
| Data is too old for the indicator | Keep value + `STALE` | Exclude or down-weight only if a documented policy says so |
| Indicator does not apply | `NULL` + `NOT_APPLICABLE` | Exclude from denominator; disclose |
| Value is estimated/imputed | Store estimate separately with method and flag | Do not treat as observed; default MVP policy is not to impute for scoring |

## 7. Derived fields and display labels

- `normalized_value`: direction-adjusted value in the approved scoring range, normally 0–1.
- `weight_used`: weight from the exact configuration version used for the run.
- `contribution`: normalized value multiplied by its applied weight under the approved formula.
- `coverage_ratio`: share of eligible configured weight represented by valid, sufficiently fresh observations; calculate only after the indicator set and weights are approved.
- `risk_score`: relative index, not a probability, temperature, or health outcome.
- `risk_category`: configurable label derived from approved thresholds; thresholds are provisional until validated.

Keep raw, normalized, and displayed values distinct.
