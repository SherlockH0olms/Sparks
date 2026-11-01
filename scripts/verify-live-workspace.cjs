const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('../frontend/node_modules/@playwright/test');
const { loadEnvConfig } = require('../frontend/node_modules/@next/env');
const root = path.resolve(__dirname, '..');
const arg = process.argv.indexOf('--base-url');
const statePath = path.join(root, '.runtime', 'live-workspace.json');
const state = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, 'utf8')) : null;
const baseValue = arg >= 0 ? process.argv[arg + 1] : state?.status === 'ready' ? state.platform_url : null;
const base = (baseValue || '').replace(/\/$/, '');
const instanceArg = process.argv.indexOf('--instance-id');
const expectedInstance = instanceArg >= 0 ? process.argv[instanceArg + 1] : arg < 0 ? state?.instance_id : null;
const result = { base_url: base, ready: false, pages: [], issues: [] };
let browser;

(async () => {
  if (!base) throw new Error('No running workspace address is recorded. Run Open MAIN Build.cmd or specify --base-url.');
  const response = await fetch(base + '/campaign', { signal: AbortSignal.timeout(8000) });
  const html = await response.text();
  const language = html.match(/<html[^>]*\blang="([^"]+)"/)?.[1];
  if (response.status !== 200) result.issues.push(`/campaign returned HTTP ${response.status}.`);
  if (language !== 'en') result.issues.push(`The running page declares language ${language || 'unknown'}; the English release is not active.`);
  const scripts = [...new Set([...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map(m => m[1]))];
  for (const script of scripts) {
    const r = await fetch(new URL(script, base), { signal: AbortSignal.timeout(8000) });
    if (!r.ok) result.issues.push(`JavaScript ${script} returned HTTP ${r.status}.`);
  }
  if (result.issues.length) throw new Error('The running interface failed its initial checks.');

  const healthResponse = await fetch(base + '/api/health', { signal: AbortSignal.timeout(8000) });
  const health = await healthResponse.json();
  if (!healthResponse.ok || health.version !== '2.0.0' || health.fixture_environment) throw new Error('The interface is not connected to the live AEGIS backend.');
  if (expectedInstance && health.instance_id !== expectedInstance) throw new Error('The interface is connected to a different backend instance.');
  loadEnvConfig(root);
  const key = process.env.AEGIS_ADMIN_TOKEN;
  if (!key) throw new Error('AEGIS_ADMIN_TOKEN is missing; sign-in could not be verified.');
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', e => result.issues.push(e.message));
  page.on('response', r => {
    if (r.status() >= 400 && new URL(r.url()).pathname.startsWith('/_next/')) result.issues.push(`HTTP ${r.status()} for ${new URL(r.url()).pathname}.`);
  });
  const login = await page.request.post(base + '/api/auth/login', { data: { key }, headers: { Origin: base } });
  if (!login.ok()) throw new Error(`Sign-in returned HTTP ${login.status()}.`);
  const targetsResponse = await page.request.get(base + '/api/targets');
  const targets = await targetsResponse.json();
  if (!targetsResponse.ok() || !targets.some(t => t.model === 'granite-4.2-8b')) throw new Error('The live registry does not contain the saved Granite target.');
  if (targets.some(t => !t.display_name)) throw new Error('Readable target names are missing from the running backend.');
  result.targets = targets.map(t => ({ name: t.display_name, model: t.model, latest: t.is_latest_for_model }));
  const campaignsResponse = await page.request.get(base + '/api/campaigns');
  const campaigns = await campaignsResponse.json();
  if (campaigns.some(c => !/^Test \d+$/.test(c.display_name || ''))) throw new Error('Readable test numbers are missing from the running backend.');
  const campaign = campaigns.find(c => c.state === 'completed') || campaigns[0];
  const suffix = campaign ? '?campaign=' + encodeURIComponent(campaign.id) : '';
  for (const route of ['/', '/target', '/campaign', '/coverage', '/findings', '/repair', '/verification', '/report', '/guide', '/audit']) {
    const r = await page.goto(base + route + suffix);
    if (!r || r.status() !== 200) throw new Error(`${route} did not return HTTP 200.`);
    await page.locator('main h1').waitFor({ timeout: 15000 });
    const lang = await page.locator('html').getAttribute('lang');
    if (lang !== 'en') throw new Error(`${route} is not declared as English.`);
    const nav = await page.locator('aside nav').innerText();
    if (!nav.includes('Overview') || !nav.includes('Targets') || !nav.includes('Campaign')) throw new Error(`${route} does not show the English navigation.`);
    result.pages.push({ path: route, status: r.status(), heading: await page.locator('main h1').innerText() });
    if (route === '/target') {
      await page.getByLabel('Granite URL', { exact: true }).waitFor();
      await page.getByRole('button', { name: 'Connect Granite', exact: true }).waitFor();
    }
  }
  if (campaign) {
    const findingsResponse = await page.request.get(base + '/api/campaigns/' + campaign.id + '/findings');
    const findings = await findingsResponse.json();
    if (findingsResponse.ok() && findings.length) {
      const route = '/findings/' + findings[0].id;
      const r = await page.goto(base + route + suffix);
      if (!r || r.status() !== 200) throw new Error('The finding detail page did not return HTTP 200.');
      await page.locator('main h1').waitFor({ timeout: 15000 });
      result.pages.push({ path: route, status: r.status(), heading: await page.locator('main h1').innerText() });
    }
  }
  if (result.issues.length) throw new Error('The live pages reported JavaScript errors.');
  await page.goto(base + '/campaign' + suffix);
  await page.getByRole('button', { name: 'New campaign', exact: true }).click();
  const targetOptions = await page.getByLabel('Target', { exact: true }).locator('option').allTextContents();
  if (new Set(targetOptions).size !== targetOptions.length || !targetOptions.some(t => t.includes('Latest'))) throw new Error('Target selection does not distinguish registrations and the latest model.');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  const testOptions = await page.getByLabel('Active campaigns', { exact: true }).locator('option').allTextContents();
  if (testOptions.slice(1).some(t => !t.startsWith('Test '))) throw new Error('Campaign selection still shows technical IDs.');
  await page.goto(base + '/target' + suffix);
  await page.getByRole('button', { name: 'Add target', exact: true }).click();
  if (await page.getByLabel('Pinned model version', { exact: true }).inputValue() !== '') throw new Error('The optional model version did not start empty.');
  await page.getByLabel('Model', { exact: true }).fill('granite-4.2-8b');
  await page.getByRole('dialog').getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel('Document editor', { exact: true }).waitFor();
  await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click();
  result.readable_names = true;
  result.optional_model_version = true;
  await page.goto(base + '/');
  await page.locator('main h1').waitFor({ timeout: 15000 });
  await page.screenshot({ path: path.join(root, '.runtime', 'live-platform-verified.png'), fullPage: true });
  result.ready = true;
  console.log(`Verified the actual English platform at ${base}: sign-in, saved Granite target, and ${result.pages.length} pages.`);
})().catch(e => {
  result.issues.push(e.message);
  console.error(result.issues.join('\n'));
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  fs.mkdirSync(path.join(root, '.runtime'), { recursive: true });
  fs.writeFileSync(path.join(root, '.runtime', 'live-platform-verification.json'), JSON.stringify(result, null, 2));
});
