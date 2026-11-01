const fs = require('node:fs');
const path = require('node:path');
const { chromium, expect } = require('../frontend/node_modules/@playwright/test');
const root = path.resolve(__dirname, '..');
(async () => {
  const credentials = JSON.parse(fs.readFileSync(0, 'utf8'));
  const base = process.env.AEGIS_UI_TEST_URL || 'http://127.0.0.1:3004';
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const login = await context.request.post(base + '/api/auth/login', { data: { key: credentials.key } });
    if (!login.ok()) throw new Error('Local UI login failed: ' + login.status());
    const health = await (await context.request.get(base + '/api/health')).json();
    const summary = health.red_attack_library;
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    const panel = page.locator('section.panel').filter({ has: page.getByRole('heading', {name: 'Red attack library'}) });
    await expect(panel).toBeVisible();
    await expect(panel.getByText(summary.unique_resources.toLocaleString('en-US'), {exact:true})).toBeVisible();
    await expect(panel.getByText(String(summary.executable_transforms), {exact:true})).toBeVisible();
    await panel.screenshot({path: path.join(root, '.runtime/red-library-expanded-ui.png')});
    await panel.locator('summary').click();
    await expect(panel.locator('table').nth(0).locator('tbody tr')).toHaveCount(summary.mechanism_groups);
    await expect(panel.locator('table').nth(3).locator('tbody tr')).toHaveCount(summary.research_inventory_count);
    await panel.getByRole('combobox',{name:'Source filter'}).selectOption('wildteaming');
    await panel.getByRole('textbox',{name:'Attack resource search'}).fill('translation');
    await panel.getByRole('button',{name:'Search',exact:true}).click();
    const results = panel.locator('table').nth(2);
    await expect(results.locator('tbody tr')).toHaveCount(10);
    await results.getByRole('button').first().click();
    await expect(panel.locator('pre')).toContainText(/translation/i);
    const firstTitle = await results.getByRole('button').first().textContent();
    await panel.getByRole('button',{name:'Next'}).click();
    await expect(results.locator('tbody tr')).toHaveCount(10);
    await expect(results.getByRole('button').first()).not.toHaveText(firstTitle);
    await panel.getByRole('textbox',{name:'Research inventory filter'}).fill('deepteam');
    await expect(panel.locator('table').nth(3).locator('tbody tr')).toHaveCount(2);
    await expect(panel.locator('table').nth(3).getByRole('link',{name:'DeepTeam',exact:true})).toBeVisible();
    if (errors.length) throw new Error('UI runtime errors: ' + errors.join('; '));
    const report = {ui:'passed',resources:summary.unique_resources,transforms:summary.executable_transforms,
      methods:summary.mechanism_groups,tactics:summary.tactic_records,inventory:summary.research_inventory_count,
      search:true,pagination:true,fullResourceRead:true,inventoryFilter:true,runtimeErrors:errors.length,
      screenshot:'.runtime/red-library-expanded-ui.png',url:base};
    fs.writeFileSync(path.join(root,'.runtime/red-library-expanded-ui.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
    await context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
