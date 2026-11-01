import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const python = process.platform === "win32"
  ? path.join(root, ".venv-win", "Scripts", "python.exe")
  : path.join(root, ".venv", "bin", "python");
const webPort = process.env.AEGIS_E2E_WEB_PORT || "3003";
const apiPort = process.env.AEGIS_E2E_API_PORT || "8003";
const baseURL = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  fullyParallel: false,
  reporter: "list",
  use: { baseURL, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `"${python}" scripts/run.py --mode demo --api-port ${apiPort} --web-port ${webPort}`,
    cwd: root,
    url: baseURL,
    timeout: 120000,
    reuseExistingServer: process.env.AEGIS_E2E_REUSE === "true",
  },
});
