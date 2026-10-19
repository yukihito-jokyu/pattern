// Product decisions belong here; OSS schemas continue to define valid values.
export const questionLevels = ['important', 'normal', 'advanced'];
export function assertQuestionLevel(level) {
    if (!questionLevels.includes(level))
        throw Error('質問範囲はimportant（重要のみ）、normal（重要＋普通）、advanced（すべて）から選んでください。');
    return level;
}
export function includesQuestion(level, importance) {
    assertQuestionLevel(level);
    return questionLevels.indexOf(importance) <= questionLevels.indexOf(level);
}

const important = new Set([
    'site.title', 'theme.navbar.title', 'site.url', 'site.baseUrl', 'site.i18n.defaultLocale', 'site.i18n.locales',
    'preset.blog', 'custom.search.enabled',
    'custom.home.heading', 'custom.home.body', 'custom.home.linkLabel', 'custom.home.linkTo',
]);
const normal = [
    /^site\.(tagline|favicon|titleDelimiter|noIndex|trailingSlash|organizationName|projectName|deploymentBranch|githubHost|githubPort)$/,
    /^preset\.docs\.(routeBasePath|breadcrumbs|showLastUpdateTime|showLastUpdateAuthor|editUrl|sidebarCollapsible|sidebarCollapsed|tagsBasePath)$/,
    /^preset\.(pages|sitemap|theme|googleAnalytics|gtag|googleTagManager)$/,
    /^theme\.(image|metadata|navbar\.(title|logo|items|hideOnScroll|style)|footer|announcementBar|colorMode\.(defaultMode|disableSwitch|respectPrefersColorScheme)|docs\.sidebar\.(hideable|autoCollapseCategories)|tableOfContents\.(minHeadingLevel|maxHeadingLevel)|prism\.(theme|darkTheme|additionalLanguages|defaultLanguage))$/,
    /^documents\.\*\.(title|description|slug|sidebar_position|sidebar_label|hide_title|hide_table_of_contents|tags|image|draft|unlisted|pagination_next|pagination_prev|toc_min_heading_level|toc_max_heading_level)$/,
    /^categories\.\*\.(label|position|collapsed|collapsible|link)$/,
    /^custom\.search\.(include|exclude|limit|label|placeholder|emptyMessage|noResultsMessage|shortcut)$/,
];
export function classifyQuestion(path, node) {
    if (node.flags?.presence === 'forbidden')
        return { importance: 'advanced', importanceReason: '廃止された項目。設定せず、移行時に参照する。' };
    if (important.has(path))
        return { importance: 'important', importanceReason: 'サイトの目的・公開URL・主要機能を決めるため、導入時に確認する。' };
    if (normal.some(rule => rule.test(path)))
        return { importance: 'normal', importanceReason: '見た目・記事の表示・運用を調整する項目。初期設定のままでも利用できる。' };
    return { importance: 'advanced', importanceReason: '内部処理・詳細な拡張・構造や型の項目。通常は現在値またはOSSの既定動作を維持する。' };
}

// Return concrete key arrays so keys such as "docs/intro.md" stay intact.
export function changedPaths(before, after, prefix = []) {
    if (JSON.stringify(before) === JSON.stringify(after)) return [];
    const beforeObject = before !== null && typeof before === 'object';
    const afterObject = after !== null && typeof after === 'object';
    if ((beforeObject && afterObject && Array.isArray(before) === Array.isArray(after)) ||
        (before === undefined && afterObject) || (after === undefined && beforeObject)) {
        const keys = [...new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])];
        if (!keys.length) return [prefix];
        return keys.flatMap(key => changedPaths(before?.[key], after?.[key], [...prefix, key]));
    }
    return [prefix];
}
export function coversPath(pattern, keys) {
    const tokens = pattern.replace(/\[\]/g, '.[]').split('.');
    return tokens.length <= keys.length && tokens.every((token, i) => token === '*' || token === '[]' || token === keys[i]);
}
