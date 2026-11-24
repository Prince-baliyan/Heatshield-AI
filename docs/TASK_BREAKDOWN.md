# Task Breakdown and Dependencies

**Status:** Initial backlog. Convert tasks into issues and assign owners before implementation.\
**Priority:** `P0` blocks the MVP; `P1` important; `P2` optional.

## 1. Workstream backlog

| ID | Priority | Task | Depends on | Acceptance evidence |
|---|---|---|---|---|
| HS-001 | P0 | Review and freeze Phase 1–3 decisions | None | Decision log approved |
| HS-002 | P0 | Confirm frontend language choice (JavaScript or TypeScript) and supported versions | HS-001 | Stack decision recorded |
| HS-003 | P0 | Create repository structure and contribution rules | HS-001 | Clean repository and README |
| HS-004 | P0 | Add `.env.example` and environment validation | HS-003 | No secrets committed; missing config gives clear error |
| HS-005 | P0 | Bootstrap Django + DRF project | HS-002, HS-003 | Backend starts from documented commands |
| HS-006 | P0 | Configure MySQL 8.0 and migrations | HS-005 | Migration and connection tests pass |
| HS-007 | P0 | Implement city, area, source, dataset and observation models | HS-006, approved schema | Model constraints and migrations tested |
| HS-008 | P0 | Add admin registration and safe data-entry workflow | HS-007 | Admin can manage approved records |
| HS-009 | P0 | Build import/validation pipeline for one approved dataset or labelled fixture | HS-007, source approval | Import report includes row counts and quality issues |
| HS-010 | P0 | Implement indicator configuration and versioning | HS-001, HS-007 | Config validation rejects invalid weights/bounds |
| HS-011 | P0 | Implement normalization and direction handling | HS-010 | Unit tests cover direct/inverse indicators |
| HS-012 | P0 | Implement missing-data and coverage gate | HS-009, HS-010 | Missing never becomes zero; insufficient data returns status |
| HS-013 | P0 | Implement score and contribution breakdown | HS-011, HS-012 | Reproducible score and contribution tests pass |
| HS-014 | P0 | Implement city/area/assessment read endpoints | HS-007, HS-013 | API contract tests pass |
| HS-015 | P0 | Bootstrap React/Vite/Tailwind frontend | HS-002, HS-003 | Production build succeeds |
| HS-016 | P0 | Add typed/central API client and UI states | HS-014, HS-015 | Loading/error/empty states verified |
| HS-017 | P0 | Build dashboard and area detail views | HS-016 | Required fields and caveats displayed |
| HS-018 | P1 | Add map visualisation for verified geometry | HS-017, geometry availability | Map matches supported analysis units |
| HS-019 | P0 | Add integration and end-to-end demo tests | HS-014, HS-017 | Core demo path passes |
| HS-020 | P0 | Prepare seed/reset process and demo runbook | HS-019 | Demo can be reset and repeated |
| HS-021 | P1 | Add deployment configuration and production hardening | HS-019 | Deployment checklist completed |
| HS-022 | P1 | Add accessibility and performance review | HS-017 | Review findings resolved or documented |

## 2. Suggested team ownership

Assign one accountable owner per task; contributors may assist. The following is a suggested split, not an assumption about individual skills:

- **Backend/data workstream:** Django, MySQL, models, imports, API.
- **Scoring/validation workstream:** indicator definitions, normalization, missing-data tests, score explainability.
- **Frontend/map workstream:** React UI, API integration, map/list fallback.
- **Integration/release workstream:** repository coordination, test runs, demo script, documentation and release checklist.

For a four-person team, rotate review responsibilities so the person implementing a feature is not its only reviewer. Record actual owner names in the issue tracker after the team agrees.

## 3. Dependency rules

- Do not start scoring implementation until indicator definitions, bounds, directions, weights, and missing-data policy are approved for the demo configuration.
- Do not start real data ingestion until source access and licence are verified.
- Do not require map polygons if suitable boundaries are unavailable; use a documented list/table fallback.
- Frontend development may use labelled mock responses, but mock values must never be represented as real observations.
- API field changes must update `API_SPEC.md` and frontend tests in the same task.

## 4. Implemented Phase 1 task status

| ID | Task | Status | Evidence |
|---|---|---|---|
| HS-R01 | Demo Meerut city and city-level area setup | COMPLETE for implementation; MySQL test suite blocked | Repeatable `setup_demo_city` command created exactly one city and one city-level area and remained repeatable |
| HS-R02 | City and area read APIs | COMPLETE for implementation; MySQL test suite blocked | Live smoke checks passed for `/api/v1/cities/`, `/api/v1/areas/`, and `/api/v1/cities/{city_id}/areas/` |

Both tasks remain subject to actual database-backed test execution. The project has no
frontend implementation changes in this phase.

## 5. Issue template

Each implementation issue should contain:

- ID and title.
- Problem / user outcome.
- Scope and explicit non-goals.
- Dependencies.
- Files or components likely affected.
- Acceptance criteria.
- Test cases.
- Data source/provenance impact, if any.
- Documentation updates required.
- Owner and reviewer.
