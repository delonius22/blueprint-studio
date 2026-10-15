// T-20: the end-to-end smoke test against the full stack with a scripted fake model
// (docker-compose.e2e.yml). Five workers drive five sessions at once (NFR-12).
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  workers: 5,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: { baseURL: "http://localhost:3100", acceptDownloads: true, viewport: { width: 1280, height: 900 } },
});
