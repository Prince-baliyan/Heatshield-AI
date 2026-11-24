/**
 * HeatShield-AI End-to-End Browser Audit Suite
 *
 * Uses Chrome DevTools Protocol (CDP) via native Node.js WebSocket.
 * No third-party test runners or packages required.
 *
 * Environment variables:
 *   FRONTEND_URL: Base URL of running Vite frontend (default: http://localhost:5173)
 *   CDP_URL: Chrome remote debugging URL (default: http://127.0.0.1:9222)
 *   AUDIT_PASSWORD: Test user password (default: HeatShield-Audit-2026!)
 */

const http = require('http');

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9222';
const AUDIT_PASSWORD = process.env.AUDIT_PASSWORD || 'HeatShield-Audit-2026!';

function httpPut(url) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method: 'PUT' }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { resolve(data); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

class ChromeClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
    this.ready = new Promise((resolve) => {
      this.ws.onopen = resolve;
    });
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    };
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const msgId = this.id++;
      this.pending.set(msgId, { resolve, reject });
      this.ws.send(JSON.stringify({ id: msgId, method, params }));
    });
  }

  async eval(expr) {
    const res = await this.send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      throw new Error(`Eval exception: ${res.exceptionDetails.text} (${expr})`);
    }
    return res.result ? res.result.value : undefined;
  }

  async navigate(url) {
    await this.send('Page.navigate', { url });
    await delay(1200);
  }

  close() {
    this.ws.close();
  }
}

