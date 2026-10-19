import { createRequire, Module } from 'node:module';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const require = createRequire(import.meta.url);
export const digest = value => crypto.createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const { Joi } = require('@docusaurus/utils-validation');
function capture(pkg) {
    let result;
    const mod = require(`${pkg}/lib/options.js`);
    const fn = mod.validateOptions ?? require(`${pkg}/lib/index.js`).validateOptions;
    try {
        fn({
            options: {}, validate: (schema, value) => { result = schema; return schema.validate(value).value ?? {}; }
        });
    }
    catch (error) {
        if (!result)
            throw error;
    }
    if (!result)
        throw new Error(`${pkg}: schema取得失敗`);
    return result;
}
// Category/sidebar schemas are private in the pinned release. Compile the installed,
// MIT-licensed module unchanged, appending exports for inspection; never modify node_modules.
function privateSchemas() {
    const file = require.resolve('@docusaurus/plugin-content-docs/lib/sidebars/validation.js');
    const mod = new Module(file, undefined);
    mod.filename = file;
    mod.paths = Module._nodeModulePaths(path.dirname(file));
    mod._compile(readFileSync(file, 'utf8') + '\nmodule.exports.inspectSchemas = {categoryMetadataFileSchema, sidebarItemSchema};', file);
    return mod.exports.inspectSchemas;
}
const custom = require('./custom-schema.cjs');
export function schemas() {
    const { categoryMetadataFileSchema, sidebarItemSchema } = privateSchemas();
    const site = require('@docusaurus/core/lib/server/configValidation.js').ConfigSchema;
    return {
        site,
        'preset.docs': capture('@docusaurus/plugin-content-docs'),
        'preset.blog': capture('@docusaurus/plugin-content-blog'),
        'preset.pages': capture('@docusaurus/plugin-content-pages'),
        'preset.sitemap': capture('@docusaurus/plugin-sitemap'),
        'preset.svgr': capture('@docusaurus/plugin-svgr'),
        'preset.googleAnalytics': capture('@docusaurus/plugin-google-analytics'),
        'preset.gtag': capture('@docusaurus/plugin-google-gtag'),
        'preset.googleTagManager': capture('@docusaurus/plugin-google-tag-manager'),
        'preset.theme': capture('@docusaurus/theme-classic'),
        theme: require('@docusaurus/theme-classic/lib/options.js').ThemeConfigSchema,
        'documents.*': require('@docusaurus/plugin-content-docs/lib/frontMatter.js').DocFrontMatterSchema,
        'categories.*': categoryMetadataFileSchema,
        'sidebar.*[]': sidebarItemSchema,
        custom,
    };
}
function serial(value) {
    return JSON.parse(JSON.stringify(value, (_, v) => typeof v === 'function' ? { computedDefault: true } : v instanceof RegExp ? { pattern: String(v) } : v));
}
const sourceFor = scope => scope === 'custom' ? 'setup/lib/custom-schema.cjs' : scope === 'site' ? '@docusaurus/core/lib/server/configValidation.js' : scope === 'theme' ? '@docusaurus/theme-classic/lib/options.js' : scope.startsWith('documents') ? '@docusaurus/plugin-content-docs/lib/frontMatter.js' : scope.startsWith('categories') || scope.startsWith('sidebar') ? '@docusaurus/plugin-content-docs/lib/sidebars/validation.js' : `@docusaurus/${({
    'googleAnalytics': 'plugin-google-analytics', 'gtag': 'plugin-google-gtag', 'googleTagManager': 'plugin-google-tag-manager', 'theme': 'theme-classic', 'docs': 'plugin-content-docs', 'blog': 'plugin-content-blog', 'pages': 'plugin-content-pages', 'sitemap': 'plugin-sitemap', 'svgr': 'plugin-svgr'
})[scope.split('.')[1]]}/lib/options.js`;
export function joiSurfaces() {
    return Object.entries(schemas()).map(([scope, schema]) => {
        const source = sourceFor(scope);
        const file = scope === 'custom' ? new URL('./custom-schema.cjs', import.meta.url) : require.resolve(source);
        return { scope, source, hash: digest(readFileSync(file, 'utf8')), schema: serial(schema.describe()) };
    });
}
export { require, Joi };
