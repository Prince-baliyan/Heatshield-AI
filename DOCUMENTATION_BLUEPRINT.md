# HeatShield AI — Documentation Blueprint

**Team:** ByteForce | **Demo:** 28 November 2026 | **City strategy:** Configurable, data-dependent | **Database:** MySQL 8.0

## Documentation phases

| Phase | Files | Exit condition |
|---|---|---|
| 0 — Blueprint | `DOCUMENTATION_BLUEPRINT.md` | Scope, ownership and dependencies are clear |
| 1 — Product foundation | `README.md`, `PROJECT_OVERVIEW.md`, `PRD.md`, `SRS.md`, `MVP_SCOPE.md` | Users, workflows, requirements and demo boundaries are agreed |
| 2 — Technical design | `ARCHITECTURE.md`, `TECH_STACK.md`, `DATABASE.md`, `API_SPEC.md` | Component, database and API contracts agree |
| 3 — Data and risk model | `DATA_SOURCES.md`, `DATA_DICTIONARY.md`, `AI_METHODOLOGY.md`, `RISK_SCORING.md` | Every score input has provenance, units, transformations and limitations |
| 4 — Delivery and quality | `TASKS.md`, `TESTING.md`, `DEPLOYMENT.md`, `KNOWN_LIMITATIONS.md` | Work is assigned and demo is reproducible |
| 5 — Change control | Update affected documents as implementation changes | Code, docs and demo claims remain aligned |

## Source-of-truth ownership

- Product purpose/users: `PROJECT_OVERVIEW.md`
- Product requirements: `PRD.md`
- Detailed system behaviour: `SRS.md`
- Demo boundary: `MVP_SCOPE.md`
- Components/data flow: `ARCHITECTURE.md`
- Exact dependencies: `TECH_STACK.md`
- Persistent entities: `DATABASE.md`
- Endpoint contracts: `API_SPEC.md`
- Dataset provenance/access: `DATA_SOURCES.md`
- Field names/units/null handling: `DATA_DICTIONARY.md`
- Method and model limitations: `AI_METHODOLOGY.md`
- Formula, weights and thresholds: `RISK_SCORING.md`
- Work status: `TASKS.md`
- Verification: `TESTING.md`
- Setup/deployment: `DEPLOYMENT.md`
- Gaps/risks: `KNOWN_LIMITATIONS.md`

## Cross-document rules

1. The first demo is a decision-support prototype, not a precise heat forecast.
2. Scores must be explainable from visible indicators and documented transformations.
3. Missing or stale data must be explicit; never silently replace missing values with zero.
4. Enable only locations with known data coverage or clearly labelled illustrative data.
5. Label sample data visibly in the UI and reports.
6. Recommendations are suggestions for human review, not automated government decisions.
7. Do not claim predicted deaths, exact street-level temperatures, outages or measured outcomes without validated evidence.
8. API, database and frontend field names/types must agree.
9. Verify external data access, terms/licensing and fallback before integration.
10. Every demo feature needs a test or documented manual verification.

## Confirmed decisions

| Decision | Value |
|---|---|
| Project | HeatShield AI |
| Team | ByteForce |
| Demo date | 28 November 2026 |
| City | Configurable, based on data availability |
| Database | MySQL 8.0 |
| Initial scoring | Transparent indicator-based scoring |
| Frontend direction | React + Vite + Tailwind CSS |
| Backend direction | Python + Django REST Framework |
| Mapping direction | Leaflet / React-Leaflet |
| Processing | Pandas + NumPy |

Exact package versions, data providers, indicator weights, thresholds and schema are not frozen yet.
