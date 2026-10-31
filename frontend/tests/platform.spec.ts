import { expect, test, Page } from "@playwright/test";

const key = "aegis-offline-demo-access-key-2026-only";
async function login(page: Page, accessKey = key) {
  await page.goto("/");
  await page.getByLabel("Erişim anahtarı", { exact: true }).fill(accessKey);
  await page.getByRole("button", { name: "Çalışma alanını aç" }).click();
  await expect(page.getByRole("heading", { name: "Güvenlik çalışma alanınız" })).toBeVisible();
}

test("three fixture scenarios, evidence, repair comparison and export render", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await login(page);
  await expect(page.getByText(/TEST FIXTURE ORTAMI/)).toBeVisible();
  const health = await page.request.get("/api/health");
  expect((await health.json()).fixture_environment).toBe(true);
  const campaigns = await (await page.request.get("/api/campaigns")).json();
  const campaign = campaigns.find((c: { findings: number }) => c.findings === 3);
  expect(campaign).toBeTruthy();
  const id = campaign.id;
  for (const [route, title] of [["campaign", "Kampanya konsolu"], ["coverage", "Kapsam haritası"], ["findings", "Kanıtlanmış bulgular"], ["repair", "Repair Lab"], ["verification", "Bağımsız doğrulama"], ["report", "Deney raporu"]]) {
    await page.goto(`/${route}?campaign=${id}`);
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  }
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Kanıt paketi indir", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("aegis-evidence.json");
  await page.goto(`/verification?campaign=${id}`);
  await expect(page.locator(".stats").getByText("Kapsamda doğrulandı", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../docs/screenshots/verification.png", fullPage: true });
  await page.goto("/");
  await page.screenshot({ path: "../docs/screenshots/overview.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("target wizard and campaign start use the authenticated API", async ({ page }) => {
  await login(page);
  await page.goto("/target");
  await page.getByRole("button", { name: "Hedef ekle", exact: true }).click();
  await page.getByRole("button", { name: "Devam", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("gerçek model sürümü gerekli");
  await page.getByLabel("Model", { exact: true }).fill("offline-fixture");
  await page.getByLabel("Gerçek model sürümü", { exact: true }).fill("fixture-browser-v2");
  await page.getByLabel("Yerel endpoint", { exact: true }).fill("http://localhost/v1");
  await page.getByRole("button", { name: "Devam", exact: true }).click();
  await page.getByRole("button", { name: "Devam", exact: true }).click();
  await page.getByRole("button", { name: "Devam", exact: true }).click();
  await page.getByRole("button", { name: "Hedefi kaydet", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.goto("/campaign");
  await page.getByRole("button", { name: "Yeni kampanya", exact: true }).click();
  await page.getByRole("button", { name: "Tüm protokol ayarlarını düzenle" }).click();
  const jsonField = page.getByLabel("Tam kampanya protokolü");
  const spec = JSON.parse(await jsonField.inputValue());
  const targets = await (await page.request.get("/api/targets")).json();
  spec.target_id = targets[0].id;
  Object.assign(spec, { languages: ["en"], properties: ["tool_authorization"], families: ["tool_misuse"], minimum_tests_per_cell: 1, max_discovery_attempts: 1, max_repair_groups: 1 });
  await jsonField.fill(JSON.stringify(spec));
  await page.getByRole("button", { name: "Kampanyayı oluştur", exact: true }).click();
  await expect(page.getByRole("button", { name: "Keşfi başlat" })).toBeVisible();
  await page.getByRole("button", { name: "Keşfi başlat" }).click();
  await expect.poll(async () => {
    const cid = new URL(page.url()).searchParams.get("campaign");
    return (await (await page.request.get(`/api/campaigns/${cid}`)).json()).state;
  }, { timeout: 45000 }).toBe("completed");
});

test("viewer access cannot launch campaigns or read audit records", async ({ page }) => {
  const issued = await page.request.post("/api/users", { headers: { Authorization: `Bearer ${key}` }, data: { name: "Browser viewer", role: "viewer", workspace: "default" } });
  expect(issued.status()).toBe(201);
  await login(page, (await issued.json()).access_key);
  await expect(page.getByRole("button", { name: "Yeni kampanya" })).toBeDisabled();
  expect((await page.request.get("/api/audit")).status()).toBe(403);
  expect((await page.request.post("/api/campaigns", { headers: { "Idempotency-Key": "viewer-rejected" }, data: { target_id: "invalid" } })).status()).toBe(403);
});
