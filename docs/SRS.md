# Software Requirements Specification (SRS)

## Purpose

Defines first-prototype software behaviour. It complements `PRD.md`; final database columns and API payloads belong to their dedicated specifications.

## System context

Planned components: React web client; Django REST Framework API; MySQL Server 8.0 database; data preparation/validation process; separate risk-assessment module called by the backend. External datasets are used only after source, permitted use, geography and freshness are checked.

## Actors

- **Dashboard user:** browses supported locations and assessments.
- **Data/admin operator (prototype role):** maintains configured areas and dataset records. Authentication/permissions are not assumed until designed.
- **System process:** validates inputs, calculates scores and returns explanations/recommendations.

## Use case: view an area assessment

**Preconditions:** At least one city and area are configured. Required indicator records exist, or the system can explain insufficient coverage.

**Main flow**
1. User opens dashboard.
2. System returns supported cities/areas.
3. User selects city and area.
4. Client requests assessment.
5. Backend validates area and data availability.
6. Risk engine applies documented scoring method.
7. Backend returns score/category, drivers, data-quality notes and recommendations.
8. Client renders map and assessment.

**Alternative flows**
- No areas configured: show an empty state.
- Data missing/insufficient: return insufficient-data state; do not silently calculate a complete score.
- Invalid area ID: return not-found response.
- Scoring failure: return safe error and log diagnostics without exposing secrets.

## Input validation

Identifiers must refer to configured records. Numeric indicators must satisfy documented range/unit. Unknown units or incompatible geographic resolutions must be rejected or explicitly transformed. Missing values remain distinguishable from measured zero. Dataset timestamps and source references should be retained where available.

## Output requirements

An assessment conceptually contains location identity; score/category if calculable; scoring method/version; contributing indicators; data coverage/quality notes; recommendations and rationale; sample/illustrative-data flag. Exact fields/types belong in `API_SPEC.md`.

## Error handling

Distinguish invalid request, unknown location, no data, insufficient coverage, stale-data warning and internal assessment failure. Frontend must not turn errors into a zero-risk result.

## Security and privacy

Do not store personal health records or identifiable individual health data in MVP. Keep secrets outside source control. Validate API inputs. Protect administrative write operations if implemented. Do not expose stack traces or secrets to browser.

## Traceability

| Requirement | PRD | Verification |
|---|---|---|
| Supported locations | FR-01 | API/UI test |
| Area selection | FR-02 | UI integration test |
| Map | FR-03 | Manual browser test |
| Score | FR-04 | Unit tests with fixed inputs |
| Explanation | FR-05 | API/UI test |
| Data quality/sample disclosure | FR-06, FR-08 | Missing/stale/sample-data tests |
| Recommendations | FR-07 | Rule mapping test |
| Error states | FR-09 | Negative API/UI tests |
