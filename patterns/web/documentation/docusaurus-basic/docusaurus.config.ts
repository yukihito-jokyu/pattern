import type {Config} from '@docusaurus/types';
import {themes} from 'prism-react-renderer';
import settings from './site.settings.json';
import {resolveConfig} from './setup/lib/runtime.cjs';

const resolved = resolveConfig(settings);
export default {
  ...resolved.site,
  baseUrl: process.env.SITE_BASE_URL ?? resolved.site.baseUrl ?? '/',
  presets: [['classic', resolved.preset], ...(resolved.site.presets ?? [])],
  plugins: [...(resolved.site.plugins ?? []), ...(resolved.custom.search.enabled ? ['./plugins/site-search'] : [])],
  themeConfig: {
    prism: {theme: themes.github, darkTheme: themes.dracula},
    ...resolved.site.themeConfig,
    ...resolved.theme,
  },
  customFields: {...resolved.site.customFields, pattern: resolved.custom},
} as Config;
