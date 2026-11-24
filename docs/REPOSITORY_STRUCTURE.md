
# HeatShield AI — Repository Structure

**Phase:** Development Foundation
**Status:** Current repository structure verified; future folders are planned separately.

## 1. Current repository structure

The following structure reflects files and directories verified in the current development repository. Generated files, virtual environments, dependency directories, and local secrets are excluded.

```text
HeatShield-AI/
├── backend/
│   ├── apps/
│   │   ├── assessments/
│   │   ├── cities/
│   │   ├── common/
│   │   ├── datasets/
│   │   └── indicators/
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── manage.py
│   ├── requirements.txt
│   ├── README.md
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── .env.example
├── data/
│   └── fixtures/
├── docs/
├── DOCUMENTATION_BLUEPRINT.md
├── .gitignore
└── README.md
```

## 2. Selected architecture

The project follows a modular monolith architecture:

- Backend: Django and Django REST Framework.
- Database: MySQL Server 8.0.
- Database driver: mysqlclient.
- Frontend: React, TypeScript, Vite and Tailwind CSS.
- API: REST endpoints under `/api/v1/`.
- Database connection: Environment-based configuration.
- Local development: Separate frontend and backend processes.

Do not introduce microservices for the MVP.

**Implementation status:** The technology stack and development environment
are configured, but this does not establish that the application features
are implemented or complete. Feature completion must be verified through
code review and testing.

## 3. Backend app responsibilities

- `common`: Shared utilities and health endpoint.
- `cities`: City and analysis-area registry.
- `datasets`: Dataset and source management.
- `indicators`: Indicator definitions and observations.
- `assessments`: Assessment and scoring functionality.

The application directories currently exist, but their business models and implementation are not complete.

## 4. Frontend responsibilities

- `App.tsx`: Main application component.
- `main.tsx`: Frontend entry point.
- `services/api.ts`: API communication.
- `styles.css`: Global styling.
- `vite.config.ts`: Vite and frontend plugin configuration.

Feature-specific components, routing and map integration are future implementation work.

## 5. Planned structure

The following directories may be introduced when their implementation tasks begin:

```text
backend/
└── tests/

frontend/src/
├── app/
├── assets/
├── components/
├── features/
│   ├── cities/
│   ├── map/
│   ├── assessments/
│   └── data-quality/
├── hooks/
├── lib/
├── styles/
└── types/

data/
├── raw/
└── processed/
```

These are planned locations, not currently verified directories. Create them only when required by an implementation task.

## 6. Repository rules

- Keep backend and frontend dependency manifests separate.
- Commit `frontend/package-lock.json`.
- Keep passwords, secret keys and local environment files out of Git.
- Keep `.env.example` files limited to safe placeholder values.
- Do not commit local database files or restricted datasets.
- Synthetic fixtures must be clearly labelled.
- Do not commit generated files, virtual environments or dependency directories.
- Keep the root README as the primary setup entry point.

## 7. Structure change control

Update this document whenever the actual repository structure or architecture changes.

Before adding new directories, identify the implementation task that requires them. Avoid creating empty folders solely for appearance.
