import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: true,
  use: {baseURL: 'http://127.0.0.1:4173/preview/', browserName: 'chromium', trace: 'retain-on-failure', screenshot: 'on'},
  webServer: {
    command: 'node tests/helpers/browser-site.mjs',
    url: 'http://127.0.0.1:4173/preview/',
    reuseExistingServer: false,
    timeout: 180000,
  },
});
