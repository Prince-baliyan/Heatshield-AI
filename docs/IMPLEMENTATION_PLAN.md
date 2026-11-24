# Implementation Plan

**Project:** HeatShield AI\
**Phase:** 4 — Implementation Planning\
**Status:** Proposed execution plan; no application code is created by this phase.

## 1. Objective

Convert the approved product, architecture, data, and scoring documentation into a controlled implementation sequence. Build a working MVP without assuming unverified datasets, APIs, city boundaries, or scientific validity.

## 2. Implementation principles

1. Documentation is the source of truth. Resolve conflicts before coding.
2. Build vertical slices that can be tested end-to-end.
3. Keep frontend, API, database, and scoring responsibilities separate.
4. Use migrations and version-controlled configuration.
5. Keep sample/synthetic data visibly labelled and isolated from real observations.
6. Do not enable a city or publish a score until its data-readiness checks pass.
7. Every feature must have acceptance criteria and tests.
8. Do not add ML merely to label the product “AI-powered”; MVP scoring remains deterministic and explainable.

## 3. Proposed delivery stages

| Stage | Work | Exit condition |
|---|---|---|
| 0. Documentation freeze | Review Phase 1–3; resolve open decisions; approve MVP scope | Decisions recorded; no contradictory requirements |
| 1. Repository foundation | Create frontend/backend structure, dependency manifests, environment template, formatting/linting, Git conventions | Fresh clone can be configured using documented steps |
| 2. Backend foundation | Django project, DRF setup, MySQL 8.0 connection, health endpoint, settings configuration | Backend starts; health endpoint and DB connection tests pass |
| 3. Data model and admin | Implement approved entities, migrations, admin workflows, source/dataset provenance | Migrations apply cleanly; sample records trace to datasets |
| 4. Data ingestion and validation | Import a verified small dataset or clearly labelled synthetic fixture; validation and quality statuses | Invalid/missing/stale data are detected and reported |
| 5. Assessment service | Implement versioned normalization, direction, weights, coverage gate, score breakdown | Unit tests cover formula, missing data, edge cases, reproducibility |
| 6. Read API | Cities, areas, assessment detail, metadata and error contracts | API contract tests pass; no unsupported score is returned |
| 7. Frontend foundation | React/Vite/Tailwind app shell, routing, API client, loading/error/empty states | Frontend builds and handles API states |
| 8. Dashboard and map | City/area selection, map or fallback list, score detail, coverage and provenance | UI displays only supported geography and clearly communicates limitations |
| 9. Integration and hardening | End-to-end tests, security checks, accessibility, performance, error handling | Release checklist passes |
| 10. Demo preparation | Seed data, demo script, reset procedure, known limitations, backup screenshots | Demo can be repeated on a clean setup |

The order may be adjusted if a dependency requires it, but the assessment service must not be built on fabricated data assumptions.

## 4. Recommended MVP feature boundary

### In scope
- Configurable city registry.
- Area/analysis-unit registry.
- Verified data-source and dataset metadata.
- Import of one small verified dataset, or labelled synthetic fixtures for UI development.
- Data quality and coverage reporting.
- Deterministic relative vulnerability index with versioned configuration.
- Explainable indicator contribution breakdown.
- Map display when valid area geometry is available; otherwise a clearly labelled area list/table.
- Curated, rule-based mitigation suggestions with caveats.
- Admin-only data and configuration management.

### Out of scope until separately approved
- Unvalidated heat forecasting.
- Illness, mortality, or outage prediction.
- Automated government decisions.
- Unverified live API integrations.
- Public user accounts or complex role systems unless required by the final demo scope.
- LLM-generated numeric analysis or autonomous recommendations.
- ML model training without labelled data and evaluation evidence.

## 5. Architecture boundaries

- **React frontend:** presentation, navigation, map/list interaction, API calls, visible data-quality caveats.
- **Django REST API:** authentication/permissions if enabled, validation, serializers, API contracts.
- **Assessment service:** deterministic calculations; no UI or network responsibilities.
- **Data ingestion layer:** source-specific import and validation; no scoring logic embedded in import scripts.
- **MySQL 8.0:** persistent application and assessment data.
- **Optional spatial features:** evaluate MySQL spatial data types and functions only if polygon storage or spatial queries are required and supported by available boundary data.

## 6. Definition of Done

A task is complete only when:
- Its acceptance criteria are met.
- Relevant automated tests pass.
- Error and empty states are handled.
- No secret or local-only configuration is committed.
- Documentation is updated if behaviour or API contracts changed.
- Data provenance and quality are preserved where relevant.
- The feature has been manually checked in the intended demo flow.

## 7. Release gates

Do not call the MVP data-backed until the source and licence checks pass. Do not call the score scientifically validated without appropriate independent validation. Do not call the product a forecasting system unless forecasting is implemented and evaluated as a separate capability.
