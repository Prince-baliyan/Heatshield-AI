# Environment Setup Plan

**Status:** Setup specification, not a machine-specific installation guide. Exact versions and commands must be verified against the team's selected stack before being frozen.

## 1. Required development tools

- Git.
- Python runtime compatible with the selected Django and DRF releases.
- Node.js runtime compatible with the selected Vite release.
- MySQL 8.0.
- A code editor.
- Optional: Docker / Docker Compose for repeatable local database setup.
- Optional: Evaluate MySQL spatial data types and functions only if approved spatial features require them.

Do not copy version numbers from an old machine without checking compatibility. Record exact versions in the project after the team selects and tests them.

## 2. Configuration files

Keep secrets outside source control. Provide:
- Backend `.env.example`.
- Frontend `.env.example` only for public client configuration.
- A documented local database name and role.
- Document the current Django settings configuration and environment-specific deployment requirements.
- A clear list of required and optional variables.

Candidate backend variables:

| Variable | Purpose | Secret? |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django signing/security key | Yes |
| `DJANGO_DEBUG` | Development debug switch | No |
| `DJANGO_ALLOWED_HOSTS` | Allowed host list | No |
| `DATABASE_NAME` | MySQL database name | No |
| `DATABASE_USER` | MySQL database username | No |
| `DATABASE_PASSWORD` | MySQL database password | Yes |
| `DATABASE_HOST` | MySQL server host | No |
| `DATABASE_PORT` | MySQL server port (3306) | No |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | No |
| `TIME_ZONE` | Application timezone | No |
| `HEATSHIELD_ENV` | Environment identifier | No |

Choose one database configuration style and document it; do not support multiple styles accidentally.

Candidate frontend variable:
- `VITE_API_BASE_URL` — API base URL. Values exposed through Vite client variables are public and must never contain secrets.

## 3. Local setup sequence

1. Clone the repository.
2. Read the root README and this environment guide.
3. Create backend virtual environment.
4. Install backend dependencies from the version-constrained backend requirements file.
5. Create local environment file from `.env.example`.
6. Create MySQL database and user using local-only credentials.
7. Apply migrations.
8. Create an admin account through the documented Django command, if admin access is in scope.
9. Install frontend dependencies using the committed lockfile.
10. Start backend and frontend using documented commands.
11. Run health, unit, API, and frontend build checks.

The exact shell commands will be added after the repository layout and dependency versions are approved.

## 4. Configuration safety

- Never commit `.env`.
- Never place private API keys in frontend variables.
- Never use production credentials in local development.
- Use least-privilege database accounts.
- Rotate any secret accidentally committed.
- Keep debug mode disabled in production.
- Restrict allowed hosts and CORS origins.
- Do not expose database ports publicly for a demo unless explicitly secured.

## 5. Reproducibility

Commit dependency lockfiles and document:
- OS tested.
- Python and Node versions.
- MySQL 8.0 version.
- Install commands.
- Migration commands.
- Test commands.
- Run commands.
- Seed/reset commands.

A new teammate should be able to follow the README on a clean machine without relying on undocumented local state.
