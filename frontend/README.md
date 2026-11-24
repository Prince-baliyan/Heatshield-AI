# Frontend

React + Vite + TypeScript + Tailwind CSS.

## Setup
```bash
npm install
cp .env.example .env.local
npm run dev
```

`VITE_API_BASE_URL` configures the centralized API client and defaults to
`/api/v1`. In local development Vite proxies that path to
`VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`), avoiding browser CORS
requirements. For a separately hosted backend, set `VITE_API_BASE_URL` to its
full `/api/v1` URL and allow the frontend origin in Django CORS. Vite reads
`.env.local` when it starts.

Run the backend in a separate terminal from `backend/`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

The public landing page does not expose the assessment workspace. The API
client and reusable workspace component remain available for future application
integration; authentication and an authenticated application area are not yet
implemented. Backend weather responses and assessments marked `illustrative`
are demos, not observed or verified real-world conditions. Assessment methods
and categories are provisional; consult the backend warnings and data class
alongside any result.

Production build:
```bash
npm run build
```
