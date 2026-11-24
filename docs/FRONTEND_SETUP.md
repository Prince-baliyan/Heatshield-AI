# Frontend Setup Specification

**Frontend:** React + Vite + Tailwind CSS\
**Status:** Setup specification. JavaScript vs TypeScript and exact package versions remain team decisions.

## 1. Responsibilities

The frontend owns presentation and user interaction:
- City and area selection.
- Map display when verified geometry is available.
- List/table fallback when map geometry is unavailable.
- Score and indicator-contribution display.
- Data coverage, freshness, missing-data and limitation messaging.
- Loading, empty, error and insufficient-data states.

The frontend must not calculate or independently alter the official assessment score.

## 2. Proposed source layout

```text
src/
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
├── services/
├── styles/
└── types/
```

Keep components small and feature-oriented. Avoid placing the entire application in one `App` component.

## 3. API integration

Create one central API client in `src/services/`. Endpoint-specific functions should call that client. Do not scatter hard-coded base URLs or fetch logic across components.

Read the base URL from `VITE_API_BASE_URL`. Vite variables are bundled into client code and are public; never store API secrets in them.

Handle these response states explicitly:
- Successful data.
- Empty result.
- Loading.
- Network/server error.
- `INSUFFICIENT_DATA`.
- `NOT_READY`.
- `REVIEW_REQUIRED`.

## 4. Map behaviour

Use the map only when the API provides valid geometry at the supported analysis resolution. Show the geometry's source and limitations where relevant.

If no verified polygons or point coordinates are available:
- Do not fabricate map shapes or coordinates.
- Show an area list/table.
- Label any sample map data as synthetic demonstration content.

Map colours must be tied to the approved display configuration. Do not use unapproved category thresholds as if they were validated classifications.

## 5. UI quality requirements

- Responsive layout for laptop and mobile widths.
- Keyboard-accessible controls and visible focus states.
- Text labels in addition to colour.
- Clear numeric units and period labels.
- Visible source and data-freshness information.
- No score shown for insufficient-data responses.
- Synthetic fixtures visibly labelled.
- Error messages that explain what the user can do next.

## 6. Package and version policy

Choose JavaScript or TypeScript before scaffolding. TypeScript is useful for API contract safety, but it introduces type definitions and setup work; it is a team decision, not an assumed requirement.

Pin compatible package versions and commit the package-manager lockfile. Use one package manager consistently across the team.
