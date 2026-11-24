# HeatShield-AI End-to-End Browser Audit Suite

This test suite performs a headless browser test of the complete HeatShield-AI user journey using Google Chrome via the Chrome DevTools Protocol (CDP) over Node.js native WebSockets.

No third-party testing frameworks (Playwright, Puppeteer, Cypress) are required.

## Covered Workflow
1. **Authentication:** User login at `/login`, CSRF cookie handling, and redirection to `/app`.
2. **Locations & Map Inspection:** Loads `/app/locations`, verifies summary metrics, OSM representative marker (`28.996330, 77.706192`), limitation banner (*"Ward boundaries and polygons are never invented"*), and Grid Radar toggle.
3. **Assessment Creation:** Creates a stored-observation assessment (`source="observations"`), verifies engine execution, and confirms transparent failure mode handling.
4. **Assessment Detail:** Loads `/app/assessments/<id>`, confirms indicator breakdown, provenance, and data class badges.
5. **CSV Export:** Downloads structured RFC 4180 audit report at `/api/v1/assessments/<id>/export/?format=csv`.
6. **Printable HTML Report:** Opens standalone print-optimized report at `/api/v1/assessments/<id>/export/?format=html` with `@media print` CSS.
7. **Cross-User Isolation:** Signs in as `audituser2`, attempts to fetch `audituser1`'s assessment detail and export URLs (asserts `404 Not Found`), and confirms user 1's records do not appear in user 2's assessment history.

## Prerequisites
1. **Backend Server:** Django running on `http://127.0.0.1:8000`:
   ```bash
   cd backend
   source .venv/bin/activate
   python manage.py runserver 127.0.0.1:8000
   ```
2. **Frontend Server:** Vite dev server running on `http://localhost:5173`:
   ```bash
   cd frontend
   npm run dev -- --port 5173
   ```
3. **Test Users:** Two test accounts (`audituser1` and `audituser2`):
   ```bash
   cd backend
   .venv/bin/python manage.py shell -c "
   from django.contrib.auth import get_user_model
   User = get_user_model()
   for name in ['audituser1', 'audituser2']:
       u, _ = User.objects.get_or_create(username=name, email=f'{name}@example.com')
       u.set_password('HeatShield-Audit-2026!')
       u.save()
   "
   ```
4. **Google Chrome / Chromium:** Installed at `/usr/bin/google-chrome` or `/usr/bin/chromium`.

## Running the E2E Test
```bash
# Launch Chrome in headless debugging mode
killall chrome google-chrome 2>/dev/null || true
google-chrome --headless=new --remote-debugging-port=9222 --no-sandbox &
CHROME_PID=$!
sleep 2

# Execute the test script
node tests/e2e/run_browser_test.js
STATUS=$?

# Cleanup Chrome process
kill $CHROME_PID 2>/dev/null || true
exit $STATUS
```

## Environment Variables
- `FRONTEND_URL`: Custom frontend URL (default: `http://localhost:5173`)
- `CDP_URL`: Custom Chrome remote debugging URL (default: `http://127.0.0.1:9222`)
- `AUDIT_PASSWORD`: Test account password (default: `HeatShield-Audit-2026!`)
