# HeatShield AI — Technology Stack

**Status:** Verified development baseline — 22 November 2026.
**Scope:** Installed and tested technologies are distinguished from planned and optional components.

## 1. Stack decisions

| Layer | Technology | Purpose | Status |
|---|---|---|---|
| Frontend language | TypeScript 5.8.3 | Type-safe client development | Verified |
| Frontend framework | React 19.3.1 | Dashboard UI | Installed; production build passes |
| Frontend build tool | Vite 7.3.8 | Development server and production build | Verified |
| TypeScript configuration | Strict project references | Separate application and Vite configurations; strict checks enabled | Verified |
| Styling | Tailwind CSS 4.3.5 | Responsive UI styling | Installed |
| Tailwind integration | @tailwindcss/vite 4.3.5 | Vite integration | Installed |
| Routing | React Router | Page navigation | Deferred; not installed |
| HTTP client | Native Fetch API | Backend API calls | Selected; no additional dependency |
| Mapping | Leaflet + React-Leaflet | Geographic map rendering | Planned; not installed |
| Backend language | Python 3.12.3 | Server-side development | Verified |
| Backend framework | Django 5.2.19 | Application server | Verified |
| API framework | Django REST Framework 3.16.1 | REST API | Verified |
| Database | MySQL Server 8.0.46 | Persistent data storage | Verified; connection successful |
| Database driver | mysqlclient 2.3.2 | Django-MySQL connectivity | Verified |
| Environment configuration | python-dotenv 1.2.4 | Load backend environment variables | Installed |
| CORS | django-cors-headers 4.9.0 | Cross-origin development support | Installed |
| Data processing | Pandas + NumPy | Data cleaning and transformations | Deferred |
| Machine learning | scikit-learn | Evaluated ML use cases only | Optional; not installed |
| Backend testing | Django test framework | Backend verification | Available |
| API verification | curl | Manual endpoint testing | Used |
| Version control | Git | Source control | Initialized |

## 2. Verified environment versions

### Backend

| Component | Installed version |
|---|---|
| Python | 3.12.3 |
| Django | 5.2.19 |
| Django REST Framework | 3.16.1 |
| django-cors-headers | 4.9.0 |
| mysqlclient | 2.3.2 |
| python-dotenv | 1.2.4 |
| MySQL Server | 8.0.46 |

### Frontend

| Component | Installed version |
|---|---|
| Node.js | 22.23.4 |
| npm | 10.9.9 |
| React | 19.3.1 |
| React DOM | 19.3.1 |
| TypeScript | 5.8.3 |
| Vite | 7.3.8 |
| Tailwind CSS | 4.3.5 |
| @tailwindcss/vite | 4.3.5 |
| @vitejs/plugin-react | 5.2.0 |
| @types/react | 19.3.0 |
| @types/react-dom | 19.3.0 |

These are observed installed versions, not a claim that every backend dependency is exactly pinned.

## 3. Dependency and lockfile policy

- Backend dependencies are declared in `backend/requirements.txt` using compatible version ranges.
- Frontend dependencies are declared in `frontend/package.json`.
- `frontend/package-lock.json` records the resolved frontend dependency tree.
- Commit the frontend lockfile to version control.
- Do not claim exact backend reproducibility until a backend lockfile or equivalent pinning strategy is adopted.
- Verify compatibility before upgrading major framework versions.

## 4. Frontend package selection

Currently installed:
- `react`
- `react-dom`
- `vite`
- `typescript`
- `tailwindcss`
- `@tailwindcss/vite`
- `@vitejs/plugin-react`
- `@types/react`
- `@types/react-dom`

Deferred:
- `react-router-dom` — add when multiple routes are required.
- `leaflet` and `react-leaflet` — add after map and geographic-data requirements are finalized.
- `axios` — unnecessary while native Fetch is sufficient.

Avoid adding dependencies without an implementation requirement.

### TypeScript and Vite configuration

- `tsconfig.json` references `tsconfig.app.json` and `tsconfig.node.json`.
- Application target: ES2022.
- Vite configuration target: ES2023.
- Strict TypeScript checking is enabled in both configurations.
- Application checks include unused-local and unused-parameter detection.
- Vite enables the React and Tailwind CSS plugins.
- Development server binds to `127.0.0.1:5173`.
- `strictPort: true` prevents automatic port changes.

## 5. Backend package selection

Currently declared in `backend/requirements.txt`:
- `Django`
- `djangorestframework`
- `django-cors-headers`
- `mysqlclient`
- `python-dotenv`

Deferred or optional:
- `pandas` and `numpy` — add when data-processing requirements justify them.
- `scikit-learn` — add only for a defined ML use case with suitable labelled data and evaluation.
- `pytest` — optional; the Django test framework is available for current backend testing.

The initial scoring engine should use ordinary, tested Python code rather than introducing ML without evidence.

## 6. Database and spatial decisions

- Database: MySQL Server 8.0.
- Current development setup: locally installed MySQL service.
- Django connectivity uses `mysqlclient`.
- Database name: `heatshield_ai`.
- Database credentials must remain in environment configuration and must never be committed.
- PostGIS is a PostgreSQL extension and is not part of this MySQL stack.
- Consider MySQL spatial data types and functions only if verified polygon boundaries or spatial queries are required.
- Representative latitude/longitude coordinates may be sufficient for an initial map if their meaning and provenance are documented.

## 7. Configuration and security principles

- Store secrets and local configuration in environment variables.
- Keep `.env` files out of Git.
- Commit `.env.example` with placeholder values only.
- Never put database credentials or private API keys in frontend source code.
- Do not hard-code machine-specific absolute paths.
- Use separate development and production settings where deployment requirements justify them.
- Do not expose database passwords in screenshots, logs, documentation, or commits.

## 8. Verification status

Verified:
- Django system checks pass.
- Django connects successfully to MySQL.
- Backend health endpoint reports database status as OK.
- Frontend TypeScript project-reference configuration is valid.
- Frontend production build passes, including TypeScript compilation.
- Frontend dependencies install successfully and `npm ls --depth=0` reports no missing direct dependencies.

Not yet implemented or verified:
- City, area, and assessment business models and migrations.
- Map integration.
- City and area API endpoints.
- Assessment/scoring service.
- Verified external heat and geographic datasets.
- Production deployment configuration.

## 9. Deferred decisions

- React Router requirement.
- Map library integration and geographic data format.
- MySQL spatial storage requirement.
- Backend dependency lockfile strategy.
- Authentication and admin write permissions for the demo.
- Data-processing dependencies.
- Any ML use case, subject to data availability and evaluation evidence.
