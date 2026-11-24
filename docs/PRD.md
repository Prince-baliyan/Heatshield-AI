# Product Requirements Document (PRD)

## Product summary

HeatShield AI is a configurable-city, map-led heat-impact decision-support prototype. The first release prioritises one demonstrable end-to-end workflow over broad geographic coverage.

## Goals

- Bring selected heat-related indicators into one area-level view.
- Make assessments understandable and auditable.
- Highlight data gaps and freshness limitations.
- Connect assessment results to practical response suggestions.
- Demonstrate the workflow on at least one data-supported city/area.

## Users and needs

| User | Need |
|---|---|
| Municipal/planning user | Identify areas needing attention and understand why |
| Disaster-management user | Compare relative priorities and review possible actions |
| Public-health/community user | Understand which groups may need additional protection |
| Demo evaluator | Verify the workflow and evidence-bounded claims |

## Functional requirements

- **FR-01 Supported locations:** list only configured cities/areas with known required-data coverage.
- **FR-02 Area selection:** allow selection of a supported area.
- **FR-03 Map:** display configured area geometry or representative markers.
- **FR-04 Assessment:** calculate score/category using the documented scoring specification.
- **FR-05 Explanation:** display contributing indicators and their influence/direction.
- **FR-06 Data quality:** expose missingness, source and freshness/coverage notes where available.
- **FR-07 Recommendations:** show response suggestions mapped to assessment drivers.
- **FR-08 Sample data:** visibly label sample/illustrative data.
- **FR-09 Errors:** show useful messages when location/data/assessment is unavailable.
- **FR-10 Comparison (stretch):** compare areas if time and data permit.
- **FR-11 Report export (stretch):** export a simple area summary if time permits.

## Non-functional requirements

Usability; explainability; reliability for invalid/incomplete inputs; responsive demo performance; maintainable scoring logic with tests; secrets outside source control; readable contrast and labelled controls.

## Out of scope

Nationwide production coverage; real-time ingestion from every provider; individual health prediction; prediction of deaths/admissions/exact street-level temperature; automated dispatch; causal impact claims; trained ML prediction without suitable labelled data and evaluation.

## Assumptions and dependencies

At least one city/area dataset can be prepared. Boundaries or representative coordinates can be obtained or created and labelled. External source access, licensing and update frequency must be checked. Exact indicators and weights belong in `RISK_SCORING.md`.

## Acceptance criteria

1. User selects at least one configured city and area.
2. Dashboard displays an assessment produced by the documented implementation.
3. User can inspect contributing indicators.
4. Missing or illustrative data is disclosed.
5. At least one recommendation is linked to an assessment driver.
6. Unavailable locations/invalid requests show clear errors.
7. Automated or documented manual tests verify the end-to-end flow.

## Priorities

- **P0:** location selection, area view, transparent score, explanation, data caveat, recommendations.
- **P1:** comparison, richer filters, downloadable report.
- **P2:** additional cities, scheduled refresh, advanced scenario simulation.
