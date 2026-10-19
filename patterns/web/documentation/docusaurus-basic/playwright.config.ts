import {defineConfig, type PlaywrightTestConfig} from '@playwright/test';
import settings from './site.settings.json';
import {resolveConfig} from './setup/lib/runtime.cjs';
const options = resolveConfig(settings).playwright as PlaywrightTestConfig;
export default defineConfig({
  ...options,
  webServer: options.webServer ?? {
    command: 'node tests/helpers/temporary-site.mjs serve',
    url: options.use?.baseURL ?? 'http://127.0.0.1:4186/preview/',
    reuseExistingServer: false,
    timeout: 180000,
  },
});
