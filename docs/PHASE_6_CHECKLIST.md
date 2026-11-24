# Phase 6 Checklist — Environment & Dependency Baseline

**Status:** Environment baseline substantially verified; data and application decisions remain open.

## 1. Decisions already accepted

- [x] Frontend language: TypeScript.
- [x] Backend framework: Django and Django REST Framework.
- [x] Database: MySQL Server 8.0; direct local installation, no Docker.
- [x] Database driver: mysqlclient.
- [x] Spatial approach: start with representative coordinates; evaluate MySQL spatial features only if verified polygon requirements justify them.
- [x] Demo city: configurable, subject to data readiness.
- [x] Frontend package manager: npm.

## 2. Environment and dependency verification

- [x] Python 3.12.3 installed.
- [x] Django 5.2.19 and Django REST Framework 3.16.1 installed.
- [x] Node.js 22.23.4 and npm 10.9.9 installed.
- [x] React 19.3.1, Vite 7.3.8, TypeScript 5.8.3 and Tailwind CSS 4.3.5 installed.
- [x] MySQL Server 8.0.46 installed and running.
- [x] Local development database `heatshield_ai` and user `heatshield_dev` configured.
- [x] Django connects successfully to MySQL.
- [x] Backend dependency check passes.
- [x] Frontend dependencies install successfully.
- [x] Frontend production build and TypeScript compilation pass.
- [x] Frontend dependency lockfile generated: `frontend/package-lock.json`.
- [x] Environment examples use placeholders; actual `.env` files are excluded from Git.
- [x] MySQL setup instructions documented in `docs/LOCAL_MYSQL_SETUP.md`.

## 3. Remaining decisions and work

- [ ] Confirm actual OS and distribution on every developer machine.
- [ ] Decide whether exact backend dependency pinning or a backend lockfile is required.
- [ ] Confirm whether authentication is required for the demo.
- [ ] Confirm the first verified dataset or use clearly labelled synthetic fixtures for UI-only development.
- [ ] Verify data source licensing, geography, freshness and coverage.
- [ ] Confirm whether valid polygon geometry exists.
- [ ] Finalize map library and geographic data format after requirements are verified.
- [ ] Finalize indicator definitions, units, normalization, weights and minimum coverage.
- [ ] Approve scoring configuration and category thresholds before presenting risk categories.

## 4. Exit criteria

Phase 6 is complete when the team has a documented and repeatable development environment, compatible dependency versions, an agreed dependency reproducibility strategy, a verified MySQL connection, and documented rules for secrets and data fixtures.

Data readiness and scoring approval are separate implementation gates.

Do not claim the application is implemented merely because the environment is installed.
