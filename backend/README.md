# Backend

Django REST Framework API scaffold.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env`, then:
```bash
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Health endpoint: `GET http://127.0.0.1:8000/api/v1/health/`

Student authentication routes:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`

Request and response examples, validation errors, and the complete frontend
session integration contract are in [`../docs/API_SPEC.md`](../docs/API_SPEC.md).
Before registration, login, or logout, fetch the CSRF endpoint, retain its
cookie, and send `csrfToken` in the `X-CSRFToken` header. Browser clients must
include cookies (`credentials: "include"` for cross-origin requests).

For local development, set `DJANGO_DEBUG=True` and configure the local frontend
origins in both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`. For production,
set `DJANGO_DEBUG=False`, a secret `DJANGO_SECRET_KEY`, the deployment's exact
`DJANGO_ALLOWED_HOSTS` and frontend origins, and serve over HTTPS. Session and
CSRF cookies default to secure outside debug mode; configure
`DJANGO_SECURE_SSL_REDIRECT` and `DJANGO_SECURE_HSTS_SECONDS` for the deployment.
