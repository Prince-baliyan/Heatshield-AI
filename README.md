# HeatShield AI

**Evidence-Aware Urban Heat Decision-Support Prototype**
*(Hackathon Track: AI-Powered Hyperlocal Heat Impact Intelligence & Response Platform)*
**Team:** ByteForce | **Target demo:** 28 November 2026

## What it does

HeatShield AI is a decision-support prototype to assess and compare heat-related vulnerability across supported local areas. It combines verified environmental data and deterministic indicator normalization to produce a transparent relative assessment and rule-based response suggestions.

> [!NOTE]
> **AI & ML Architecture Notice:**
> - **Current System:** Uses transparent, deterministic indicator-based scoring (weighted relative index) and a rule-based expert recommendation engine.
> - **No Synthetic Inference / Black-Box ML:** There are no trained neural networks, predictive black-box ML models, or ungrounded generative LLM components in the assessment path.
> - **Honest Boundary:** It is not a weather forecasting service or a clinically validated heat-health prediction system. Machine learning models are deferred until labelled epidemiological outcomes and representative validation data exist (see `docs/AI_METHODOLOGY.md`).

## Intended demo workflow

1. Select a supported city and area.
2. View the area's relative assessment on a map/dashboard.
3. Inspect the indicators contributing to the assessment.
4. Review data coverage and quality notes.
5. View suggested local response actions.
6. Compare areas or export a simple report only if time and verified data permit.

## Planned technology

- Frontend: React, Vite, Tailwind CSS
- Map: Leaflet / React-Leaflet
- Backend: Python, Django REST Framework
- Database: MySQL 8.0
- Processing: Pandas, NumPy
- Initial risk engine: documented indicator-based scoring

Exact versions will be recorded in `docs/TECH_STACK.md` after compatibility checks.

## Target structure

```text
HeatShield-AI/
├── README.md
├── .env.example
├── .gitignore
├── docs/
├── frontend/
├── backend/
├── data/{raw,processed,sample}/
├── ml_engine/
└── tests/
```

This is the planned layout, not a claim that every component exists already.

## Start here

Read `docs/DOCUMENTATION_BLUEPRINT.md`, then `docs/PROJECT_OVERVIEW.md`, `docs/PRD.md`, `docs/SRS.md` and `docs/MVP_SCOPE.md`.

## Accuracy rules

- Label synthetic, sample or illustrative data.
- Do not present an indicator score as measured temperature or probability of illness/death.
- Show missing/stale data and uncertainty.
- Treat recommendations as decision support.
- Do not claim a city is supported until its data coverage is checked.

## Current status

The Django backend includes health and illustrative demo-weather endpoints, persisted assessment history, a deterministic provisional weather index, and configurable recommendation evaluation. The assessment write endpoint requires authentication. The assessment scores, bounds, weights, minimum coverage, and category cut-offs are provisional and not scientifically validated. The database schema is migrated, but the current local database contains no city, area, observation, or recommendation-rule records. No ward data or geometry is included. The React app remains a scaffold; assessment dashboard integration is not implemented.

For the provisional calculation, supported indicator inputs, weights, bounds, coverage behavior, and limitations, see `docs/RISK_SCORING.md`. For assessment API requests and responses, see `docs/API_SPEC.md`.

To configure the repeatable, city-level demo location:

```bash
cd backend
.venv/bin/python manage.py setup_demo_city
```

This creates the Meerut city and `Meerut City` area only when they are absent.
It does not create ward records, coordinates, observations, datasets, assessments,
recommendations, or other demo measurement data.
