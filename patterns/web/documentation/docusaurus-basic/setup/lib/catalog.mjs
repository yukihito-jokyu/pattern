import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { joiSurfaces, require, digest } from './surfaces.mjs';
import { classifyQuestion } from './question-levels.mjs';
const ts = require('typescript');
function typeSurfaces() {
    const file = fileURLToPath(new URL('./type-surfaces.ts', import.meta.url));
    const program = ts.createProgram([file], {
        strict: true, skipLibCheck: true, moduleResolution: ts.ModuleResolutionKind.Bundler, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022
    });
    const checker = program.getTypeChecker();
    const source = program.getSourceFile(file);
    function describe(type, ancestors = new Set()) {
        const text = checker.typeToString(type, undefined, ts.TypeFormatFlags.NoTruncation);
        if (type.getCallSignatures().length || type.getConstructSignatures().length || ['RegExp', 'Date', 'Buffer'].includes(type.symbol?.name))
            return { type: 'module', expression: text };
        if (ancestors.has(type.id))
            return { type: 'recursive', expression: text };
        const next = new Set([...ancestors, type.id]);
        if (type.isUnion())
            return { type: 'alternatives', matches: type.types.map(t => ({ schema: describe(t, next) })) };
        if (type.isStringLiteral() || type.isNumberLiteral())
            return { type: typeof type.value, allow: [type.value], flags: { only: true } };
        if (type.flags & ts.TypeFlags.BooleanLiteral)
            return { type: 'boolean', allow: [type.intrinsicName === 'true'], flags: { only: true } };
        if (type.flags & ts.TypeFlags.StringLike)
            return { type: 'string' };
        if (type.flags & ts.TypeFlags.NumberLike)
            return { type: 'number' };
        if (type.flags & ts.TypeFlags.BooleanLike)
            return { type: 'boolean' };
        if (type.flags & ts.TypeFlags.Undefined)
            return { type: 'undefined' };
        if (type.flags & ts.TypeFlags.Null)
            return { type: 'null' };
        if (checker.isArrayType(type))
            return { type: 'array', items: [describe(checker.getTypeArguments(type)[0], next)] };
        if (checker.isTupleType(type))
            return { type: 'array', items: checker.getTypeArguments(type).map(t => describe(t, next)) };
        if (type.flags & ts.TypeFlags.Object) {
            const keys = {};
            for (const prop of checker.getPropertiesOfType(type)) {
                if (prop.name.startsWith('__@'))
                    continue;
                const declaration = prop.valueDeclaration ?? prop.declarations?.[0];
                if (!declaration)
                    continue;
                const d = describe(checker.getTypeOfSymbolAtLocation(prop, declaration), next);
                d.description = ts.displayPartsToString(prop.getDocumentationComment(checker));
                d.flags = { ...d.flags, presence: prop.flags & ts.SymbolFlags.Optional ? 'optional' : 'required' };
                keys[prop.name] = d;
            }
            const index = checker.getIndexTypeOfType(type, ts.IndexKind.String);
            return { type: 'object', keys, ...(index ? { patterns: [{ rule: describe(index, next) }] } : {}) };
        }
        return { type: 'any', expression: text };
    }
    const get = name => describe(checker.getTypeAtLocation(source.statements.find(n => n.name?.text === name)));
    return [
        {
            scope: 'preset', source: '@docusaurus/preset-classic/lib/options.d.ts', hash: digest(readFileSync(require.resolve('@docusaurus/preset-classic/lib/options.d.ts'), 'utf8')), schema: get('PresetSettings')
        },
        {
            scope: 'playwright', source: 'playwright/types/test.d.ts', hash: digest(readFileSync(path.join(path.dirname(require.resolve('playwright/package.json')), 'types/test.d.ts'), 'utf8')), schema: get('BrowserSettings')
        },
    ];
}
function typescriptSurface() {
    const describe = option => ({
        type: typeof option.type === 'string' ? option.type : option.type instanceof Map ? 'enum' : 'any', description: option.description?.message, ...(option.type instanceof Map ? { allow: [...option.type.keys()] } : {}), ...(option.element ? { items: [describe(option.element)] } : {}), default: option.defaultValueDescription
    });
    return {
        scope: 'typescript', source: 'typescript/lib/typescript.js', hash: digest(readFileSync(require.resolve('typescript'), 'utf8')), schema: {
            type: 'object', keys: {
                compilerOptions: {
                    type: 'object', keys: Object.fromEntries(ts.optionDeclarations.filter(x => !x.isCommandLineOnly).map(x => [x.name, describe(x)]))
                }, files: { type: 'array', items: [{ type: 'string' }] }, include: { type: 'array', items: [{ type: 'string' }] }, exclude: { type: 'array', items: [{ type: 'string' }] }, extends: {
                    type: 'alternatives', matches: [{ schema: { type: 'string' } }, { schema: { type: 'array', items: [{ type: 'string' }] } }]
                }, references: {
                    type: 'array', items: [{ type: 'object', keys: { path: { type: 'string' }, prepend: { type: 'boolean' } } }]
                }, compileOnSave: { type: 'boolean' }, watchOptions: { type: 'object', keys: Object.fromEntries(ts.optionsForWatch.map(x => [x.name, describe(x)])) }, typeAcquisition: {
                    type: 'object', keys: {
                        enable: { type: 'boolean' }, include: { type: 'array', items: [{ type: 'string' }] }, exclude: { type: 'array', items: [{ type: 'string' }] }, disableFilenameBasedTypeAcquisition: { type: 'boolean' }
                    }
                }, '$schema': { type: 'string' }
            }
        }
    };
}
const docs = {
    site: 'https://docusaurus.io/docs/api/docusaurus-config',
    theme: 'https://docusaurus.io/docs/api/themes/configuration',
    preset: 'https://docusaurus.io/docs/using-plugins#docusauruspreset-classic',
    documents: 'https://docusaurus.io/docs/api/plugins/@docusaurus/plugin-content-docs#markdown-front-matter',
    categories: 'https://docusaurus.io/docs/sidebar/autogenerated#category-item-metadata',
    sidebar: 'https://docusaurus.io/docs/sidebar/items',
    typescript: 'https://www.typescriptlang.org/tsconfig/',
    playwright: 'https://playwright.dev/docs/api/class-testconfig',
    custom: 'setup/sources.md',
};
export function collectCatalog() {
    const surfaces = [...joiSurfaces(), ...typeSurfaces(), typescriptSurface()];
    const entries = [];
    for (const surface of surfaces) {
        const walk = (node, valuePath, id = valuePath, condition = null) => {
            entries.push({
                id, path: valuePath, ...classifyQuestion(valuePath, node), source: surface.source, reference: docs[surface.scope.split('.')[0]], type: node.type, required: node.flags?.presence === 'required', forbidden: node.flags?.presence === 'forbidden', default: node.flags?.default ?? node.default ?? { notSpecified: true }, constraints: node.rules ?? [], choices: node.allow ?? [], condition, description: node.description ?? node.flags?.description ?? `${valuePath} の設定。型・既定動作と出典を確認して選択します。`, question: `${valuePath} は現在の値を維持しますか、変更しますか、未設定に戻しますか？`, binding: surface.scope, schema: node
            });
            for (const [key, child] of Object.entries(node.keys ?? {}))
                walk(child, `${valuePath}.${key}`, `${id}.${key}`, condition);
            (node.items ?? []).forEach((child, i) => walk(child, valuePath + '[]', `${id}[]:${i}`, condition));
            (node.patterns ?? []).forEach((pattern, i) => {
                if (pattern.rule)
                    walk(pattern.rule, valuePath + '.*', `${id}.*:${i}`, condition);
            });
            const branches = [...(node.matches ?? []), ...(node.whens ?? [])];
            branches.forEach((branch, i) => {
                for (const key of ['schema', 'then', 'otherwise'])
                    if (branch[key])
                        walk(branch[key], valuePath, `${id}~${i}:${key}`, JSON.stringify(branch.is ?? branch.ref ?? '型による分岐'));
                for (const [j, b] of (branch.switch ?? []).entries())
                    if (b.then)
                        walk(b.then, valuePath, `${id}~${i}:switch${j}`, JSON.stringify(b.is));
            });
        };
        walk(surface.schema, surface.scope, `${surface.scope}#${surface.source}`);
    }
    // Avoid duplicating complete recursive schema trees on every row.
    for (const entry of entries) {
        const { keys, items, matches, whens, patterns, ...leaf } = entry.schema;
        entry.schema = leaf;
    }
    return { version: 1, surfaces, entries };
}
function version(p) {
    let file;
    try {
        file = require.resolve(p + '/package.json');
    }
    catch {
        file = path.resolve(path.dirname(require.resolve(p + '/lib/options.js')), '../package.json');
    }
    return JSON.parse(readFileSync(file, 'utf8')).version;
}
export function coverageOf(catalog) {
    return {
        version: 1, dependencies: Object.fromEntries(['@docusaurus/core', '@docusaurus/preset-classic', '@docusaurus/plugin-content-docs', '@docusaurus/theme-classic', 'typescript', '@playwright/test'].map(p => [p, version(p)])), sources: catalog.surfaces.map(({ scope, source, hash }) => ({ scope, source, hash })), ids: catalog.entries.map(e => e.id)
    };
}
