# HeatShield AI — Architecture Decision Record

**Phase:** 6 — Development Environment & Dependency Baseline
**Status:** Historical decisions preserved; current implementation baseline updated.

## 1. Current accepted decisions

| Decision | Selected option | Consequence |
|---|---|---|
| Frontend language | TypeScript | Use TypeScript for React components, API contracts, and shared frontend types |
| Backend framework | Django and Django REST Framework | Use Django as the backend application and API framework |
| Database | MySQL Server 8.0 | Use a locally installed MySQL service; no Docker required |
| Database driver | mysqlclient | Django connects to MySQL through the mysqlclient driver |
| Spatial approach | Conditional MySQL spatial features | Start with representative coordinates; use spatial features only when verified geographic requirements justify them |
| Demo city | Configurable | Do not hard-code a city; enable a city only after data-readiness checks pass |
| Frontend package manager | npm | Use npm and commit `frontend/package-lock.json` |

## 2. Superseded historical decisions

The following decisions were made during an earlier Phase 6 planning baseline. They are retained for project history but are no longer active.

| Earlier decision | Earlier selection | Current status |
|---|---|---|
| Database | PostgreSQL with direct local installation | Superseded by MySQL Server 8.0 |
| Spatial extension | Conditional PostGIS adoption | Superseded; evaluate MySQL spatial features if required |

Do not follow the archived PostgreSQL setup instructions for the current project.

Historical setup reference: `docs/ARCHIVED_POSTGRESQL_SETUP.md`.

## 3. Current architecture consequences

### TypeScript
- Use `.ts` for non-UI TypeScript modules and `.tsx` for React components.
- Define API response types centrally.
- Treat API data as untrusted at runtime; TypeScript types alone do not validate server responses.
- Keep authoritative score calculations in the backend.

### Local MySQL
- Backend connects to the local MySQL service using environment variables.
- Database name: `heatshield_ai`.
- Development database user: `heatshield_dev`.
- Host: `127.0.0.1`.
- Port: `3306`.
- Use `mysqlclient` as the Django database driver.
- Do not commit database passwords or local database dumps.
- Docker Compose is not part of the required local workflow.
- Follow `docs/LOCAL_MYSQL_SETUP.md` for setup instructions.

### Conditional MySQL spatial features
- MySQL 8.0 provides spatial data types and functions.
- Start with representative latitude/longitude coordinates if they satisfy the MVP requirements.
- Consider spatial columns and queries only if approved area polygons, spatial joins, or point-in-polygon operations are required.
- If no verified geometry is available, use area identifiers and a list/table UI instead of inventing map boundaries.

### Configurable city
- Store city configuration in the database, not as a frontend constant.
- City availability must depend on verified boundary/area data and indicator coverage.
- An unready city should return a clear `NOT_READY` state.
- Demo fixtures must be clearly marked synthetic and must not be presented as observed city data.

## 4. Decisions still open

The following decisions are not yet finalized:

- Whether exact backend dependency pinning or a backend lockfile is required.
- Whether authentication is needed for the first demo.
- Final indicator catalogue, weights, normalization bounds, freshness rules, and coverage threshold.
- Actual verified data sources and city/area geography.
- Whether the demo requires polygon maps or can use representative points.
- Final MySQL spatial storage requirements.
- Approved scoring configuration and category thresholds.

Record each decision before implementing a task that depends on it.
