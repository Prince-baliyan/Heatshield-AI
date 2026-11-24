# Backend Setup Specification

**Backend:** Python + Django + Django REST Framework + MySQL 8.0
**Status:** Setup specification; exact dependency versions are intentionally not pinned in this document.

## 1. Responsibilities

The backend owns:
- Data validation and persistence.
- Source and dataset provenance.
- Indicator observations and quality states.
- Versioned assessment calculations.
- API response contracts and access control.

The backend must not:
- Invent unavailable observations.
- turn missing values into zero.
- Calculate scores from unapproved indicator configurations.
- Expose secrets or unrestricted admin operations.

## 2. Initial Django project

Create a Django project package named `config` and use separate settings modules:
- `config.settings.base`
- `config.settings.development`
- `config.settings.production`

Create Django apps as implementation tasks become ready:
- `apps.common`
- `apps.cities`
- `apps.datasets`
- `apps.indicators`
- `apps.assessments`

Add `apps/__init__.py` and each app's `__init__.py` where required. Keep app configuration and migrations inside each Django app.

## 3. Settings requirements

Base settings should contain shared installed apps, middleware, URL configuration, templates, timezone, static/media configuration and password validation.

Development settings may enable developer conveniences but must not be reused in production.

Production settings must:
- Require a strong secret from environment.
- Disable debug mode.
- Require explicit allowed hosts.
- Configure secure cookies and HTTPS settings for the actual deployment environment.
- Use production database credentials from environment.
- Avoid exposing detailed exception traces to clients.

Do not hard-code credentials, secret keys, hostnames, or deployment URLs.

## 4. MySQL

Use MySQL 8.0 as the primary database.

The current development configuration uses:
- Database engine: `django.db.backends.mysql`
- Database name: `heatshield_ai`
- Database user: `heatshield_dev`
- Host: `127.0.0.1`
- Port: `3306`
- Character set: `utf8mb4`
- Python driver: `mysqlclient`

Define database credentials through local environment variables.

Do not commit database passwords or expose the MySQL service publicly.

Implement spatial features only after confirming the required geographic operations and MySQL spatial capabilities.

Migrations must be committed. Do not edit an already-applied migration to represent a new schema change; create a new migration.

## 5. API structure

Use the versioned prefix:

`/api/v1/`

Candidate endpoint groups from Phase 2:
- `GET /api/v1/cities/`
- `GET /api/v1/cities/{city_id}/areas/`
- `GET /api/v1/areas/{area_id}/assessment/`

Implement only after matching the Phase 2 API specification. Any contract change must update `API_SPEC.md`, backend tests, and frontend service/types together.

## 6. Backend quality gates

Before a backend task is complete:
- Run migrations against a clean development database.
- Run unit and API tests.
- Validate environment configuration.
- Check permissions for admin/write operations.
- Verify provenance is retained for imported observations.
- Verify assessment responses include status, coverage, method/configuration version and limitations.
- Verify insufficient-data cases do not return a fabricated score.

## 7. Dependency policy

Select compatible versions as a team, verify compatibility against official release documentation, then pin exact versions in `requirements.txt` or the chosen lockfile. Do not install unpinned latest versions in a reproducibility-critical release branch.
