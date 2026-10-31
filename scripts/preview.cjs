// Open the requested local product preview. Provider credentials never leave the API.
const { chromium } = require('../frontend/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

async function login(page, url, key) {
  await page.goto(url);
  await page.getByLabel('Erişim anahtarı', { exact: true }).fill(key);
  await page.getByRole('button', { name: 'Çalışma alanını aç' }).click();
  await page.getByRole('heading', { name: 'Güvenlik çalışma alanınız' }).waitFor();
}

(async () => {
  const context = await chromium.launchPersistentContext(path.join(root, '.runtime', 'preview-profile'), {
    channel: 'msedge', headless: false, viewport: null,
  });
  const config = fs.readFileSync(path.join(root, '.env'), 'utf8');
  const key = config.split(/\r?\n/).find(line => line.startsWith('AEGIS_ADMIN_TOKEN=')).slice(18).trim().replace(/^["']|["']$/g, '');
  const production = context.pages()[0] || await context.newPage();
  await login(production, 'http://127.0.0.1:3002', key);
  const demo = await context.newPage();
  await login(demo, 'http://localhost:3003', 'aegis-offline-demo-access-key-2026-only');
  const campaigns = await (await demo.request.get('http://localhost:3003/api/campaigns')).json();
  const main = campaigns.find(c => c.findings === 3);
  await demo.goto('http://localhost:3003/verification?campaign=' + main.id);
  await context.waitForEvent('close', { timeout: 0 });
})().catch(() => { process.stderr.write('Preview browser could not open. Use the URLs in README.md.\n'); process.exitCode = 1; });