async function runBrowserAudit() {
  console.log('=== STARTING REAL BROWSER AUDIT ===');
  console.log(`Frontend URL: ${FRONTEND_URL}`);
  console.log(`Chrome CDP:   ${CDP_URL}`);

  const target = await httpPut(`${CDP_URL}/json/new?${FRONTEND_URL}/login`);
  const client = new ChromeClient(target.webSocketDebuggerUrl);
  await client.ready;
  await client.send('Page.enable');
  await client.send('Runtime.enable');
  await delay(1000);

  // STEP 1: LOGIN AS audituser1
  console.log('\n--- 1. Login Workflow ---');
  await client.navigate(`${FRONTEND_URL}/login`);
  await delay(1000);

  const loginTitle = await client.eval('document.title');
  console.log('Login Page Title:', loginTitle);

  // Fill in login credentials
  const loginResult = await client.eval(`
    (async () => {
      const usernameInput = document.querySelector('input[autocomplete="username"]');
      const passwordInput = document.querySelector('input[type="password"]');
      const submitBtn = document.querySelector('button[type="submit"]');

      if (!usernameInput || !passwordInput || !submitBtn) {
        return { success: false, reason: 'Inputs not found' };
      }

      const setVal = (el, val) => {
        const proto = Object.getPrototypeOf(el);
        const set = Object.getOwnPropertyDescriptor(proto, 'value').set;
        set.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };

      setVal(usernameInput, 'audituser1');
      setVal(passwordInput, '${AUDIT_PASSWORD}');
      submitBtn.click();
      return { success: true };
    })()
  `);
  console.log('Submitted login credentials:', loginResult);
  await delay(2000);

  const afterLoginUrl = await client.eval('window.location.pathname');
  console.log('Path after login:', afterLoginUrl);
  if (!afterLoginUrl.startsWith('/app')) {
    throw new Error('Login failed: did not redirect to /app');
  }
  console.log('✓ Successfully authenticated and navigated to /app');

  // STEP 2: OPEN LOCATIONS PAGE & INSPECT MAP MARKER
  console.log('\n--- 2. Locations Page & Map Marker Inspection ---');
  await client.navigate(`${FRONTEND_URL}/app/locations`);
  await delay(1500);

  const locationDetails = await client.eval(`
    (() => {
      const heading = document.querySelector('h1')?.innerText || '';
      const summaryCards = Array.from(document.querySelectorAll('.hs-display')).map(el => el.innerText);
      const coordsText = document.body.innerText.includes('28.996330') ? 'Found 28.996330' : 'Coords not found';
      const iframe = document.querySelector('iframe');
      const iframeSrc = iframe ? iframe.src : 'NO_IFRAME';
      const limitationBanner = document.body.innerText.includes('Ward boundaries and polygons are never invented');
      const readinessStatus = document.body.innerText.includes('ASSESSMENT READY') || document.body.innerText.includes('READY');

      return {
        heading,
        summaryCards,
        coordsText,
        iframeSrc,
        limitationBanner,
        readinessStatus
      };
    })()
  `);
  console.log('Locations Inspection Results:', JSON.stringify(locationDetails, null, 2));

  // Test toggling to Grid Radar mode
  const radarToggled = await client.eval(`
    (() => {
      const radarBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Grid Radar'));
      if (radarBtn) {
        radarBtn.click();
        return true;
      }
      return false;
    })()
  `);
  await delay(500);
  const radarVisible = await client.eval(`
    document.body.innerText.includes('Meerut City') && document.body.innerText.includes('28.996330° N')
  `);
  console.log('Grid Radar mode toggled:', radarToggled, 'Content verified:', radarVisible);

  // STEP 3: OPEN ASSESSMENT CREATION & CREATE STORED-DATA ASSESSMENT
  console.log('\n--- 3. Assessment Creation Workflow (Stored Observations) ---');
  await client.navigate(`${FRONTEND_URL}/app/assessments/new`);
  await delay(1500);

  const createPageReady = await client.eval(`
    (() => {
      const sourceSelect = document.querySelector('form select') || Array.from(document.querySelectorAll('select')).find(s => s.innerHTML.includes('Stored observations'));
      if (!sourceSelect) return { ready: false, reason: 'Select not found' };

      sourceSelect.value = 'observations';
      sourceSelect.dispatchEvent(new Event('change', { bubbles: true }));

      return { ready: true, selectedValue: sourceSelect.value };
    })()
  `);
  console.log('Selected stored observations source:', createPageReady);
  await delay(1000);

  // Submit the form
  const submitCreate = await client.eval(`
    (() => {
      const submitBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Create assessment'));
      if (!submitBtn) return { submitted: false, reason: 'Submit button not found' };
      if (submitBtn.disabled) return { submitted: false, reason: 'Submit button is disabled' };
      submitBtn.click();
      return { submitted: true };
    })()
  `);
  console.log('Submitted assessment creation:', submitCreate);
  await delay(2500);

  // Inspect the created assessment rendered on the page
  const assessmentResultPanel = await client.eval(`
    (() => {
      const text = document.body.innerText;
      const hasInsufficient = text.includes('INSUFFICIENT_DATA') || text.includes('Insufficient data');
      const hasBoundsWarning = text.includes('outside the provisional normalization bounds') || text.includes('normalization bounds');
      const hasTemp = text.includes('Air temperature');
      const hasHumidity = text.includes('Relative humidity');
      const viewDetailLink = document.querySelector('a[href*="/app/assessments/"]')?.getAttribute('href') || null;

      return {
        hasInsufficient,
        hasBoundsWarning,
        hasTemp,
        hasHumidity,
        viewDetailLink
      };
    })()
  `);
  console.log('Result panel content:', assessmentResultPanel);

  // Get the created assessment run ID from backend for audituser1
  const createdRunId = await client.eval(`
    (async () => {
      const res = await fetch('/api/v1/assessments/');
      const data = await res.json();
      return data.results && data.results[0] ? data.results[0].id : null;
    })()
  `);
  console.log('Created Assessment Run ID:', createdRunId);
  if (!createdRunId) {
    throw new Error('Failed to locate created assessment run ID.');
  }

  // STEP 4: OPEN ASSESSMENT DETAIL PAGE
  console.log(`\n--- 4. Assessment Detail Page (#${createdRunId}) ---`);
  await client.navigate(`${FRONTEND_URL}/app/assessments/${createdRunId}`);
  await delay(1500);

  const detailInfo = await client.eval(`
    (() => {
      const title = document.querySelector('h1')?.innerText || '';
      const text = document.body.innerText;
      const csvBtn = document.querySelector('a[href*="export/?format=csv"]');
      const printBtn = document.querySelector('a[href*="export/?format=html"]');
      const hasIndicators = text.includes('Air temperature') && text.includes('Relative humidity');
      const dataClass = text.includes('derived') ? 'derived' : 'unknown';

      return {
        title,
        hasCsvBtn: !!csvBtn,
        csvHref: csvBtn ? csvBtn.getAttribute('href') : null,
        hasPrintBtn: !!printBtn,
        printHref: printBtn ? printBtn.getAttribute('href') : null,
        hasIndicators,
        dataClass
      };
    })()
  `);
  console.log('Detail Page Verification:', JSON.stringify(detailInfo, null, 2));

  // STEP 5: DOWNLOAD CSV IN BROWSER CONTEXT
  console.log('\n--- 5. CSV Export Verification ---');
  const csvContent = await client.eval(`
    (async () => {
      const res = await fetch('/api/v1/assessments/${createdRunId}/export/?format=csv');
      const text = await res.text();
      return {
        status: res.status,
        contentType: res.headers.get('content-type'),
        disposition: res.headers.get('content-disposition'),
        firstLines: text.split('\\n').slice(0, 10).join('\\n')
      };
    })()
  `);
  console.log('CSV Export Response:');
  console.log('Status:', csvContent.status);
  console.log('Content-Type:', csvContent.contentType);
  console.log('Disposition:', csvContent.disposition);
  console.log('CSV Preview:\n', csvContent.firstLines);

  // STEP 6: PRINTABLE HTML REPORT IN BROWSER CONTEXT
  console.log('\n--- 6. Printable HTML Report Verification ---');
  const htmlContent = await client.eval(`
    (async () => {
      const res = await fetch('/api/v1/assessments/${createdRunId}/export/?format=html');
      const text = await res.text();
      return {
        status: res.status,
        contentType: res.headers.get('content-type'),
        hasPrintMediaCSS: text.includes('@media print') || text.includes('window.print()'),
        hasAssessmentTitle: text.includes('Assessment #${createdRunId}')
      };
    })()
  `);
  console.log('HTML Printable Report:');
  console.log('Status:', htmlContent.status);
  console.log('Content-Type:', htmlContent.contentType);
  console.log('Print features found:', htmlContent.hasPrintMediaCSS, htmlContent.hasAssessmentTitle);

  // STEP 7: TEST CROSS-USER ACCESS (User 2 trying to access User 1's assessment)
  console.log('\n--- 7. Cross-User Isolation Verification ---');
  await client.eval(`
    (async () => {
      await fetch('/api/v1/auth/logout/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': (await (await fetch('/api/v1/auth/csrf/')).json()).csrfToken
        }
      });
    })()
  `);
  await client.navigate(`${FRONTEND_URL}/login`);
  await delay(1000);

  // Log in as audituser2
  await client.eval(`
    (async () => {
      const usernameInput = document.querySelector('input[autocomplete="username"]');
      const passwordInput = document.querySelector('input[type="password"]');
      const submitBtn = document.querySelector('button[type="submit"]');

      const setVal = (el, val) => {
        const proto = Object.getPrototypeOf(el);
        const set = Object.getOwnPropertyDescriptor(proto, 'value').set;
        set.call(el, val);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };

      setVal(usernameInput, 'audituser2');
      setVal(passwordInput, '${AUDIT_PASSWORD}');
      submitBtn.click();
    })()
  `);
  await delay(2000);

  const user2CurrentPath = await client.eval('window.location.pathname');
  console.log('User 2 logged in, current path:', user2CurrentPath);

  // User 2 attempts to fetch audituser1's assessment detail via API
  const crossUserDetailAttempt = await client.eval(`
    (async () => {
      const res = await fetch('/api/v1/assessments/${createdRunId}/');
      return { status: res.status };
    })()
  `);
  console.log(`Cross-user detail fetch (User 2 fetching User 1 run #${createdRunId}):`, crossUserDetailAttempt.status, '(Expected 404)');

  // User 2 attempts to export audituser1's assessment via API
  const crossUserExportAttempt = await client.eval(`
    (async () => {
      const resCsv = await fetch('/api/v1/assessments/${createdRunId}/export/?format=csv');
      const resHtml = await fetch('/api/v1/assessments/${createdRunId}/export/?format=html');
      return { csvStatus: resCsv.status, htmlStatus: resHtml.status };
    })()
  `);
  console.log('Cross-user export attempts (User 2 exporting User 1 data):', crossUserExportAttempt, '(Expected 404, 404)');

  // User 2 checks their assessment history list
  const user2AssessmentList = await client.eval(`
    (async () => {
      const res = await fetch('/api/v1/assessments/');
      const data = await res.json();
      return { count: data.count, ids: (data.results || []).map(r => r.id) };
    })()
  `);
  console.log('User 2 assessment history list:', user2AssessmentList);
  const user1RunInUser2List = user2AssessmentList.ids.includes(createdRunId);
  console.log(`Did User 1 run #${createdRunId} appear in User 2 list?`, user1RunInUser2List, '(Expected false)');

  client.close();
  console.log('\n=== REAL BROWSER AUDIT COMPLETED SUCCESSFULLY ===');
}

runBrowserAudit().catch(err => {
  console.error('\n*** BROWSER AUDIT ERROR ***:', err);
  process.exit(1);
});
