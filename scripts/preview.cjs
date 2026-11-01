// Open only the recorded, verified English live platform.
const { chromium } = require('../frontend/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const { loadEnvConfig } = require('../frontend/node_modules/@next/env');
const root = path.resolve(__dirname, '..');

(async () => {
  const statePath = path.join(root, '.runtime', 'live-workspace.json');
  if (!fs.existsSync(statePath)) throw new Error('Run Open MAIN Build.cmd first.');
  const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
  if (state.status !== 'ready') throw new Error('The live workspace is not ready. Run Open MAIN Build.cmd.');
  const health = await (await fetch(state.platform_url + 'api/health')).json();
  if (health.fixture_environment || health.instance_id !== state.instance_id) throw new Error('The recorded address is not the current live platform.');
  loadEnvConfig(root);
  const key = process.env.AEGIS_ADMIN_TOKEN;
  if (!key) throw new Error('AEGIS_ADMIN_TOKEN is missing.');
  const context = await chromium.launchPersistentContext(path.join(root, '.runtime', 'preview-profile'), {
    channel: 'msedge', headless: false, viewport: null,
  });
  const page = context.pages()[0] || await context.newPage();
  await page.goto(state.platform_url);
  if (await page.locator('html').getAttribute('lang') !== 'en') {
    await context.close();
    throw new Error('The running interface is not English.');
  }
  if (await page.getByLabel('Access key', { exact: true }).isVisible()) {
    await page.getByLabel('Access key', { exact: true }).fill(key);
    await page.getByRole('button', { name: 'Open workspace', exact: true }).click();
  }
  await page.getByRole('heading', { name: 'Your AI security workspace', exact: true }).waitFor();
  await context.waitForEvent('close', { timeout: 0 });
})().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
