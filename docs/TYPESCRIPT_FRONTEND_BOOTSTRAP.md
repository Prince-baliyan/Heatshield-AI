# TypeScript Frontend Bootstrap Plan

**Selected:** React + Vite + TypeScript + Tailwind CSS\
**Status:** Bootstrap plan; exact compatible package versions and package manager must be selected and pinned before installation.

## 1. Project creation

Create the frontend from the repository root only after selecting the Node.js version and package manager.

A standard Vite React TypeScript scaffold can be created with the official Vite project generator. Select the React + TypeScript template. Do not select JavaScript.

The generated project should include:
- `src/main.tsx`
- `src/App.tsx`
- `tsconfig.json`
- Vite configuration
- package manifest and lockfile

## 2. TypeScript rules

- Keep `strict` type checking enabled.
- Use `unknown` rather than `any` for untrusted external values.
- Define API response contracts in `src/types/`.
- Keep API request functions in `src/services/`.
- Validate important runtime API responses; compile-time types do not validate JSON received over HTTP.
- Avoid duplicating server-side scoring logic in the frontend.

## 3. Suggested feature layout

```text
src/
├── app/
├── components/
├── features/
│   ├── cities/
│   ├── map/
│   ├── assessments/
│   └── data-quality/
├── lib/
├── services/
├── styles/
└── types/
```

## 4. Frontend environment

Create `frontend/.env.local` from `frontend/.env.example`.

`VITE_API_BASE_URL` is public configuration. Never place private API keys, database credentials, or Django secret keys in any `VITE_` variable.

## 5. Initial verification

After scaffolding:
- Install dependencies using the selected package manager.
- Commit the generated lockfile.
- Run the development server.
- Run the production build.
- Run lint/type checks if configured.
- Verify that no secret is included in the browser bundle.

## 6. Tailwind setup

Use the official Tailwind installation guide matching the selected major version and Vite integration. Tailwind setup instructions differ between major versions; do not copy configuration from an older tutorial without checking compatibility.
