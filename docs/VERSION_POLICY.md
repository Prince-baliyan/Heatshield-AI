# Version and Dependency Policy

**Purpose:** Select reproducible versions without guessing compatibility or pinning unverified releases.

## 1. Version selection process

Before implementation, the team must select and record versions for:

- Python
- Django
- Django REST Framework
- MySQL Server
- mysqlclient
- Node.js
- npm
- React
- Vite
- TypeScript
- Tailwind CSS
- Map library (only if map geometry is available)

For each selection:

1. Check official release and support documentation.
2. Confirm compatibility with the other selected packages.
3. Install on the actual development OS.
4. Run a clean build and relevant tests.
5. Decide and document the pinning or version-range policy.
6. Record the date and environment tested.

Do not interpret a version range as a reproducible lock. Do not blindly install `latest`.

## 2. Dependency separation

Backend dependencies belong in `backend/requirements.txt`. Frontend dependencies belong in `frontend/package.json` and `frontend/package-lock.json`.

Do not mix Python and Node dependencies in one manifest.

## 3. Current verified development baseline

The following versions were observed in the local development environment. They are environment observations, not a claim of official support verification.

| Component | Observed version | Verification |
|---|---|---|
| Python | 3.12.3 | Local runtime |
| Django | 5.2.19 | Installed package |
| Django REST Framework | 3.16.1 | Installed package |
| MySQL Server | 8.0.46 | Local server |
| mysqlclient | 2.3.2 | Installed package |
| Node.js | 22.23.4 | Local runtime |
| npm | 10.9.9 | Local package manager |
| React | 19.3.1 | Installed package |
| React DOM | 19.3.1 | Installed package |
| Vite | 7.3.8 | Installed package |
| TypeScript | 5.8.3 | Installed package |
| Tailwind CSS | 4.3.5 | Installed package |

Recheck this table whenever the development environment or dependency manifests change.

## 4. Lockfile rules

- Commit `frontend/package-lock.json`.
- Do not manually edit lockfiles.
- Backend dependencies currently use version ranges in `backend/requirements.txt`.
- Exact backend pinning or a lock-capable workflow remains an open team decision.
- Update dependencies in a separate reviewed task.
- Run the backend checks and frontend build after dependency updates.
