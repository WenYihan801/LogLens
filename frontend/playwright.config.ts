import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run against a live stack (local mode, not read-only).
 *   docker compose up -d            # or: make dev-backend + make dev-frontend
 *   npm run e2e                     # E2E_BASE_URL defaults to http://localhost:5173
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1, // the specs share one database
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      // PW_CHANNEL=chrome uses an installed Google Chrome instead of the downloaded Chromium.
      use: { ...devices["Desktop Chrome"], ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}) },
    },
  ],
});
