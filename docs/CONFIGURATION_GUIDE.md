
# Configuration Guide

## 1. Environment files

Use local environment files for machine-specific settings:

- `backend/.env` — Django and MySQL configuration.
- `backend/.env.example` — safe backend configuration template.
- `frontend/.env.local` — local Vite configuration.
- `frontend/.env.example` — safe frontend configuration template.

Never commit real credentials, secret keys, or local environment files.

## 2. Backend variables

The backend loads `backend/.env` using `python-dotenv`.

| Variable | Purpose | Development value |
|---|---|---|
| DJANGO_SECRET_KEY | Django secret key | Generate a private key |
| DJANGO_DEBUG | Debug mode | True |
| DJANGO_ALLOWED_HOSTS | Allowed host names | 127.0.0.1,localhost |
| DATABASE_NAME | MySQL database | heatshield_ai |
| DATABASE_USER | MySQL user | heatshield_dev |
| DATABASE_PASSWORD | MySQL password | Local secret |
| DATABASE_HOST | Database host | 127.0.0.1 |
| DATABASE_PORT | MySQL port | 3306 |
| TIME_ZONE | Application timezone | Asia/Kolkata |
| MAX_OBSERVATION_AGE_DAYS | Maximum allowed age of stored observation periods, measured from `period_end` to the current local date; older records are excluded | 7 |
| CORS_ALLOWED_ORIGINS | Permitted frontend origins | http://localhost:5173 |
| CSRF_TRUSTED_ORIGINS | Origins allowed to submit CSRF-protected requests | http://localhost:5173,http://127.0.0.1:5173 |
| DJANGO_SESSION_COOKIE_SECURE | Send session cookie only over HTTPS | False in development; True in production |
| DJANGO_CSRF_COOKIE_SECURE | Send CSRF cookie only over HTTPS | False in development; True in production |
| DJANGO_SESSION_COOKIE_SAMESITE | Session cookie SameSite policy | Lax |
| DJANGO_CSRF_COOKIE_SAMESITE | CSRF cookie SameSite policy | Lax |
| DJANGO_SECURE_SSL_REDIRECT | Redirect HTTP to HTTPS | False locally; enable in production when proxy TLS is configured |
| DJANGO_SECURE_HSTS_SECONDS | HSTS duration in seconds | 0 locally; configure for production HTTPS |

`DJANGO_DEBUG=True` is for local development only. Production must use `False`, a securely generated secret key, and explicitly configured allowed hosts.

`MAX_OBSERVATION_AGE_DAYS` defaults to 7. Configure it to match the approved
dataset's update cadence and the assessment's intended time scope. A larger
value permits historical assessments but does not make old data current; the
result must still be described using its actual observation period. A value of
0 accepts only observations ending on the current local date.

Do not rely on the insecure fallback secret key in production.
The session and CSRF cookies default to secure in non-debug mode; explicitly
configure the same setting names in deployment. CORS credentials are enabled
only for the configured `CORS_ALLOWED_ORIGINS`; never use wildcard origins.
For cross-site deployments, configure HTTPS and compatible `SameSite=None`
cookie settings, then add only the exact HTTPS frontend origin to both origin
allow-lists.

## 3. Frontend variables

The frontend uses Vite environment variables.

Current variable:

| Variable | Purpose | Development value |
|---|---|---|
| VITE_API_BASE_URL | Backend API base URL | http://127.0.0.1:8000/api/v1 |

Variables prefixed with `VITE_` are exposed in the browser bundle.

Never put database passwords, private API keys, or server-side credentials in frontend environment files.

## 4. Database configuration

The project uses MySQL Server 8.0.

| Setting | Development value |
|---|---|
| Database | heatshield_ai |
| User | heatshield_dev |
| Host | 127.0.0.1 |
| Port | 3306 |
| Django driver | mysqlclient |

Django reads database settings from the backend environment variables.

Keep database credentials local. Do not commit database dumps or local database files.

## 5. Configuration changes

When adding or renaming an environment variable:

1. Update the relevant `.env.example`.
2. Update this configuration guide.
3. Add startup validation if required.
4. Update deployment configuration separately.
5. Never include real secrets in Git commits or pull requests.
