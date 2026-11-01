import { expect, test, Page } from "@playwright/test";

const key = "aegis-offline-demo-access-key-2026-only";
async function login(page: Page, accessKey = key) {
  await page.goto("/");
  await page.getByLabel("Access key", { exact: true }).fill(accessKey);
  await page.getByRole("button", { name: "Open workspace" }).click();
  await expect(page.getByRole("heading", { name: "Your AI security workspace" })).toBeVisible();
}

test("three fixture scenarios, evidence, repair comparison and export render", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await login(page);
  await expect(page.getByText(/TEST FIXTURE/)).toBeVisible();
  const health = await page.request.get("/api/health");
  expect((await health.json()).fixture_environment).toBe(true);
  const campaigns = await (await page.request.get("/api/campaigns")).json();
  const campaign = campaigns.find((c: { findings: number }) => c.findings === 3);
  expect(campaign).toBeTruthy();
  const id = campaign.id;
  for (const [route, title] of [["campaign", "Campaign console"], ["coverage", "Coverage map"], ["findings", "Confirmed findings"], ["repair", "Repair Lab"], ["verification", "Independent verification"], ["report", "Experiment report"]]) {
    await page.goto(`/${route}?campaign=${id}`);
    await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  }
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download evidence package", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("aegis-evidence.json");
  await page.goto(`/verification?campaign=${id}`);
  await expect(page.locator(".stats").getByText("Validated in scope", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../.runtime/english-ui/verification.png", fullPage: true });
  await page.goto("/");
  await page.screenshot({ path: "../.runtime/english-ui/overview.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("target wizard and campaign start use the authenticated API", async ({ page }) => {
  await login(page);
  await page.goto("/target");
  await page.getByRole("button", { name: "Add target", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("pinned model version");
  await page.getByLabel("Model", { exact: true }).fill("offline-fixture");
  await page.getByLabel("Pinned model version", { exact: true }).fill("fixture-browser-v2");
  await page.getByLabel("API base URL", { exact: true }).fill("http://localhost/v1");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Save target", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.goto("/campaign");
  await page.getByRole("button", { name: "New campaign", exact: true }).click();
  await expect(page.getByRole("checkbox", { name: "English", exact: true })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Turkish", exact: true })).not.toBeChecked();
  await page.getByLabel("Test depth", { exact: true }).selectOption("smoke");
  await page.getByRole("button", { name: "Advanced protocol settings" }).click();
  const jsonField = page.getByLabel("Full campaign protocol");
  const spec = JSON.parse(await jsonField.inputValue());
  const targets = await (await page.request.get("/api/targets")).json();
  spec.target_id = targets[0].id;
  Object.assign(spec, { languages: ["en"], properties: ["tool_authorization"], families: ["tool_misuse"], minimum_tests_per_cell: 1, max_discovery_attempts: 1, max_repair_groups: 1 });
  await jsonField.fill(JSON.stringify(spec));
  await page.getByRole("button", { name: "Create campaign", exact: true }).click();
  await expect(page.getByRole("button", { name: "Start campaign" })).toBeVisible();
  await page.getByRole("button", { name: "Start campaign" }).click();
  await expect.poll(async () => {
    const cid = new URL(page.url()).searchParams.get("campaign");
    return (await (await page.request.get(`/api/campaigns/${cid}`)).json()).state;
  }, { timeout: 45000 }).toBe("completed");
});

test("viewer access cannot launch campaigns or read audit records", async ({ page }) => {
  const issued = await page.request.post("/api/users", { headers: { Authorization: `Bearer ${key}` }, data: { name: "Browser viewer", role: "viewer", workspace: "default" } });
  expect(issued.status()).toBe(201);
  await login(page, (await issued.json()).access_key);
  await expect(page.getByRole("button", { name: "New campaign" })).toBeDisabled();
  expect((await page.request.get("/api/audit")).status()).toBe(403);
  expect((await page.request.post("/api/campaigns", { headers: { "Idempotency-Key": "viewer-rejected" }, data: { target_id: "invalid" } })).status()).toBe(403);
});

test("English walkthrough covers the complete workflow and preserves campaign context", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByText("First time using AEGIS?", { exact: true }).click();
  await expect(page.locator(".login-help")).toContainText("AEGIS_ADMIN_TOKEN");
  await login(page);
  const campaigns = await (await page.request.get("/api/campaigns")).json();
  const id = campaigns.find((c: { findings: number }) => c.findings === 3).id;
  await page.goto(`/guide?step=setup&campaign=${id}`);
  await expect(page.getByRole("heading", { name: "How to use AEGIS Loop", exact: true })).toBeVisible();
  const steps = page.getByRole("navigation", { name: "Walkthrough steps" });
  await expect(steps.getByRole("button")).toHaveCount(9);
  await expect(page.getByRole("button", { name: "Previous step", exact: true })).toBeDisabled();
  await page.getByText("Where to enter your keys and endpoints", { exact: true }).click();
  await expect(page.locator(".guide-current .guide-config pre")).toContainText("AEGIS_RED_API_KEY");
  await expect(page.locator(".guide-current .guide-config pre")).toContainText("AEGIS_JUDGE_API_KEY");
  for (const step of ["target", "campaign", "run", "coverage", "findings", "repair", "verification", "report"]) {
    await page.getByRole("button", { name: "Next step", exact: true }).click();
    await expect.poll(() => new URL(page.url()).searchParams.get("step")).toBe(step);
    expect(new URL(page.url()).searchParams.get("campaign")).toBe(id);
    await expect(steps.locator('[aria-current="step"]')).toContainText(String(["setup", "target", "campaign", "run", "coverage", "findings", "repair", "verification", "report"].indexOf(step) + 1).padStart(2, "0"));
    await expect(page.locator(".guide-current").getByRole("heading", { name: "What to do", exact: true })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "Next step", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Previous step", exact: true }).click();
  await expect(page.locator("#guide-current-title")).toContainText("independent comparison");
  await page.reload();
  await expect(page.locator("#guide-current-title")).toContainText("independent comparison");
  await page.getByLabel("Find a term", { exact: true }).fill("ASR");
  await expect(page.locator(".guide-glossary dt")).toHaveCount(1);
  await expect(page.locator(".guide-glossary")).toContainText("Observed violations divided by valid security tests");
  await page.getByLabel("Find a term", { exact: true }).fill("no-such-platform-term");
  await expect(page.getByText("No terms match your search.", { exact: true })).toBeVisible();
  await page.getByLabel("Find a term", { exact: true }).clear();
  await page.screenshot({ path: "../.runtime/english-ui/guide-desktop.png", fullPage: true });
  await page.goto(`/target?campaign=${id}`);
  await page.locator(".page-help summary").click();
  await expect(page.locator(".page-help")).toContainText("Test connection before creating a campaign");
  await page.getByRole("link", { name: "Detailed walkthrough" }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("step")).toBe("target");
  expect(new URL(page.url()).searchParams.get("campaign")).toBe(id);
  expect(errors).toEqual([]);
});

test("mobile guide and labelled navigation stay readable without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.getByRole("link", { name: "How to use", exact: true }).click();
  await expect(page.getByRole("heading", { name: "How to use AEGIS Loop", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "How to use", exact: true }).locator("span")).toBeVisible();
  await page.getByRole("navigation", { name: "Walkthrough steps" }).getByRole("button", { name: /Choose the test scope and budget/ }).click();
  await expect(page.locator("#guide-current-title")).toContainText("Choose the test scope and budget");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../.runtime/english-ui/guide-mobile.png", fullPage: true });
  await page.getByRole("link", { name: "Open Campaign", exact: false }).click();
  await expect(page.getByRole("heading", { name: "Campaign console", exact: true })).toBeVisible();
});

test("deployment options, native Ollama, and write-only target credentials", async ({page})=>{
  await login(page);
  await page.goto("/target");
  await page.getByRole("button",{name:"Add target",exact:true}).click();
  const deployment=page.getByLabel("Deployment type",{exact:true});
  await expect(deployment.locator("option")).toHaveCount(7);
  for(const [kind,url] of [["lan","192.168.1.50"],["tailscale","100.64.0.20"],["cloudflare","https://"],["ngrok","ngrok"],["notebook","ngrok"],["custom","https://"],["local","127.0.0.1"]]){
    await deployment.selectOption(kind);
    await expect(page.getByLabel("API base URL",{exact:true})).toHaveValue(new RegExp(url));
  }
  await page.getByLabel("API format",{exact:true}).selectOption("ollama");
  await expect(page.getByLabel("API base URL",{exact:true})).toHaveValue("http://127.0.0.1:11434");
  await page.getByLabel("API format",{exact:true}).selectOption("openai_compatible");
  await deployment.selectOption("cloudflare");
  await page.getByLabel("Model authentication",{exact:true}).selectOption("key");
  await page.getByLabel("Target API key",{exact:true}).fill("browser-target-private-key");
  await page.getByLabel("Access authentication",{exact:true}).selectOption("token");
  await page.getByLabel("Access client ID",{exact:true}).fill("browser-access-id");
  await page.getByLabel("Access client secret",{exact:true}).fill("browser-access-private-secret");
  await page.getByLabel("Model",{exact:true}).fill("offline-fixture");
  await page.getByLabel("Pinned model version",{exact:true}).fill("browser-cloudflare-v1");
  for(let i=0;i<3;i++) await page.getByRole("button",{name:"Continue",exact:true}).click();
  const review=page.getByRole("dialog");
  await expect(review).toContainText("Entered; hidden");
  await expect(review).not.toContainText("browser-target-private-key");
  await expect(review).not.toContainText("browser-access-private-secret");
  await page.screenshot({path:"../.runtime/english-ui/target-review.png",fullPage:true});
  await page.getByRole("button",{name:"Save target",exact:true}).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const targets=await(await page.request.get("/api/targets")).json();
  const saved=targets.find((t:{model_revision:string})=>t.model_revision==="browser-cloudflare-v1");
  expect(saved.connection_kind).toBe("cloudflare");
  expect(saved.authentication_configured).toBe(true);
  expect(saved.api_key).toBeUndefined();
});

test("report presentation preview and binary exports work on desktop and mobile",async({page})=>{
  await login(page);
  const campaigns=await(await page.request.get("/api/campaigns")).json();
  const id=campaigns.find((c:{findings:number})=>c.findings===3).id;
  await page.goto(`/report?campaign=${id}`);
  const preview=page.frameLocator('iframe[title="AI security and remediation report preview"]');
  await expect(preview.getByRole("heading",{name:"Evidence-backed remediation",exact:true})).toBeVisible();
  await expect(preview.getByRole("heading",{name:"MITRE ATLAS and NIST evidence",exact:true})).toBeVisible();
  for(const [name,filename] of [["Download PDF","aegis-report.pdf"],["Download PowerPoint","aegis-report.pptx"],["Download remediation bundle","aegis-remediation.zip"]]){
    const promise=page.waitForEvent("download");
    await page.getByRole("link",{name,exact:true}).click();
    const download=await promise;
    expect(download.suggestedFilename()).toBe(filename);
    expect(await download.failure()).toBeNull();
  }
  await page.screenshot({path:"../.runtime/english-ui/report-desktop.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:"../.runtime/english-ui/report-mobile.png",fullPage:true});
});
