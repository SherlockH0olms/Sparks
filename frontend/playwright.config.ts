import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const python = process.platform === "win32"
  ? path.join(root, ".venv-win", "Scripts", "python.exe")
  : path.join(root, ".venv", "bin", "python");

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  fullyParallel: false,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:3003", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `"${python}" scripts/run.py --mode demo --api-port 8003 --web-port 3003`,
    cwd: root,
    url: "http://127.0.0.1:3003",
    timeout: 120000,
    reuseExistingServer: process.env.AEGIS_E2E_REUSE === "true",
  },
});
