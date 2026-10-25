import { defineConfig } from "@playwright/test";

const port = process.env.LEARNING_TEST_PORT ?? "4187";
export default defineConfig({
  testDir: "tests/browser",
  forbidOnly: true,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: "list",
  use: {
    browserName: "chromium",
    baseURL: "http://127.0.0.1:" + port,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "node tools/browser-server.mjs",
    url: "http://127.0.0.1:" + port,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
