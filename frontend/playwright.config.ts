import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
const system =
  process.env.CHROMIUM_PATH ??
  ["/usr/local/bin/chromium", "/usr/bin/chromium"].find(existsSync);
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 10000 },
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100",
    locale: "fa-IR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: {
      executablePath: system,
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
