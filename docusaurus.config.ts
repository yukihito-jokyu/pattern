import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'pattern',
  tagline: '設定・構成の説明と実装のパターン集',
  url: 'https://yukihito-jokyu.github.io',
  baseUrl: process.env.SITE_BASE_URL || '/pattern/',
  trailingSlash: false,
  future: {v4: true},
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  onDuplicateRoutes: 'throw',
  markdown: {
    format: 'md',
    hooks: {onBrokenMarkdownLinks: 'throw', onBrokenMarkdownImages: 'throw'},
  },
  i18n: {defaultLocale: 'ja', locales: ['ja']},
  presets: [['classic', {
    docs: {sidebarPath: './sidebars.ts', routeBasePath: 'docs'},
    blog: false,
  } satisfies Preset.Options]],
  plugins: ['./plugins/site-search', './plugins/pattern-list'],
  themeConfig: {
    colorMode: {respectPrefersColorScheme: true},
    navbar: {
      title: 'pattern',
      items: [{type: 'docSidebar', sidebarId: 'docsSidebar', label: 'ドキュメント', position: 'left'}],
    },
    prism: {theme: prismThemes.github, darkTheme: prismThemes.dracula},
  } satisfies Preset.ThemeConfig,
};

export default config;
